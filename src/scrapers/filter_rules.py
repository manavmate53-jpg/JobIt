"""Negative Filtering & Domain Trap Detector.

Automatically discards irrelevant, mislabeled, or off-target listings:
- Physical manufacturing / factory operations (mattresses, foam, plant engineering, injection molding)
- Pharmaceutical brand marketing (HCP marketing, clinical detailing, vaccines)
- Offline vehicle / equipment NBFC financing (tractor loans, commercial vehicle branch credit)
- Corporate positions requiring 5+ mandatory years of corporate enterprise product management
"""

import re
from typing import Optional, Tuple


# Regex patterns for negative domain traps
MANUFACTURING_KEYWORDS = [
    r"\bmattress(?:es)?\b",
    r"\bfoam\s+production\b",
    r"\bplastic\s+furniture\b",
    r"\bthe\s+sleep\s+company\b",
    r"\bsleepwell\b",
    r"\bwakefit\b",
    r"\bkurl-?on\b",
    r"\bduroflex\b",
    r"\bplant\s+engineering\b",
    r"\binjection\s+molding\b",
    r"\bcasting\b",
    r"\bextrusion\b",
    r"\bboiler\s+operator\b",
    r"\btextile\s+mill\b",
    r"\bchemical\s+factory\b",
    r"\bshop\s+floor\b",
    r"\bfoundry\b",
    r"\bmetal\s+fabrication\b",
    r"\bassembly\s+line\s+supervisor\b",
]

PHARMA_KEYWORDS = [
    r"\bhcp\s+marketing\b",
    r"\bclinical\s+detailing\b",
    r"\bmedical\s+vaccines?\b",
    r"\bpharma(?:ceutical)?\s+sales\b",
    r"\bprescribing\s+doctors?\b",
    r"\bmedical\s+representative\b",
    r"\bmr\s+brand\s+manager\b",
    r"\btherapeutics\s+marketing\b",
    r"\bpharmacovigilance\b",
    r"\bformulation\s+plant\b",
]

OFFLINE_FINANCE_KEYWORDS = [
    r"\bconstruction\s+equipment\s+loans?\b",
    r"\bcommercial\s+vehicle\s+branch\b",
    r"\btractor\s+loans?\b",
    r"\bused\s+car\s+branch\s+credit\b",
    r"\bnbfc\s+collections?\b",
    r"\brepossession\s+officer\b",
    r"\btwo\s+wheeler\s+loan\s+underwriter\b",
    r"\bbranch\s+credit\s+manager\b",
]

FOUNDER_OFFICE_KEYWORDS = [
    r"\bfounder'?s?\s+office\b",
    r"\bchief\s+of\s+staff\b",
]

SENIOR_YEARS_PATTERNS = [
    r"\b(?:minimum|at\s+least|requires?)\s*(?:of\s*)?([5-9]|[1-2][0-9])\+?\s*years?\b",
    r"\b([5-9]|[1-2][0-9])\+?\s*years?(?:\s*of)?\s*(?:corporate\s+|enterprise\s+)?(?:product\s+management|pm\s+experience)\b",
    r"\b(?:director|vp|vice\s+president|head)\s+of\s+product\b",
    r"\bchief\s+product\s+officer\b",
    r"\bprincipal\s+product\s+manager\b",
    r"\bgroup\s+product\s+manager\b",
]


def check_negative_filters(
    title: str,
    company: str,
    description: str,
    experience_text: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Evaluates whether a job posting falls into any negative domain traps.

    Returns:
        (is_valid, reject_reason): If invalid, is_valid is False and reason explains why.
    """
    full_text = f"{title} {company} {description} {experience_text or ''}".lower()

    # 1. Check physical manufacturing
    for pat in MANUFACTURING_KEYWORDS:
        if re.search(pat, full_text, flags=re.IGNORECASE):
            return False, f"Domain Trap: Physical manufacturing / factory operations ({pat})"

    # 2. Check pharma marketing
    for pat in PHARMA_KEYWORDS:
        if re.search(pat, full_text, flags=re.IGNORECASE):
            return False, f"Domain Trap: Pharmaceutical brand marketing ({pat})"

    # 3. Check offline NBFC vehicle financing
    for pat in OFFLINE_FINANCE_KEYWORDS:
        if re.search(pat, full_text, flags=re.IGNORECASE):
            return False, f"Domain Trap: Offline vehicle/equipment NBFC financing ({pat})"

    # 4. Check Founder's Office (Candidate Preference)
    for pat in FOUNDER_OFFICE_KEYWORDS:
        if re.search(pat, full_text, flags=re.IGNORECASE):
            return False, f"Candidate Preference: Founder's Office skipped ({pat})"

    # 5. Check mandatory 5+ years corporate PM gate
    # Check title first (e.g. Vice President, VP, Director, Head of Product, Principal)
    title_lower = title.lower()
    senior_title_patterns = [
        r"\bvice\s+president\b",
        r"\bvp\b",
        r"\bdirector\b",
        r"\bhead\s+of\s+product\b",
        r"\bchief\s+product\s+officer\b",
        r"\bprincipal\s+(?:product|pm)\b",
        r"\bgroup\s+product\s+manager\b",
        r"\bgeneral\s+manager\b",
    ]
    for pat in senior_title_patterns:
        if re.search(pat, title_lower, flags=re.IGNORECASE):
            return False, f"Seniority Trap: Title indicates executive hierarchy ({pat})"

    # Check experience text and description
    for pat in SENIOR_YEARS_PATTERNS:
        match = re.search(pat, full_text, flags=re.IGNORECASE)
        if match:
            # Check if this is a negative sentence like 'doesn't require 5 years'
            start = max(0, match.start() - 30)
            prefix = full_text[start:match.start()]
            if any(neg in prefix for neg in ["not", "no ", "without"]):
                continue
            return False, f"Experience Gate: Requires 5+ years corporate PM experience ({match.group(0)})"

    return True, None
