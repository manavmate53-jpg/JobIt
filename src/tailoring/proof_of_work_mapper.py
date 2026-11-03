"""
JobIt v2.0 - Proof of Work Mapper
Selects the exact 3 PM Lab interactive builds matching the target company domain.
Live interactive hub: https://manavmate53-jpg.github.io/pm-product-lab/#hub
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class PMLabBuild:
    id: str
    name: str
    category: str
    url: str
    summary: str
    key_metrics: str
    domains: List[str]


ALL_PM_LAB_BUILDS: Dict[str, PMLabBuild] = {
    "payrouter": PMLabBuild(
        id="payrouter",
        name="PayRouter Engine",
        category="Fintech & Smart Routing",
        url="https://manavmate53-jpg.github.io/pm-product-lab/#payrouter",
        summary="Smart cascading payment router with sub-200ms failover, gateway health monitoring, MDR optimization, and refund idempotency.",
        key_metrics="Sub-200ms failover, 15-45 bps lower MDR fees",
        domains=["fintech", "payments", "bfsi", "e-commerce", "b2b saas"]
    ),
    "flashqueue": PMLabBuild(
        id="flashqueue",
        name="FlashQueue Simulator",
        category="High Scale & Infrastructure",
        url="https://manavmate53-jpg.github.io/pm-product-lab/#flashqueue",
        summary="High-concurrency virtual waiting room buffering 50,000+ user surges, mitigating 504 timeouts via token bucket rate limiting.",
        key_metrics="50,000+ user surge buffer, zero 504 timeouts",
        domains=["logistics", "quick commerce", "ticketing", "marketplaces", "consumer tech", "infra"]
    ),
    "crewrostering": PMLabBuild(
        id="crewrostering",
        name="CrewRoster Dashboard",
        category="Operations PM & Workforce Tech",
        url="https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering",
        summary="Frontline workforce rostering and SLA escalation system with automated standby dispatch buffers and QR attendance audit (modeled on NeoManpower operations).",
        key_metrics="100% SLA compliance, 48-hr reconciliation",
        domains=["operations", "workforce", "supply chain", "logistics", "field services", "b2b saas"]
    ),
    "verishield": PMLabBuild(
        id="verishield",
        name="VeriShield",
        category="B2B KYC & Verification",
        url="https://manavmate53-jpg.github.io/pm-product-lab/#verishield",
        summary="B2B KYC and GSTIN/PAN verification engine with fuzzy entity matching, automated sanctions checking, and risk routing.",
        key_metrics="Sub-800ms verification, 12-point checks",
        domains=["fintech", "compliance", "identity", "b2b saas", "legaltech", "lending"]
    ),
    "automatch": PMLabBuild(
        id="automatch",
        name="AutoMatch IQ",
        category="Marketplace & Discovery",
        url="https://manavmate53-jpg.github.io/pm-product-lab/#automatch",
        summary="Marketplace discovery flow with live event telemetry, candidate scoring heuristics, and embedded SQL runner.",
        key_metrics="24% conversion bottleneck resolved",
        domains=["marketplaces", "recruitment", "e-commerce", "growth", "discovery"]
    ),
    "evalguard": PMLabBuild(
        id="evalguard",
        name="EvalGuard AI",
        category="B2B SaaS & Production AI",
        url="https://manavmate53-jpg.github.io/pm-product-lab/#evalguard",
        summary="Production LLM agent with JSON schema guardrails, human-in-the-loop escalation triggers, and token unit economics benchmarking.",
        key_metrics="99.4% schema compliance, 40% cost reduction",
        domains=["ai", "genai", "b2b saas", "developer tools", "automation"]
    )
}


class ProofOfWorkMapper:
    """Matches company domain and role pillar to the top 3 PM Lab builds."""

    def select_top_3_builds(
        self,
        sector: str,
        pillar: str,
        company_name: str = ""
    ) -> List[PMLabBuild]:
        sec = sector.lower()
        pil = pillar.upper()

        # Sector-specific rules
        if "fintech" in sec or "payment" in sec or "credit" in sec or "lending" in sec:
            selected_ids = ["payrouter", "verishield", "evalguard"]
        elif "logistics" in sec or "quick commerce" in sec or "delivery" in sec:
            selected_ids = ["flashqueue", "crewrostering", "automatch"]
        elif "ai" in sec or "genai" in sec or "developer tools" in sec:
            selected_ids = ["evalguard", "flashqueue", "payrouter"]
        elif "recruitment" in sec or "hr" in sec or "marketplace" in sec:
            selected_ids = ["automatch", "crewrostering", "evalguard"]
        elif "operations" in sec or "supply chain" in sec or "b2b" in sec:
            if "FOUNDERS_OFFICE" in pil:
                selected_ids = ["crewrostering", "automatch", "evalguard"]
            elif "PRODUCT_OPERATIONS" in pil:
                selected_ids = ["crewrostering", "flashqueue", "automatch"]
            else:
                selected_ids = ["evalguard", "payrouter", "flashqueue"]
        else:
            # General defaults based on pillar
            if "FOUNDERS_OFFICE" in pil:
                selected_ids = ["crewrostering", "evalguard", "automatch"]
            elif "PRODUCT_OPERATIONS" in pil:
                selected_ids = ["crewrostering", "flashqueue", "verishield"]
            else:
                selected_ids = ["evalguard", "payrouter", "flashqueue"]

        return [ALL_PM_LAB_BUILDS[bid] for bid in selected_ids if bid in ALL_PM_LAB_BUILDS]
