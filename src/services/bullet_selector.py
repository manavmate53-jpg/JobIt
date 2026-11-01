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
        """Sorts candidate's interactive builds dynamically based on job category:
        1. Fintech: PayRouter Engine, VeriShield, FlashQueue Simulator
        2. High Scale / Infrastructure: FlashQueue Simulator, PayRouter Engine, EvalGuard AI
        3. B2B SaaS / AI: EvalGuard AI, VeriShield, AutoMatch IQ
        4. Operations / Marketplace: CrewRoster Dashboard, AutoMatch IQ, VeriShield
        """
        jd_lower = jd_text.lower()
        scored_projects: List[Tuple[Dict[str, Any], float]] = []

        fintech_keywords = [
            "fintech", "payment", "payments", "gateway", "checkout", "routing",
            "refund", "idempotency", "transaction", "mdr", "card", "upi", "banking",
            "kyc", "gstin", "pan", "verification", "compliance", "fraud", "claims"
        ]
        high_scale_keywords = [
            "scale", "concurrency", "infrastructure", "system design", "distributed",
            "latency", "throughput", "caching", "traffic", "waiting room", "rate limit",
            "rate limiting", "token bucket", "504", "surge", "load", "redis", "queues",
            "backend", "microservices", "architect"
        ]
        b2b_saas_ai_keywords = [
            "ai", "llm", "genai", "agent", "agentic", "model", "prompt", "guardrails",
            "schema", "evaluation", "saas", "b2b", "token economics", "inference",
            "hitl", "nvidia", "nim", "fastapi", "enterprise"
        ]
        operations_marketplace_keywords = [
            "operations", "workforce", "rostering", "field", "logistics", "dispatch",
            "attendance", "qr", "sla", "marketplace", "discovery", "telemetry",
            "sql", "matching", "two-sided", "gig", "on-ground", "fleet"
        ]

        fintech_score = sum(1 for kw in fintech_keywords if kw in jd_lower)
        high_scale_score = sum(1 for kw in high_scale_keywords if kw in jd_lower)
        b2b_ai_score = sum(1 for kw in b2b_saas_ai_keywords if kw in jd_lower)
        ops_marketplace_score = sum(1 for kw in operations_marketplace_keywords if kw in jd_lower)

        for proj in featured_projects:
            proj_name = proj.get("name", "").lower()
            proj_cat = proj.get("category", "").lower()
            proj_text = f"{proj_name} {proj_cat} {proj.get('summary', '')}".lower()
            score = 50.0

            # Dynamic weighting based on detected primary category
            if fintech_score > 0 and (fintech_score >= max(high_scale_score, b2b_ai_score, ops_marketplace_score)):
                if "payrouter" in proj_name:
                    score += 55.0 + fintech_score * 3.0
                elif "verishield" in proj_name:
                    score += 45.0 + fintech_score * 2.5
                elif "flashqueue" in proj_name:
                    score += 35.0
                elif "automatch" in proj_name:
                    score += 25.0
            elif high_scale_score > 0 and (high_scale_score >= max(fintech_score, b2b_ai_score, ops_marketplace_score)):
                if "flashqueue" in proj_name:
                    score += 55.0 + high_scale_score * 3.0
                elif "payrouter" in proj_name:
                    score += 45.0 + high_scale_score * 2.5
                elif "evalguard" in proj_name:
                    score += 35.0
                elif "crewroster" in proj_name:
                    score += 20.0
            elif ops_marketplace_score > 0 and (ops_marketplace_score >= max(fintech_score, high_scale_score, b2b_ai_score)):
                if "crewroster" in proj_name:
                    score += 55.0 + ops_marketplace_score * 3.0
                elif "automatch" in proj_name:
                    score += 48.0 + ops_marketplace_score * 2.5
                elif "verishield" in proj_name:
                    score += 32.0
                elif "flashqueue" in proj_name:
                    score += 20.0
            elif b2b_ai_score > 0:
                if "evalguard" in proj_name:
                    score += 55.0 + b2b_ai_score * 3.0
                elif "verishield" in proj_name:
                    score += 42.0 + b2b_ai_score * 2.0
                elif "automatch" in proj_name:
                    score += 35.0
                elif "payrouter" in proj_name:
                    score += 25.0

            # General semantic overlap bonus
            overlap = len(set(re.findall(r"\b[a-z]{3,}\b", proj_text)).intersection(set(re.findall(r"\b[a-z]{3,}\b", jd_lower))))
            score += min(20.0, overlap * 2.5)

            scored_projects.append((proj, score))

        scored_projects.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in scored_projects]
