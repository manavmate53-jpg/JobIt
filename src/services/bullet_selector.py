"""Bullet Relevance Scoring & Dynamic Selector.

Inspired by Resume-Matcher's bullet_scoring and bullet_selector services.
Scores master-resume bullet points and interactive projects against the target job description,
dynamically prioritizing the most relevant achievements for maximum ATS and recruiter impact.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Strong builder action verbs that carry high ATS punch
ACTION_VERBS = {
    "cut", "built", "shipped", "optimized", "architected", "improved",
    "authored", "deployed", "scaled", "acquired", "orchestrated", "negotiated",
    "managed", "led", "boosted", "delivered", "automated", "designed"
}


class BulletSelector:
    """Ranks and selects the highest-scoring candidate bullet points for a target role."""

    def score_bullet(self, bullet_text: str, jd_lower: str) -> float:
        """Scores an individual bullet point against the job description (0 to 100)."""
        score = 40.0
        bullet_lower = bullet_text.lower()

        # 1. Action verb bonus (+15 pts)
        first_word = bullet_lower.split()[0] if bullet_lower.split() else ""
        if first_word in ACTION_VERBS or any(bullet_lower.startswith(v) for v in ACTION_VERBS):
            score += 15.0

        # 2. Grounded quantitative metric bonus (+20 pts)
        if re.search(r"\d+[%+k]?\b|\b\d+,\d+\b", bullet_text):
            score += 20.0

        # 3. JD Semantic Term Overlap (+25 pts)
        jd_tokens = set(re.findall(r"\b[a-z]{3,}\b", jd_lower))
        bullet_tokens = set(re.findall(r"\b[a-z]{3,}\b", bullet_lower))
        overlap = len(jd_tokens.intersection(bullet_tokens))
        score += min(25.0, overlap * 5.0)

        return min(100.0, score)

    def rank_experience_bullets(
        self,
        work_experience: List[Dict[str, Any]],
        jd_text: str,
        max_bullets_per_role: int = 5
    ) -> List[Dict[str, Any]]:
        """Re-orders achievements within each company so the highest-scoring bullets appear first."""
        jd_lower = jd_text.lower()
        tailored_experience = []

        for exp in work_experience:
            exp_copy = dict(exp)
            achievements = exp.get("achievements", [])

            # Score each achievement
            scored_bullets: List[Tuple[str, float]] = []
            for ach in achievements:
                s = self.score_bullet(ach, jd_lower)
                scored_bullets.append((ach, s))

            # Sort descending by relevance score
            scored_bullets.sort(key=lambda x: x[1], reverse=True)
            exp_copy["achievements"] = [b[0] for b in scored_bullets[:max_bullets_per_role]]
            tailored_experience.append(exp_copy)

        return tailored_experience

    def rank_featured_projects(
        self,
        featured_projects: List[Dict[str, Any]],
        jd_text: str
    ) -> List[Dict[str, Any]]:
        """Sorts candidate's interactive builds so the build most aligned to the target JD leads."""
        jd_lower = jd_text.lower()
        scored_projects: List[Tuple[Dict[str, Any], float]] = []

        for proj in featured_projects:
            proj_text = f"{proj.get('name', '')} {proj.get('category', '')} {proj.get('summary', '')}".lower()
            score = 50.0

            if "ai" in jd_lower or "llm" in jd_lower:
                if "evalguard" in proj_text:
                    score += 45.0
            elif "fintech" in jd_lower or "kyc" in jd_lower or "compliance" in jd_lower:
                if "verishield" in proj_text:
                    score += 45.0
            elif "logistics" in jd_lower or "marketplace" in jd_lower or "supply" in jd_lower or "fleet" in jd_lower:
                if "automatch" in proj_text:
                    score += 45.0
            elif "growth" in jd_lower or "lead" in jd_lower or "b2b" in jd_lower:
                if "lead radar" in proj_text:
                    score += 40.0

            # General overlap
            overlap = len(set(proj_text.split()).intersection(set(jd_lower.split())))
            score += min(15.0, overlap * 2.0)

            scored_projects.append((proj, score))

        scored_projects.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in scored_projects]
