"""Scoring & Fit Evaluation Engine.

Two-stage evaluation pipeline:
1. Deterministic Rule Score (0 to 40 pts):
   - Location matches Mumbai / Navi Mumbai / Remote (+15 pts)
   - Experience band matches 0-3 years / fresher / entry-level (+15 pts)
   - Domain matches Software, AI, Fintech, B2B SaaS, Marketplaces, or Supply Chain (+10 pts)
2. Semantic / LLM Evaluation (0 to 60 pts):
   - Analyze role requirements vs candidate's hands-on strengths
   - Structured JSON output with fit_score, decision, matching_skills, gap_analysis, and recommended_angle.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.profile_engine import ProfileEngine, sanitize_builder_text
from src.scrapers.base_scraper import ScrapedJob
from src.scrapers.filter_rules import check_negative_filters

logger = logging.getLogger(__name__)


class EvaluationResult(BaseModel):
    deterministic_score: int = Field(ge=0, le=40)
    semantic_score: int = Field(ge=0, le=60)
    fit_score: int = Field(ge=0, le=100)
    decision: str  # "APPLY" | "CONSIDER" | "SKIP"
    matching_skills: List[str]
    gap_analysis: str
    recommended_angle: str
    is_filtered_out: bool = False
    filter_reason: Optional[str] = None


class ScoringEngine:
    """Evaluates job postings against the candidate's master profile."""

    def __init__(self, profile_engine: Optional[ProfileEngine] = None):
        self.profile_engine = profile_engine or ProfileEngine()
        self.profile = self.profile_engine.profile

    def compute_deterministic_score(self, job: ScrapedJob) -> int:
        """Calculates deterministic score (0 to 40 pts) based on location, experience, and domain."""
        score = 0
        loc_text = f"{job.location} {job.raw_description}".lower()

        # 1. Location match: Mumbai / Navi Mumbai / Remote Worldwide (+15 pts)
        remote_worldwide_keywords = [
            "mumbai", "navi mumbai", "thane", "remote", "hybrid", "anywhere in india",
            "worldwide", "global", "anywhere", "work from home", "wfh", "telecommute",
            "apac", "emea", "latam", "usa", "canada", "europe", "uk", "germany"
        ]
        if any(loc in loc_text for loc in remote_worldwide_keywords):
            score += 15
        elif any(loc in loc_text for loc in ["pune", "bengaluru", "bangalore", "delhi", "gurgaon", "noida", "india"]):
            score += 8

        # 2. Experience band match: 0-3 years / fresher / entry-level / intern (+15 pts)
        exp_text = f"{job.experience_years} {job.raw_description}".lower()
        if any(w in exp_text for w in ["0-", "1-", "2-", "0 to", "1 to", "2 to", "entry level", "associate", "junior", "fresher", "intern", "trainee", "early career", "1-3", "2-3", "1-2"]):
            score += 15
        elif any(w in exp_text for w in ["3-4", "3-5", "2-4", "2-5", "mid level"]):
            score += 10
        elif any(w in exp_text for w in ["5+", "6+", "7+", "8+", "10+"]):
            score += 0
        else:
            # Default for unspecified experience if title indicates early career or specialist
            title_lower = job.role.lower()
            if any(t in title_lower for t in ["associate", "junior", "apm", "coordinator", "analyst", "intern", "specialist", "trainee", "lead"]):
                score += 15
            else:
                score += 10

        # 3. Domain match: Software, AI, Fintech, B2B SaaS, Marketplaces, Supply Chain, Operations (+10 pts)
        domain_text = f"{job.role} {job.company} {job.raw_description}".lower()
        target_domains = [
            "ai", "llm", "genai", "software", "saas", "b2b", "fintech",
            "marketplace", "logistics", "supply chain", "fleet", "operations",
            "kyc", "compliance", "developer tools", "product operations", "data",
            "s&op", "demand planning", "project management", "agile", "business analyst",
            "solutions", "systems", "growth", "product owner"
        ]
        matches = [d for d in target_domains if d in domain_text]
        if matches:
            score += 10
        elif any(d in domain_text for d in ["tech", "digital", "internet", "e-commerce", "analytics"]):
            score += 6

        return min(40, score)

    def evaluate(self, job: ScrapedJob) -> EvaluationResult:
        """Full evaluation pipeline: filter check -> deterministic score -> semantic evaluation."""
        # 1. Check negative domain traps first
        is_valid, filter_reason = check_negative_filters(
            title=job.role,
            company=job.company,
            description=job.raw_description,
            experience_text=job.experience_years
        )
        if not is_valid:
            return EvaluationResult(
                deterministic_score=0,
                semantic_score=0,
                fit_score=0,
                decision="SKIP",
                matching_skills=[],
                gap_analysis=f"Disqualified by negative domain filter: {filter_reason}",
                recommended_angle="Do not pursue. Posting falls into an off-target industry or seniority gate.",
                is_filtered_out=True,
                filter_reason=filter_reason
            )

        # 2. Compute deterministic score (0 - 40)
        det_score = self.compute_deterministic_score(job)

        # 3. Semantic evaluation (0 - 60)
        # Try LLM if API key exists; fallback to grounded heuristic evaluator
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        sem_result: Optional[Dict[str, Any]] = None
        if gemini_key:
            sem_result = self._evaluate_with_gemini(job, det_score, gemini_key)
        elif openai_key:
            sem_result = self._evaluate_with_openai(job, det_score, openai_key)

        if not sem_result:
            sem_result = self._evaluate_heuristically(job, det_score)

        sem_score = int(sem_result.get("semantic_score", 45))
        total_score = min(100, det_score + sem_score)

        # Decision threshold
        if total_score >= 75:
            decision = "APPLY"
        elif total_score >= 55:
            decision = "CONSIDER"
        else:
            decision = "SKIP"

        return EvaluationResult(
            deterministic_score=det_score,
            semantic_score=sem_score,
            fit_score=total_score,
            decision=decision,
            matching_skills=sem_result.get("matching_skills", []),
            gap_analysis=sanitize_builder_text(sem_result.get("gap_analysis", "")),
            recommended_angle=sanitize_builder_text(sem_result.get("recommended_angle", "")),
            is_filtered_out=False
        )

    def _evaluate_heuristically(self, job: ScrapedJob, det_score: int) -> Dict[str, Any]:
        """Grounded heuristic semantic evaluator without external API dependency."""
        job_text = f"{job.role} {job.company} {job.raw_description}".lower()

        # Skill bank mapping
        skill_catalog = {
            "AI PRDs & Specs": ["prd", "specification", "product requirements", "specs", "roadmap", "features", "backlog"],
            "LLM & Model Serving": ["ai", "llm", "genai", "prompt", "inference", "llama", "model", "token"],
            "SQL & Funnel Analytics": ["sql", "analytics", "metrics", "funnel", "conversion", "telemetry", "drop-off"],
            "Figma UX & Wireframing": ["figma", "wireframe", "ux", "ui", "user journey", "prototype", "onboarding"],
            "Ground Operations Logistics": ["operations", "logistics", "supply", "fleet", "sla", "dispatch", "fulfillment"],
            "B2B Enterprise Discovery": ["b2b", "enterprise", "client", "stakeholder", "vendor", "account", "contract"],
            "Jira & Agile Sprint Planning": ["jira", "agile", "scrum", "sprint", "grooming", "standup", "velocity"],
            "Document Parsing & KYC": ["kyc", "document", "parsing", "verification", "gst", "gstin", "compliance", "fraud"],
            "Agile Project Coordination (CIPM)": ["cipm", "project management", "project coordinator", "milestones", "pmi", "deliverables", "gantt"],
            "Supply Chain & S&OP Planning": ["supply chain", "demand planning", "s&op", "inventory", "procurement", "dispatch"],
            "Business & Systems Analysis": ["business analyst", "systems analyst", "solutions", "functional specs", "workflows", "gap analysis"],
            "Growth & Marketplace Mechanics": ["growth", "marketplace", "retention", "activation", "experimentation", "monetization"],
            "Product Ownership & Backlog": ["product owner", "user stories", "acceptance criteria", "po intern", "backlog"]
        }

        matched_skills = []
        for skill_name, triggers in skill_catalog.items():
            if any(t in job_text for t in triggers):
                matched_skills.append(skill_name)

        if not matched_skills:
            matched_skills = ["Technical PRDs", "Jira & Agile", "SQL & Telemetry", "Operations Planning"]

        # Calculate semantic score based on matches and relevance
        base_sem = 32
        bonus = min(28, len(matched_skills) * 4)
        sem_score = base_sem + bonus

        # Generate grounded gap analysis
        if "ai" in job_text or "llm" in job_text:
            gap = (
                "Role emphasizes production AI and prompt reliability. "
                "Candidate's HireFlo India achievement cutting Llama 3.1 compute costs by 40% via NVIDIA NIM "
                "and EvalGuard AI guardrails perfectly counters any enterprise gap."
            )
            angle = (
                "Lead with HireFlo India NVIDIA NIM optimization, 1,000-doc parsing pipeline, "
                "and live EvalGuard AI token economics demo."
            )
        elif "cipm" in job_text or "project manager" in job_text or "project coordinator" in job_text or "agile" in job_text:
            gap = (
                "Role requires disciplined milestone tracking and agile sprint cadence. "
                "Candidate's PMI CIPM certification and NeoManpower track record managing 200+ projects with zero SLA breaches proves delivery rigor."
            )
            angle = (
                "Highlight CIPM project certification, Jira sprint hygiene, and hands-on SLA adherence."
            )
        elif "supply" in job_text or "s&op" in job_text or "demand" in job_text or "logistics" in job_text or "operations" in job_text:
            gap = (
                "Role seeks deep operational empathy alongside software tools. "
                "Candidate's NeoManpower track record (50+ B2B clients, 133 personnel, 200+ projects with zero SLA breaches) "
                "proves rare hands-on grit that purely theoretical APMs lack."
            )
            angle = (
                "Highlight NeoManpower commercial operations leadership and AutoMatch IQ marketplace funnel telemetry."
            )
        elif "business analyst" in job_text or "systems" in job_text or "solutions" in job_text:
            gap = (
                "Role requires bridging business workflows with technical specifications. "
                "Candidate's B.Com commercial background, upGrad Business Analytics certification, and technical PRD authoring bridges this seamlessly."
            )
            angle = (
                "Emphasize business analytics, SQL data querying, and clear functional specification drafting."
            )
        elif "fintech" in job_text or "kyc" in job_text or "b2b" in job_text:
            gap = (
                "Role requires understanding compliance constraints and B2B user onboarding. "
                "Candidate's VeriShield verification engine and B.Com commercial background directly bridge this."
            )
            angle = (
                "Pitch VeriShield KYC/GSTIN risk engine and 30% onboarding completion boost at HireFlo India."
            )
        else:
            gap = (
                "Job expects strong cross-functional execution and PRD ownership. "
                "Candidate's dual background in founder operations and AI product management provides immediate velocity."
            )
            angle = (
                "Emphasize 14+ technical PRDs shipped at HireFlo India, SQL analytics, and interactive PM Product Lab builds."
            )

        return {
            "semantic_score": sem_score,
            "matching_skills": matched_skills[:5],
            "gap_analysis": gap,
            "recommended_angle": angle,
        }

    def _evaluate_with_gemini(self, job: ScrapedJob, det_score: int, api_key: str) -> Optional[Dict[str, Any]]:
        """Invokes Google Gemini model for structured semantic evaluation."""
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
You are an expert Head of Product evaluating a candidate against a job description.
{self.profile_engine.get_grounding_prompt_context()}

TARGET JOB:
Company: {job.company}
Role: {job.role}
Location: {job.location}
Experience: {job.experience_years}
Description: {job.raw_description}

Evaluate fit on a scale of 0 to 60 for the semantic/strengths portion (deterministic score already computed as {det_score}/40).
Output strictly valid JSON matching this schema:
{{
  "semantic_score": 48,
  "matching_skills": ["skill 1", "skill 2", "skill 3"],
  "gap_analysis": "Concise 1-2 sentence honest gap analysis without buzzwords or em dashes",
  "recommended_angle": "Concise 1 sentence recommended pitch angle referencing specific projects (HireFlo, NeoManpower, EvalGuard AI, VeriShield)"
}}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            logger.warning(f"Gemini evaluation failed, falling back to heuristic: {e}")
            return None

    def _evaluate_with_openai(self, job: ScrapedJob, det_score: int, api_key: str) -> Optional[Dict[str, Any]]:
        """Invokes OpenAI model for structured semantic evaluation."""
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            prompt = f"""
You are an expert Head of Product evaluating a candidate against a job description.
{self.profile_engine.get_grounding_prompt_context()}

TARGET JOB:
Company: {job.company}
Role: {job.role}
Location: {job.location}
Experience: {job.experience_years}
Description: {job.raw_description}

Evaluate fit on a scale of 0 to 60 for semantic score (deterministic score: {det_score}/40).
Respond with valid JSON:
{{
  "semantic_score": 48,
  "matching_skills": ["skill 1", "skill 2"],
  "gap_analysis": "Concise gap analysis without em dashes or buzzwords",
  "recommended_angle": "Actionable pitch angle referencing candidate's actual projects"
}}
"""
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            return data
        except Exception as e:
            logger.warning(f"OpenAI evaluation failed, falling back to heuristic: {e}")
            return None
