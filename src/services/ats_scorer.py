"""ATS Score Computation Utilities.

Inspired by Resume-Matcher's deterministic ATS evaluation architecture.
Computes a transparent, weighted ATS composite score from 5 core signals:
  1. keyword_match (40%): Overlap between JD keywords and resume content
  2. skills_coverage (20%): Overlap between target JD competencies and candidate skill profile
  3. title_match (15%): Target role title presence in candidate headline/summary
  4. section_completeness (15%): Presence and formatting of essential resume sections
  5. date_consistency (10%): Share of experience dates following standardized chronological patterns
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Standard weights summing to 1.0 (matching Resume-Matcher standards)
WEIGHTS: Dict[str, float] = {
    "keyword_match": 0.40,
    "skills_coverage": 0.20,
    "title_match": 0.15,
    "section_completeness": 0.15,
    "date_consistency": 0.10,
}

_TITLE_STOPWORDS = frozenset({"a", "an", "and", "the", "of", "for", "in", "to", "at", "&", "-", "/", "|"})

_ESSENTIAL_SECTIONS = ["summary", "skills", "experience", "education", "projects", "contact"]


class ATSReport(BaseModel):
    overall_score: float = Field(ge=0.0, le=100.0)
    sub_scores: Dict[str, float]
    matched_keywords: List[str]
    missing_keywords: List[str]
    suggestions: List[str]
    title_match_type: str


class ATSScorer:
    """Evaluates ATS readiness and compatibility between a resume and target job description."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or WEIGHTS

    def evaluate(
        self,
        resume_text: str,
        resume_context: Dict[str, Any],
        job_role: str,
        job_description: str
    ) -> ATSReport:
        """Computes comprehensive ATS report with sub-scores and actionable suggestions."""
        sub_scores: Dict[str, float] = {}
        suggestions: List[str] = []

        # 1. Keyword match (40%)
        kw_score, matched_kw, missing_kw = self._compute_keyword_match(resume_text, job_description)
        sub_scores["keyword_match"] = round(kw_score, 1)
        if missing_kw:
            suggestions.append(f"Incorporate missing target keywords naturally: {', '.join(missing_kw[:4])}")

        # 2. Skills coverage (20%)
        skills_score = self._compute_skills_coverage(resume_context, job_description)
        sub_scores["skills_coverage"] = round(skills_score, 1)
        if skills_score < 75.0:
            suggestions.append("Reorder Core Competencies so target role skills appear in the first row.")

        # 3. Title match (15%)
        title_score, match_type = self._compute_title_match(resume_context, job_role)
        sub_scores["title_match"] = round(title_score, 1)
        if title_score < 75.0:
            suggestions.append(f"Align headline or professional summary closer to target title: '{job_role}'.")

        # 4. Section completeness (15%)
        section_score = self._compute_section_completeness(resume_context)
        sub_scores["section_completeness"] = round(section_score, 1)

        # 5. Date consistency (10%)
        date_score = self._compute_date_consistency(resume_context)
        sub_scores["date_consistency"] = round(date_score, 1)

        # Weighted composite overall score
        overall = sum(sub_scores[k] * self.weights[k] for k in self.weights)
        overall = round(min(100.0, max(0.0, overall)), 1)

        return ATSReport(
            overall_score=overall,
            sub_scores=sub_scores,
            matched_keywords=matched_kw,
            missing_keywords=missing_kw,
            suggestions=suggestions,
            title_match_type=match_type
        )

    def _extract_jd_keywords(self, text: str) -> Set[str]:
        """Extracts significant keywords and domain terms from job description."""
        # Clean text
        cleaned = re.sub(r"[^\w\s\-\.\#\+]", " ", text.lower())
        tokens = [t.strip(".-") for t in cleaned.split() if len(t.strip(".-")) > 2]
        stopwords = {
            "the", "and", "with", "for", "that", "this", "from", "will", "have", "are",
            "you", "our", "team", "work", "role", "looking", "candidate", "experience",
            "years", "about", "your", "must", "well", "ability", "strong", "preferred"
        }
        filtered = [t for t in tokens if t not in stopwords]

        # Common multi-word terms in tech PM
        phrases = [
            "product requirements", "prd", "user journeys", "user research", "agile",
            "sprint planning", "backlog grooming", "unit economics", "inference latency",
            "prompt engineering", "json schema", "sql telemetry", "funnel conversion",
            "data analytics", "customer discovery", "b2b clients", "sla compliance",
            "nvidia nim", "llama", "figma", "jira", "postman", "rest api", "wireframing"
        ]
        extracted: Set[str] = set()
        lower_text = text.lower()
        for phrase in phrases:
            if phrase in lower_text:
                extracted.add(phrase)

        # Add top individual words
        for t in filtered[:30]:
            if len(t) > 3:
                extracted.add(t)

        return extracted

    def _compute_keyword_match(self, resume_text: str, jd_text: str) -> Tuple[float, List[str], List[str]]:
        """Calculates keyword match percentage and lists present vs missing keywords."""
        jd_keywords = self._extract_jd_keywords(jd_text)
        if not jd_keywords:
            return 80.0, [], []

        resume_lower = resume_text.lower()
        matched = []
        missing = []

        for kw in sorted(jd_keywords):
            # Check whole word / phrase match
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, resume_lower):
                matched.append(kw)
            else:
                missing.append(kw)

        coverage = (len(matched) / len(jd_keywords)) * 100.0
        return coverage, matched, missing

    def _compute_skills_coverage(self, resume_context: Dict[str, Any], jd_text: str) -> float:
        """Measures how many candidate technical/PM skills match the job description."""
        skills_dict = resume_context.get("skills", {})
        all_skills: List[str] = []
        for cat, items in skills_dict.items():
            if isinstance(items, list):
                all_skills.extend(items)

        if not all_skills:
            return 70.0

        jd_lower = jd_text.lower()
        matched_count = 0
        for skill in all_skills:
            skill_tokens = [t.lower() for t in re.split(r"[\s,&/]+", skill) if len(t) > 3]
            if any(t in jd_lower for t in skill_tokens):
                matched_count += 1

        pct = (matched_count / min(15, len(all_skills))) * 100.0
        return min(100.0, max(50.0, pct))

    def _compute_title_match(self, resume_context: Dict[str, Any], target_title: str) -> Tuple[float, str]:
        """Scores alignment between candidate headline/summary and target job title."""
        target_clean = re.sub(r"[^\w\s]", "", target_title.lower()).strip()
        headline = resume_context.get("headline", "").lower()
        summary = resume_context.get("summary", "").lower()

        # Exact title in headline
        if target_clean in headline:
            return 100.0, "EXACT_IN_HEADLINE"

        # Exact title in summary
        if target_clean in summary:
            return 85.0, "EXACT_IN_SUMMARY"

        # Overlap of title tokens (excluding stopwords)
        title_tokens = [t for t in target_clean.split() if t not in _TITLE_STOPWORDS]
        if not title_tokens:
            return 75.0, "PARTIAL_MATCH"

        matches_in_head = sum(1 for t in title_tokens if t in headline)
        matches_in_sum = sum(1 for t in title_tokens if t in summary)

        if matches_in_head == len(title_tokens) or matches_in_sum == len(title_tokens):
            return 80.0, "ALL_TOKENS_PRESENT"
        
        overlap_score = (max(matches_in_head, matches_in_sum) / len(title_tokens)) * 65.0
        return max(40.0, overlap_score), "PARTIAL_OVERLAP"

    def _compute_section_completeness(self, resume_context: Dict[str, Any]) -> float:
        """Verifies presence of standard resume sections."""
        score = 0.0
        # Contact info
        if resume_context.get("name") and resume_context.get("email") and resume_context.get("phone"):
            score += 20.0
        # Links
        links = resume_context.get("links", {})
        if links.get("portfolio") or links.get("pm_product_lab"):
            score += 15.0
        # Summary
        if resume_context.get("summary") and len(resume_context["summary"]) > 50:
            score += 15.0
        # Work experience
        if resume_context.get("work_experience"):
            score += 20.0
        # Featured projects
        if resume_context.get("featured_projects"):
            score += 15.0
        # Education & certifications
        if resume_context.get("education") and resume_context.get("certifications"):
            score += 15.0

        return min(100.0, score)

    def _compute_date_consistency(self, resume_context: Dict[str, Any]) -> float:
        """Verifies standardized date formatting across all experience entries."""
        exps = resume_context.get("work_experience", [])
        if not exps:
            return 100.0

        valid_pattern = re.compile(r"(?:[a-zA-Z]{3}\s+)?\d{4}\s*-\s*(?:[a-zA-Z]{3}\s+)?(?:\d{4}|present|current)", re.IGNORECASE)
        consistent = 0
        for exp in exps:
            dur = exp.get("duration", "")
            if valid_pattern.search(dur):
                consistent += 1

        return (consistent / len(exps)) * 100.0
