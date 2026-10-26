"""Profile Engine: Parses, validates, and injects candidate ground truth."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PersonalLinks(BaseModel):
    portfolio: str
    pm_product_lab: str
    github: str
    linkedin: str


class PersonalDetails(BaseModel):
    name: str
    location: str
    phone: str
    email: str
    headline: str
    links: PersonalLinks


class Compensation(BaseModel):
    current_ctc_inr_lpa: float
    expected_ctc_min_inr_lpa: float
    expected_ctc_max_inr_lpa: float
    notes: str


class Positioning(BaseModel):
    persona: str
    years_experience: str
    primary_target_roles: List[str]
    target_locations: List[str]
    target_domains: List[str]
    compensation: Compensation


class WorkExperience(BaseModel):
    company: str
    role: str
    duration: str
    location: str
    context: str
    achievements: List[str]
    technologies: List[str]


class FeaturedProject(BaseModel):
    name: str
    category: str
    url: str
    summary: str
    key_metrics: str


class SkillsCollection(BaseModel):
    product_management: List[str]
    ai_and_technical: List[str]
    operations_and_business: List[str]
    tools: List[str]


class Education(BaseModel):
    degree: str
    institution: str
    specialization: str
    location: str


class Certification(BaseModel):
    name: str
    issuer: str


class ToneRules(BaseModel):
    style: str
    forbidden_patterns: List[str]
    required_framing: str


class CandidateProfile(BaseModel):
    personal: PersonalDetails
    positioning: Positioning
    work_experience: List[WorkExperience]
    featured_projects: List[FeaturedProject]
    skills: SkillsCollection
    education: List[Education]
    certifications: List[Certification]
    tone_rules: ToneRules


def get_default_profile_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "config" / "candidate_profile.json"


def sanitize_builder_text(text: str) -> str:
    """Removes em dashes, double dashes, and corporate buzzwords to maintain builder tone."""
    if not text:
        return ""
    # Replace em-dashes and en-dashes with simple commas, colons or clean stops
    cleaned = text.replace("—", ", ").replace("–", "-").replace(" -- ", ", ")
    
    # Strip unnecessary jargon words
    buzzwords = [
        r"\bspearheaded\b",
        r"\bleveraged synergistic\b",
        r"\bsynergies\b",
        r"\bholistic paradigm\b",
        r"\bthought leader\b",
        r"\bvisionary maven\b",
        r"\bvalue-add proposition\b",
    ]
    for pattern in buzzwords:
        cleaned = re.sub(pattern, "led", cleaned, flags=re.IGNORECASE)
    
    # Clean up double horizontal spaces and awkward comma spaces while preserving line breaks
    cleaned = re.sub(r"[^\S\r\n]+", " ", cleaned).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s*,\s*,", ",", cleaned)
    cleaned = re.sub(r"\s*,\s*\.", ".", cleaned)
    return cleaned


class ProfileEngine:
    """Loads candidate profile and provides context formatters for evaluation and tailoring."""

    def __init__(self, profile_path: Optional[Path] = None):
        self.profile_path = profile_path or get_default_profile_path()
        self.profile = self.load_profile()

    def load_profile(self) -> CandidateProfile:
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Candidate profile not found at {self.profile_path}")
        with open(self.profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CandidateProfile(**data)

    def get_grounding_prompt_context(self) -> str:
        """Generates candidate ground truth block for LLM evaluation and tailoring prompts."""
        p = self.profile
        lines = [
            f"CANDIDATE GROUND TRUTH (DO NOT FABRICATE OR EXAGGERATE):",
            f"- Name: {p.personal.name} | Location: {p.personal.location}",
            f"- Persona: {p.positioning.persona}",
            f"- Background: Transitioned from bootstrapped operations founder to tech Product Manager.",
            f"- Current CTC: INR {p.positioning.compensation.current_ctc_inr_lpa} LPA | Expected: INR {p.positioning.compensation.expected_ctc_min_inr_lpa}-{p.positioning.compensation.expected_ctc_max_inr_lpa} LPA",
            f"- Portfolio: {p.personal.links.portfolio}",
            f"- PM Product Lab: {p.personal.links.pm_product_lab}",
            f"- GitHub: {p.personal.links.github} | LinkedIn: {p.personal.links.linkedin}",
            "\nAUTHENTIC WORK EXPERIENCE:",
        ]
        for exp in p.work_experience:
            lines.append(f"  * {exp.company} ({exp.duration}) - {exp.role}:")
            lines.append(f"    Context: {exp.context}")
            for ach in exp.achievements:
                lines.append(f"    - {ach}")
        lines.append("\nINTERACTIVE BUILDS (IN PM PRODUCT LAB):")
        for proj in p.featured_projects:
            lines.append(f"  * {proj.name} ({proj.category}): {proj.summary} [Metric: {proj.key_metrics}]")

        lines.append(f"\nEDUCATION & CERTIFICATIONS:")
        for edu in p.education:
            lines.append(f"  * {edu.degree}, {edu.institution} ({edu.specialization})")
        cert_names = [f"{c.name} ({c.issuer})" for c in p.certifications]
        lines.append(f"  * Certifications: {', '.join(cert_names)}")

        lines.append("\nTONE GUIDELINES:")
        lines.append(f"  * {p.tone_rules.required_framing}")
        lines.append(f"  * FORBIDDEN: Strictly avoid em dashes (—), double hyphens (--), and generic corporate buzzwords.")
        return "\n".join(lines)

    def get_template_context(self, tailored_keywords: Optional[List[str]] = None, custom_summary: Optional[str] = None) -> Dict[str, Any]:
        """Provides context dictionary for HTML and Markdown resume generation."""
        p = self.profile
        keywords = tailored_keywords or []
        summary = custom_summary or (
            f"Early-career tech Product Manager and former founder with hands-on experience owning "
            f"0-to-1 product roadmaps, technical PRDs, and LLM inference cost optimization at HireFlo India. "
            f"Previously bootstrapped NeoManpower to 50+ B2B enterprise clients and 200+ on-ground deployments "
            f"across Mumbai. Bridges technical AI execution with disciplined operational delivery."
        )
        return {
            "name": p.personal.name,
            "location": p.personal.location,
            "phone": p.personal.phone,
            "email": p.personal.email,
            "headline": p.personal.headline,
            "links": p.personal.links.model_dump(),
            "summary": sanitize_builder_text(summary),
            "tailored_keywords": keywords,
            "work_experience": [exp.model_dump() for exp in p.work_experience],
            "featured_projects": [proj.model_dump() for proj in p.featured_projects],
            "skills": p.skills.model_dump(),
            "education": [edu.model_dump() for edu in p.education],
            "certifications": [cert.model_dump() for cert in p.certifications],
        }
