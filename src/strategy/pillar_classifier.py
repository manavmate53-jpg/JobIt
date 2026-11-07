"""
JobIt v2.0 - 3-Pillar Classifier
Routes opportunities into Pillar 1 (Founder's Office), Pillar 2 (ProdOps),
or Pillar 3 (Early-Stage / AI APM) with tailored narrative and PM Lab mappings.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StrategicPillar(str, Enum):
    FOUNDERS_OFFICE = "PILLAR_1_FOUNDERS_OFFICE"
    PRODUCT_OPERATIONS = "PILLAR_2_PRODUCT_OPERATIONS"
    AI_APM = "PILLAR_3_AI_APM"
    EVENT_OPERATIONS = "PILLAR_4_EVENT_OPERATIONS_MICE"


@dataclass
class ClassificationResult:
    pillar: StrategicPillar
    pillar_label: str
    confidence: float
    matched_keywords: List[str]
    narrative_focus: str
    primary_pm_lab_ids: List[str]
    suggested_ctc_band: Dict[str, float]


class PillarClassifier:
    """Classifies job titles and descriptions into one of the 3 strategic pillars."""

    def __init__(self):
        self.p1_patterns = [
            r"founder'?s?\s+office",
            r"chief\s+of\s+staff",
            r"strategy\s+(?:&|and)\s+ops",
            r"strategy\s+(?:&|and)\s+operations",
            r"founder\s+associate",
            r"special\s+projects",
            r"executive\s+assistant\s+to\s+founder",
            r"business\s+operations\s+lead",
            r"strategic\s+initiatives"
        ]

        self.p2_patterns = [
            r"product\s+ops",
            r"product\s+operations",
            r"operations\s+pm",
            r"operations\s+product\s+manager",
            r"supply\s+chain\s+pm",
            r"program\s+manager\s*-\s*product",
            r"field\s+operations",
            r"ops\s+product",
            r"process\s+product\s+manager"
        ]

        self.p3_patterns = [
            r"associate\s+product\s+manager",
            r"\bapm\b",
            r"junior\s+product\s+manager",
            r"ai\s+product\s+manager",
            r"technical\s+product\s+manager",
            r"fintech\s+pm",
            r"growth\s+product\s+manager",
            r"\bproduct\s+manager\b"
        ]

        self.p4_patterns = [
            r"event\s+operations",
            r"event\s+production",
            r"event\s+procurement",
            r"\bmice\b",
            r"venue\s+operations",
            r"client\s+servicing",
            r"venue\s+manager",
            r"event\s+project\s+manager",
            r"experiential\s+operations"
        ]

    def classify(
        self,
        title: str,
        description: str = "",
        sector: str = "",
        stage: str = "Seed"
    ) -> ClassificationResult:
        combined_text = f"{title} {description} {sector}".lower()

        p1_matches = [p for p in self.p1_patterns if re.search(p, combined_text)]
        p2_matches = [p for p in self.p2_patterns if re.search(p, combined_text)]
        p3_matches = [p for p in self.p3_patterns if re.search(p, combined_text)]
        p4_matches = [p for p in self.p4_patterns if re.search(p, combined_text)]

        # Specific weighting based on title vs description
        title_lower = title.lower()
        p1_title = any(re.search(p, title_lower) for p in self.p1_patterns)
        p2_title = any(re.search(p, title_lower) for p in self.p2_patterns)
        p3_title = any(re.search(p, title_lower) for p in self.p3_patterns)
        p4_title = any(re.search(p, title_lower) for p in self.p4_patterns)

        # Stage context: Early Seed/Pre-Series A strongly favors Founder's Office
        is_seed_stage = any(s in stage.lower() for s in ["seed", "pre-series a", "angel", "bootstrapped"])

        # Determine winner
        if p4_title or (p4_matches and len(p4_matches) >= len(p1_matches) and len(p4_matches) >= len(p2_matches) and len(p4_matches) >= len(p3_matches)):
            pillar = StrategicPillar.EVENT_OPERATIONS
            label = "Event Operations Manager / MICE Project Manager"
            confidence = 0.95 if p4_title else 0.82
            matched = p4_matches
            narrative = "4+ years delivering 150-200+ events across 15+ agencies in Mumbai. 2026 marquee executions at Tata Mumbai Marathon (Mumbai University venue production/ops), ICANN 2026, and Neurology Summit 2026. Manages procurement, venue mapping, AV, catering, and Canva/AI workflows."
            lab_ids = ["crewrostering", "flashqueue"]
            ctc_band = {"min_lpa": 5.5, "max_lpa": 7.5, "quoted": 6.5}
        elif p1_title or (p1_matches and len(p1_matches) >= len(p2_matches) and len(p1_matches) >= len(p3_matches)):
            pillar = StrategicPillar.FOUNDERS_OFFICE
            label = "Founder's Office / Chief of Staff"
            confidence = 0.95 if p1_title else 0.80
            matched = p1_matches
            narrative = "Zero-to-one business operator: scaled NeoManpower from scratch to 50+ B2B clients & 200+ projects with P&L ownership. Restructured HireFlo 5-tier monetization. Takes operational firefighting off the founder's plate."
            lab_ids = ["automatch", "crewrostering", "evalguard"]
        elif p2_title or (p2_matches and len(p2_matches) >= len(p3_matches)):
            pillar = StrategicPillar.PRODUCT_OPERATIONS
            label = "Product Operations Manager / Operations PM"
            confidence = 0.92 if p2_title else 0.78
            matched = p2_matches
            narrative = "High-velocity operator: directed 133 field personnel across 200+ events with 0 SLA breaches. Built QR check-in workflows & roster audit systems cutting reconciliation from 12 days to 48 hours."
            lab_ids = ["crewrostering", "flashqueue", "automatch"]
        elif p3_title or p3_matches:
            pillar = StrategicPillar.AI_APM
            label = "Early-Stage APM / AI PM / Technical PM"
            confidence = 0.90 if p3_title else 0.75
            matched = p3_matches
            narrative = "Technical PM with Scaler Quora System Design rigor: designed HireFlo 1,000-doc parsing pipeline (98% precision) and cut Llama 3.1 compute costs by 40% via NVIDIA NIM & strict JSON schema contracts."
            lab_ids = ["payrouter", "evalguard", "flashqueue"]
        else:
            # Default fallback based on stage and sector
            if is_seed_stage:
                pillar = StrategicPillar.FOUNDERS_OFFICE
                label = "Founder's Office / Generalist Operator"
                confidence = 0.70
                matched = ["early-stage founder leverage"]
                narrative = "Hands-on founder operator capable of driving 0-to-1 operational execution and taking cross-functional fires off the founding team's desk."
                lab_ids = ["crewrostering", "automatch", "evalguard"]
            else:
                pillar = StrategicPillar.AI_APM
                label = "Associate Product Manager"
                confidence = 0.70
                matched = ["startup product execution"]
                narrative = "Technical product manager focused on execution velocity, PRDs, and quantifiable business outcomes."
                lab_ids = ["payrouter", "evalguard", "crewrostering"]

        # CTC Band calculation
        if pillar == StrategicPillar.EVENT_OPERATIONS:
            ctc_band = {"min_lpa": 5.5, "max_lpa": 7.5, "quoted": 6.5}
        elif is_seed_stage:
            ctc_band = {"min_lpa": 6.0, "max_lpa": 8.5, "quoted": 7.0}
        else:
            ctc_band = {"min_lpa": 9.0, "max_lpa": 13.0, "quoted": 10.5}

        return ClassificationResult(
            pillar=pillar,
            pillar_label=label,
            confidence=confidence,
            matched_keywords=matched,
            narrative_focus=narrative,
            primary_pm_lab_ids=lab_ids,
            suggested_ctc_band=ctc_band
        )

