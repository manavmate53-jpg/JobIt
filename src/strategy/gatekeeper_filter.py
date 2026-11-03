"""
JobIt v2.0 - Gatekeeper Filter
Hard degree-gate bypass and blacklist enforcement. Blocks legacy banks, IT services MNCs,
non-tech traps, and >3-year seniority traps before any compute or outreach is wasted.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GatekeeperResult:
    passed: bool
    drop_reason: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    bypassed_degree_gate: bool = False


class GatekeeperFilter:
    """Evaluates companies and job postings against hard blacklists and degree gates."""

    def __init__(self, filter_matrix_path: Optional[Path] = None):
        matrix_path = filter_matrix_path or Path("config/filter_matrix.json")
        self.legacy_banks = []
        self.it_services_mncs = []
        self.non_tech_traps = []
        self.seniority_traps = []
        self.forbidden_requirements = []
        self.allowed_titles = []

        if matrix_path.exists():
            with open(matrix_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                bl = cfg.get("blacklist", {})
                self.legacy_banks = [x.lower() for x in bl.get("legacy_banks", [])]
                self.it_services_mncs = [x.lower() for x in bl.get("it_services_mncs", [])]
                self.non_tech_traps = [x.lower() for x in bl.get("non_tech_traps", [])]
                self.seniority_traps = [x.lower() for x in bl.get("seniority_traps", [])]
                self.forbidden_requirements = [x.lower() for x in bl.get("forbidden_requirements", [])]
                wl = cfg.get("whitelist", {})
                self.allowed_titles = [x.lower() for x in wl.get("allowed_titles", [])]

    def evaluate(
        self,
        company_name: str,
        role_title: str = "",
        job_description: str = "",
        requirements: str = ""
    ) -> GatekeeperResult:
        comp = company_name.lower().strip()
        tit = role_title.lower().strip()
        desc = (job_description + " " + requirements).lower()
        flags: List[str] = []

        # 1. Check Legacy Banks
        for bank in self.legacy_banks:
            # Word-boundary or exact token check
            pattern = r"\b" + re.escape(bank) + r"\b"
            if re.search(pattern, comp) or bank == comp:
                return GatekeeperResult(
                    passed=False,
                    drop_reason=f"Blacklisted Legacy Bank: '{company_name}' ({bank}) enforces rigid corporate degree gates",
                    flags=["BLACKLIST_BANK"]
                )

        # 2. Check IT Services MNCs
        for mnc in self.it_services_mncs:
            pattern = r"\b" + re.escape(mnc) + r"\b"
            if re.search(pattern, comp) or mnc == comp:
                return GatekeeperResult(
                    passed=False,
                    drop_reason=f"Blacklisted IT Services MNC: '{company_name}' ({mnc}) filters via automated resume screening bots",
                    flags=["BLACKLIST_IT_MNC"]
                )

        # 3. Check Seniority Traps
        for sen in self.seniority_traps:
            if sen in tit:
                return GatekeeperResult(
                    passed=False,
                    drop_reason=f"Seniority Trap: '{role_title}' targets 5+ year corporate leads or principals",
                    flags=["SENIORITY_OVERFLOW"]
                )

        # 4. Check Non-Tech Traps
        for trap in self.non_tech_traps:
            if trap in desc or trap in tit:
                return GatekeeperResult(
                    passed=False,
                    drop_reason=f"Non-Tech Industry Trap: Detected '{trap}' domain",
                    flags=["NON_TECH_SECTOR"]
                )

        # 5. Check Explicit Degree or High-Year Filters in Description
        bypassed_degree = False
        if any(term in desc for term in ["b.tech mandatory", "iit/nit only", "premier engineering college"]):
            flags.append("PORTAL_DEGREE_GATE_DETECTED")
            bypassed_degree = True

        for req in self.forbidden_requirements:
            if req in desc:
                return GatekeeperResult(
                    passed=False,
                    drop_reason=f"Disqualifying Requirement: '{req}' found in job description",
                    flags=["YEARS_EXPERIENCE_GATE"]
                )

        # Passed all gatekeeper filters
        return GatekeeperResult(
            passed=True,
            drop_reason=None,
            flags=flags,
            bypassed_degree_gate=bypassed_degree
        )
