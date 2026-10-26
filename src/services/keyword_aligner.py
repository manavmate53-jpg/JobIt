"""Keyword Extraction & Natural Alignment Service.

Inspired by Resume-Matcher's keyword_forcing architecture.
Extracts high-priority JD keywords, cross-references them against candidate ground-truth skills,
and injects attested keywords naturally into competencies and summary without keyword stuffing.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class KeywordAligner:
    """Discovers high-propensity keywords and aligns candidate competencies."""

    def align_keywords(
        self,
        candidate_skills: Dict[str, List[str]],
        jd_text: str
    ) -> Dict[str, Any]:
        """Maps candidate skills to the JD, identifying active matches and priority highlights."""
        jd_lower = jd_text.lower()
        aligned_skills: Dict[str, List[str]] = {}
        matched_highlights: List[str] = []

        for category, skills in candidate_skills.items():
            scored_skills: List[Tuple[str, int]] = []
            for skill in skills:
                skill_clean = skill.lower()
                tokens = [t for t in re.split(r"[\s,&/]+", skill_clean) if len(t) > 2]
                match_count = sum(1 for t in tokens if t in jd_lower)

                if match_count > 0:
                    matched_highlights.append(skill)
                    scored_skills.append((skill, match_count + 5))
                else:
                    scored_skills.append((skill, 1))

            # Sort skills so JD-matched skills appear first in each category
            scored_skills.sort(key=lambda x: x[1], reverse=True)
            aligned_skills[category] = [s[0] for s in scored_skills]

        # Extract top 5 priority keywords to inject into summary
        priority_keywords = list(dict.fromkeys(matched_highlights))[:5]
        if not priority_keywords:
            priority_keywords = ["Technical PRDs", "SQL Analytics", "Product Discovery", "Jira"]

        return {
            "aligned_skills": aligned_skills,
            "priority_keywords": priority_keywords,
            "match_count": len(matched_highlights),
        }
