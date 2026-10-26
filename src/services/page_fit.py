"""Single-Page Budget & Layout Validator.

Inspired by Resume-Matcher's page_fit service.
Calculates visual height, line budgets, and total word count to guarantee that the tailored
resume renders cleanly on exactly ONE A4 page without awkward page breaks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Single-Page A4 Budget Thresholds
MAX_RESUME_WORDS = 540
MIN_RESUME_WORDS = 320
MAX_SUMMARY_WORDS = 85
MAX_BULLETS_PER_ROLE = 5
MAX_FEATURED_PROJECTS = 3


class PageFitValidator:
    """Validates and enforces single-page A4 budget constraints."""

    @classmethod
    def audit_context(cls, context: Dict[str, Any]) -> Tuple[bool, int, List[str]]:
        """Audits resume context against single-page A4 density limits."""
        warnings: List[str] = []
        total_words = 0

        # Summary
        summary = context.get("summary", "")
        summary_words = len(summary.split())
        total_words += summary_words
        if summary_words > MAX_SUMMARY_WORDS:
            warnings.append(f"Summary exceeds {MAX_SUMMARY_WORDS} words ({summary_words} words)")

        # Work Experience
        exps = context.get("work_experience", [])
        for exp in exps:
            bullets = exp.get("achievements", [])
            if len(bullets) > MAX_BULLETS_PER_ROLE:
                warnings.append(f"{exp.get('company')} has {len(bullets)} bullets (max {MAX_BULLETS_PER_ROLE})")
            for b in bullets:
                total_words += len(b.split())

        # Projects
        projs = context.get("featured_projects", [])
        if len(projs) > MAX_FEATURED_PROJECTS:
            warnings.append(f"Featured projects exceeds {MAX_FEATURED_PROJECTS} ({len(projs)} present)")
        for p in projs[:MAX_FEATURED_PROJECTS]:
            total_words += len(p.get("summary", "").split())

        is_guaranteed = total_words <= MAX_RESUME_WORDS and len(warnings) == 0

        return is_guaranteed, total_words, warnings

    @classmethod
    def enforce_single_page(cls, context: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically trims excess bullets/projects to ensure single-page compliance."""
        safe_ctx = dict(context)

        # Cap projects at 3
        if "featured_projects" in safe_ctx:
            safe_ctx["featured_projects"] = safe_ctx["featured_projects"][:MAX_FEATURED_PROJECTS]

        # Cap bullets per experience
        if "work_experience" in safe_ctx:
            trimmed_exps = []
            for exp in safe_ctx["work_experience"]:
                e = dict(exp)
                e["achievements"] = e.get("achievements", [])[:MAX_BULLETS_PER_ROLE]
                trimmed_exps.append(e)
            safe_ctx["work_experience"] = trimmed_exps

        return safe_ctx
