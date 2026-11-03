"""
JobIt v2.0 - 100-Point Startup & Opportunity Scoring Engine
Evaluates opportunities based on funding stage, strategic pillar fit, location,
domain match, and proof-of-work prototype overlap.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from src.strategy.pillar_classifier import ClassificationResult, PillarClassifier, StrategicPillar

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    total_score: int
    qualified: bool
    funding_stage_score: int  # max 25
    pillar_score: int  # max 25
    location_score: int  # max 25
    domain_score: int  # max 15
    proof_of_work_score: int  # max 10
    qualification_notes: List[str] = field(default_factory=list)


class StrategyScoringEngine:
    """100-Point scoring rubric for startup opportunities."""

    QUALIFICATION_THRESHOLD = 70

    def __init__(self):
        self.classifier = PillarClassifier()

    def score_funding_stage(self, stage: str) -> int:
        st = stage.lower()
        if "seed" in st or "pre-series a" in st or "pre seed" in st:
            return 25  # Sweet spot: highest founder accessibility and urgency
        if "series a" in st:
            return 20  # Excellent: capital to scale, hiring 1st/2nd PM or ProdOps
        if "series b" in st:
            return 15  # Solid, though slightly more formal hiring processes
        if "angel" in st or "bootstrapped" in st:
            return 15
        return 10

    def score_pillar_alignment(self, classification: ClassificationResult) -> int:
        if classification.confidence >= 0.90:
            return 25
        if classification.confidence >= 0.75:
            return 20
        return 15

    def score_location(self, location: str) -> int:
        loc = location.lower()
        # Mumbai local network (candidate is based in Jogeshwari East, Mumbai)
        if any(m in loc for m in ["mumbai", "navi mumbai", "thane"]):
            return 25
        if "remote" in loc:
            return 20
        if any(h in loc for h in ["bengaluru", "bangalore", "delhi", "gurgaon", "noida", "ncr"]):
            return 15
        return 10

    def score_domain(self, sector: str) -> int:
        sec = sector.lower()
        high_affinity = ["fintech", "ai", "genai", "logistics", "supply chain", "workforce", "b2b saas", "marketplace"]
        if any(domain in sec for domain in high_affinity):
            return 15
        if "tech" in sec or "software" in sec:
            return 10
        return 5

    def score_proof_of_work(self, classification: ClassificationResult) -> int:
        # Candidate has 6 live PM Lab builds ready to demo
        if len(classification.primary_pm_lab_ids) >= 2:
            return 10
        if len(classification.primary_pm_lab_ids) == 1:
            return 7
        return 5

    def evaluate(
        self,
        company_name: str,
        role_title: str,
        funding_stage: str,
        sector: str,
        location: str,
        description: str = ""
    ) -> tuple[ScoreBreakdown, ClassificationResult]:
        classification = self.classifier.classify(
            title=role_title,
            description=description,
            sector=sector,
            stage=funding_stage
        )

        stage_pts = self.score_funding_stage(funding_stage)
        pillar_pts = self.score_pillar_alignment(classification)
        loc_pts = self.score_location(location)
        dom_pts = self.score_domain(sector)
        pow_pts = self.score_proof_of_work(classification)

        total = stage_pts + pillar_pts + loc_pts + dom_pts + pow_pts
        qualified = total >= self.QUALIFICATION_THRESHOLD

        notes = []
        if stage_pts >= 20:
            notes.append(f"High-intent funding stage: {funding_stage} (+{stage_pts})")
        if loc_pts == 25:
            notes.append(f"Direct local Mumbai advantage: {location} (+{loc_pts})")
        elif loc_pts == 20:
            notes.append(f"Flexible Remote model (+{loc_pts})")
        if pillar_pts >= 20:
            notes.append(f"Strong fit for {classification.pillar_label} (+{pillar_pts})")

        breakdown = ScoreBreakdown(
            total_score=total,
            qualified=qualified,
            funding_stage_score=stage_pts,
            pillar_score=pillar_pts,
            location_score=loc_pts,
            domain_score=dom_pts,
            proof_of_work_score=pow_pts,
            qualification_notes=notes
        )

        return breakdown, classification
