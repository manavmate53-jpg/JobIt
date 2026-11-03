"""
JobIt v2.0 - Wellfound & Startup Cross-Check Engine
Matches funded startups to potential or confirmed open roles on Wellfound, Cutshort,
and startup career boards across the 3 strategic pillars.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from src.signals.funding_scraper import FundingSignal

logger = logging.getLogger(__name__)


@dataclass
class StartupOpportunity:
    company_name: str
    funding_stage: str
    amount_raised: str
    sector: str
    hq_location: str
    founder_names: List[str]
    suggested_role: str
    pillar: str  # FOUNDERS_OFFICE, PRODUCT_OPERATIONS, AI_APM
    wellfound_url: str
    careers_url: str
    key_pitch_hook: str
    source_signal_url: str


class WellfoundCrossChecker:
    """Matches funded tech companies with high-intent hiring needs across 3 pillars."""

    def __init__(self):
        # Slug overrides for known startups
        self.slug_overrides = {
            "Portkey": "portkey-ai",
            "Sarvam AI": "sarvam-ai",
            "SuperOps": "superops-ai",
            "GrayQuest": "grayquest",
            "Finvolv": "finvolv",
            "Spendflo": "spendflo",
            "Atlan": "atlan",
            "Toddle": "toddle",
            "Kula": "kula-app",
            "Ultrahuman": "ultrahuman",
            "Cashfree Payments": "cashfree",
            "Zepto": "zepto-app"
        }

    def generate_slug(self, company_name: str) -> str:
        if company_name in self.slug_overrides:
            return self.slug_overrides[company_name]
        slug = re.sub(r"[^a-zA-Z0-9\s]", "", company_name).strip().lower()
        slug = re.sub(r"\s+", "-", slug)
        return slug

    def infer_primary_pillar(self, signal: FundingSignal) -> str:
        """
        Determines the most strategic pillar to lead with based on stage & sector.
        - Seed / Pre-Series A (<$5M): Founder's Office / Chief of Staff (highest founder leverage)
        - Logistics / Quick Commerce / Ops-heavy: Product Operations Manager
        - AI / Developer Tools / Fintech / Series A+: AI APM / Technical PM
        """
        sec = signal.sector.lower()
        stage = signal.funding_stage.lower()

        if "logistics" in sec or "operations" in sec or "supply chain" in sec or "quick commerce" in sec:
            return "PRODUCT_OPERATIONS"

        if "seed" in stage or "pre-series a" in stage or "angel" in stage:
            return "FOUNDERS_OFFICE"

        if "ai" in sec or "developer tools" in sec or "fintech" in sec:
            return "AI_APM"

        return "FOUNDERS_OFFICE"

    def match_opportunity(self, signal: FundingSignal) -> StartupOpportunity:
        """Constructs a high-intent opportunity from a funding signal."""
        slug = self.generate_slug(signal.company_name)
        wellfound_url = f"https://wellfound.com/company/{slug}/jobs"
        careers_url = f"https://www.{slug}.com/careers"

        pillar = self.infer_primary_pillar(signal)

        if pillar == "FOUNDERS_OFFICE":
            suggested_role = "Founder's Office / Strategy & Operations Lead"
            pitch_hook = f"Helping the founding team scale {signal.company_name} post-{signal.funding_stage} round by taking operational execution and 0-to-1 workflows off your plate."
        elif pillar == "PRODUCT_OPERATIONS":
            suggested_role = "Product Operations Manager / Operations PM"
            pitch_hook = f"Bridging {signal.company_name}'s high-growth field operations with automated tracking systems to maintain 100% SLA compliance as transaction volume surges."
        else:
            suggested_role = "Associate Product Manager / AI Systems PM"
            pitch_hook = f"Driving rigorous PRDs, API contracts, and model unit economics for {signal.company_name}'s core platform features with zero hand-holding."

        return StartupOpportunity(
            company_name=signal.company_name,
            funding_stage=signal.funding_stage,
            amount_raised=signal.amount_raised,
            sector=signal.sector,
            hq_location=signal.hq_location,
            founder_names=signal.founder_names,
            suggested_role=suggested_role,
            pillar=pillar,
            wellfound_url=wellfound_url,
            careers_url=careers_url,
            key_pitch_hook=pitch_hook,
            source_signal_url=signal.source_url
        )

    def crosscheck_all(self, signals: List[FundingSignal]) -> List[StartupOpportunity]:
        return [self.match_opportunity(sig) for sig in signals]

