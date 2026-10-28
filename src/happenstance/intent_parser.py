"""Natural Language Processing (NLP) Intent Parser & Entity Extractor for Happenstance AI.

Translates plain English queries into structured graph search constraints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StructuredQuery:
    """Parsed structured constraints from natural language query."""
    raw_query: str
    target_roles: List[str] = field(default_factory=list)
    target_companies: List[str] = field(default_factory=list)
    target_locations: List[str] = field(default_factory=list)
    target_sectors: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    min_days_since_interaction: Optional[int] = None
    max_days_since_interaction: Optional[int] = None
    max_degree: int = 2
    require_mutual: bool = False
    min_strength_category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "target_roles": self.target_roles,
            "target_companies": self.target_companies,
            "target_locations": self.target_locations,
            "target_sectors": self.target_sectors,
            "keywords": self.keywords,
            "min_days_since_interaction": self.min_days_since_interaction,
            "max_days_since_interaction": self.max_days_since_interaction,
            "max_degree": self.max_degree,
            "require_mutual": self.require_mutual,
            "min_strength_category": self.min_strength_category,
        }


class IntentParser:
    """Parses natural language requests into structured constraints."""

    ROLE_DICTIONARY = {
        "vc": ["VC", "Venture Capitalist", "Investor", "Partner"],
        "investor": ["VC", "Venture Capitalist", "Angel Investor", "Partner"],
        "founder": ["Founder", "Co-Founder", "CEO", "Co-founder & CEO"],
        "ceo": ["CEO", "Chief Executive Officer", "Founder"],
        "pm": ["Product Manager", "Associate Product Manager", "Technical Product Manager", "Group Product Manager"],
        "product manager": ["Product Manager", "Associate Product Manager", "Technical Product Manager"],
        "apm": ["Associate Product Manager", "APM"],
        "tpm": ["Technical Product Manager", "TPM"],
        "engineer": ["Software Engineer", "Staff Engineer", "ML Engineer", "Research Engineer"],
        "colleague": ["Colleague", "Co-worker", "Teammate"],
        "recruiter": ["Recruiter", "Talent Acquisition", "Head of Talent", "Sourcer"],
        "hr": ["Human Resources", "Talent Acquisition", "HR Lead"]
    }

    LOCATION_DICTIONARY = [
        "san francisco", "sf", "bay area", "new york", "nyc",
        "mumbai", "bangalore", "bengaluru", "delhi", "gurgaon", "noida",
        "pune", "hyderabad", "london", "remote", "worldwide"
    ]

    SECTOR_DICTIONARY = [
        "ai", "artificial intelligence", "genai", "llm", "machine learning",
        "developer tools", "devtools", "infrastructure", "saas", "b2b",
        "fintech", "crypto", "web3", "ecommerce", "logistics", "supply chain",
        "healthcare", "biotech"
    ]

    COMPANY_DICTIONARY = [
        "google", "meta", "facebook", "apple", "amazon", "microsoft", "netflix",
        "perplexity", "perplexity ai", "together ai", "llamaindex", "posthog",
        "zepto", "dukaan", "groww", "klub", "cashflo", "sarvam ai", "replit",
        "elevenlabs", "deel", "cursor", "invideo", "korbit", "superops", "landeed",
        "gupshup", "sprinto", "cred", "jupiter", "shiprocket", "stripe", "atlassian"
    ]

    def parse(self, text: str) -> StructuredQuery:
        """Parses a natural language query into a StructuredQuery."""
        lowered = text.lower().strip()
        query = StructuredQuery(raw_query=text)

        # 1. Extract Roles
        for key, synonyms in self.ROLE_DICTIONARY.items():
            pattern = rf"\b{re.escape(key)}s?\b"
            if re.search(pattern, lowered):
                for syn in synonyms:
                    if syn not in query.target_roles:
                        query.target_roles.append(syn)

        # 2. Extract Locations
        for loc in self.LOCATION_DICTIONARY:
            pattern = rf"\b{re.escape(loc)}\b"
            if re.search(pattern, lowered):
                loc_clean = loc.title()
                if loc_clean == "Sf":
                    loc_clean = "San Francisco"
                elif loc_clean == "Nyc":
                    loc_clean = "New York"
                if loc_clean not in query.target_locations:
                    query.target_locations.append(loc_clean)

        # 3. Extract Sectors
        for sec in self.SECTOR_DICTIONARY:
            pattern = rf"\b{re.escape(sec)}\b"
            if re.search(pattern, lowered):
                sec_clean = sec.upper() if sec in ("ai", "llm", "saas", "b2b") else sec.title()
                if sec_clean not in query.target_sectors:
                    query.target_sectors.append(sec_clean)

        # 4. Extract Companies
        for comp in self.COMPANY_DICTIONARY:
            pattern = rf"\b{re.escape(comp)}\b"
            if re.search(pattern, lowered):
                comp_clean = comp.title()
                if "Ai" in comp_clean:
                    comp_clean = comp_clean.replace("Ai", "AI")
                if comp_clean not in query.target_companies:
                    query.target_companies.append(comp_clean)

        # 5. Temporal Constraints
        # "haven't spoken to in 6 months", "not spoken in 180 days", "last spoken > 6 months"
        month_match = re.search(r"(?:haven['’]t spoken|not spoken|last spoken|no contact).*?(\d+)\s*month", lowered)
        if month_match:
            months = int(month_match.group(1))
            query.min_days_since_interaction = months * 30

        day_match = re.search(r"(?:haven['’]t spoken|not spoken|last spoken|no contact).*?(\d+)\s*day", lowered)
        if day_match:
            days = int(day_match.group(1))
            query.min_days_since_interaction = days

        recent_match = re.search(r"(?:recently|last|within)\s*(\d+)\s*(?:month|day|week)", lowered)
        if recent_match and "haven't" not in lowered and "not" not in lowered:
            raw_val = int(recent_match.group(1))
            if "month" in lowered:
                query.max_days_since_interaction = raw_val * 30
            elif "week" in lowered:
                query.max_days_since_interaction = raw_val * 7
            else:
                query.max_days_since_interaction = raw_val

        # 6. Path Constraints & Mutuals
        if any(term in lowered for term in ["mutual", "introduce", "intro", "warm referral", "friend can", "friend introduce"]):
            query.require_mutual = True
            query.max_degree = 2

        if any(term in lowered for term in ["close friend", "strong connection", "best friend"]):
            query.min_strength_category = "Strong Connection"

        if any(term in lowered for term in ["direct", "1st degree", "my contacts", "people i know"]):
            if "mutual" not in lowered and "introduce" not in lowered:
                query.max_degree = 1

        # 7. Extract remaining keywords
        words = re.findall(r"\b[A-Za-z0-9_-]{3,}\b", text)
        stop_words = {
            "find", "show", "who", "whom", "have", "haven", "not", "with", "from", "now",
            "working", "early", "stage", "startup", "startups", "invest", "can", "introduce",
            "someone", "people", "contacts", "network", "which", "that", "this", "they"
        }
        query.keywords = [w for w in words if w.lower() not in stop_words][:8]

        return query
