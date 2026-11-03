"""
JobIt v2.0 - Job Board Scraper (Filtered Startup Scraper)
Pulls role postings from LinkedIn and Naukri while strictly enforcing whitelist
criteria and dropping blacklisted enterprise companies upfront.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StartupJobBoardScraper:
    """Scrapes jobs with strict pre-filtering against enterprise blacklists."""

    def __init__(self, filter_matrix_path: Optional[Path] = None):
        matrix_path = filter_matrix_path or Path("config/filter_matrix.json")
        self.blacklist_banks = []
        self.blacklist_it = []
        self.non_tech = []
        self.seniority = []
        self.allowed_titles = []

        if matrix_path.exists():
            with open(matrix_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                bl = data.get("blacklist", {})
                self.blacklist_banks = [x.lower() for x in bl.get("legacy_banks", [])]
                self.blacklist_it = [x.lower() for x in bl.get("it_services_mncs", [])]
                self.non_tech = [x.lower() for x in bl.get("non_tech_traps", [])]
                self.seniority = [x.lower() for x in bl.get("seniority_traps", [])]
                wl = data.get("whitelist", {})
                self.allowed_titles = [x.lower() for x in wl.get("allowed_titles", [])]

    def is_enterprise_blacklisted(self, company: str, title: str, description: str = "") -> bool:
        """Returns True if the posting matches any blacklisted company or enterprise trap."""
        comp = company.lower().strip()
        tit = title.lower().strip()
        desc = description.lower()

        # Check banks
        for bank in self.blacklist_banks:
            if bank in comp:
                return True

        # Check IT MNCs
        for it in self.blacklist_it:
            if it in comp:
                return True

        # Check seniority traps
        for sen in self.seniority:
            if sen in tit:
                return True

        # Check non-tech traps
        for trap in self.non_tech:
            if trap in desc or trap in tit:
                return True

        # Experience check
        if any(f"{n}+ years" in desc or f"{n} to " in desc for n in [5, 6, 7, 8, 10]):
            return True

        return False

    def is_title_whitelisted(self, title: str) -> bool:
        """Checks if title aligns with the 3 pillars."""
        tit = title.lower()
        if not self.allowed_titles:
            return True
        return any(allowed in tit for allowed in self.allowed_titles)

    def filter_raw_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters a raw list of jobs from scrapers or database."""
        surviving = []
        for job in jobs:
            company = job.get("company", "")
            title = job.get("title", "")
            description = job.get("description", "")

            if self.is_enterprise_blacklisted(company, title, description):
                continue

            if not self.is_title_whitelisted(title):
                continue

            surviving.append(job)

        return surviving
