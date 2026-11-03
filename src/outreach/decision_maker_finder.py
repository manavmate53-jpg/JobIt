"""
JobIt v2.0 - Decision Maker Finder
Discovers and constructs contact profiles for Founders, Heads of Product, and Talent Leads,
generating email permutations and targeted LinkedIn search URLs.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContactProfile:
    name: str
    title: str
    first_name: str
    last_name: str
    email_permutations: List[str]
    linkedin_search_url: str
    role_priority: int  # 1: Founder/Co-founder, 2: Head/VP Product, 3: Talent Lead


class DecisionMakerFinder:
    """Finds high-leverage decision makers and generates contact vectors."""

    def __init__(self):
        pass

    def clean_domain(self, company_name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9]", "", company_name).lower()
        return f"{clean}.com"

    def generate_email_permutations(self, first_name: str, last_name: str, domain: str) -> List[str]:
        fn = re.sub(r"[^a-zA-Z]", "", first_name).lower()
        ln = re.sub(r"[^a-zA-Z]", "", last_name).lower()

        if not fn:
            return [f"founder@{domain}", f"hiring@{domain}", f"careers@{domain}"]

        perms = [
            f"{fn}@{domain}",
            f"{fn}.{ln}@{domain}" if ln else f"{fn}@{domain}",
            f"{fn}{ln}@{domain}" if ln else f"{fn}@{domain}",
            f"{fn[0]}{ln}@{domain}" if ln else f"{fn}@{domain}",
            f"careers@{domain}"
        ]
        # Remove duplicates while preserving order
        seen = set()
        deduped = []
        for p in perms:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return deduped

    def generate_linkedin_search_url(self, company_name: str, target_role: str) -> str:
        query = f'"{company_name}" "{target_role}"'
        encoded = urllib.parse.quote(query)
        return f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER"

    def identify_targets(
        self,
        company_name: str,
        founder_names: Optional[List[str]] = None,
        pillar: str = "PILLAR_1_FOUNDERS_OFFICE"
    ) -> List[ContactProfile]:
        domain = self.clean_domain(company_name)
        profiles = []

        # 1. Primary Founder(s)
        founders = founder_names or ["Founder"]
        for name in founders:
            parts = name.strip().split()
            fn = parts[0] if parts else "Founder"
            ln = parts[-1] if len(parts) > 1 else ""

            profiles.append(
                ContactProfile(
                    name=name,
                    title="Founder / CEO",
                    first_name=fn,
                    last_name=ln,
                    email_permutations=self.generate_email_permutations(fn, ln, domain),
                    linkedin_search_url=self.generate_linkedin_search_url(company_name, "Founder"),
                    role_priority=1
                )
            )

        # 2. Functional Leader based on Pillar
        if "PRODUCT" in pillar.upper() or "APM" in pillar.upper():
            profiles.append(
                ContactProfile(
                    name=f"Head of Product, {company_name}",
                    title="Head of Product / VP Product",
                    first_name="Product Lead",
                    last_name="",
                    email_permutations=[f"product@{domain}", f"careers@{domain}"],
                    linkedin_search_url=self.generate_linkedin_search_url(company_name, "Head of Product"),
                    role_priority=2
                )
            )

        # 3. Talent Acquisition / Recruiting Lead
        profiles.append(
            ContactProfile(
                name=f"Talent Lead, {company_name}",
                title="Lead Recruiter / Head of Talent",
                first_name="Hiring Team",
                last_name="",
                email_permutations=[f"talent@{domain}", f"hiring@{domain}", f"careers@{domain}"],
                linkedin_search_url=self.generate_linkedin_search_url(company_name, "Talent Lead"),
                role_priority=3
            )
        )

        return profiles
