"""Writing Quality & Fact Preservation Rules.

Inspired by Resume-Matcher's writing_quality and resume_preservation services.
Enforces:
1. Strict typography rules (zero em dashes, zero double hyphens).
2. Elimination of weak passive openers ("responsible for", "assisted with").
3. Anti-hallucination fact preservation (auditing quantitative metrics against candidate ground truth).
4. Bullet conciseness and punch (under 35 words).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

# Forbidden typography patterns
EM_DASH_RE = re.compile(r"—|–|(?<![\w-])-{2,3}(?![\w-])|(?<=\w)-{2,3}(?=\w)")

# Weak passive openers to eradicate
WEAK_OPENERS = [
    "responsible for",
    "helped with",
    "helped to",
    "assisted with",
    "assisted in",
    "participated in",
    "involved in",
    "worked on",
    "tasked with",
    "duties included",
    "in charge of",
]

# Replacement action map for weak openers
OPENER_REPLACEMENTS = {
    "responsible for": "led",
    "helped with": "collaborated on",
    "assisted in": "built",
    "participated in": "drove",
    "tasked with": "owned",
    "duties included": "delivered",
}

# Corporate buzzwords blacklist
CORPORATE_BUZZWORDS = [
    r"\bspearheaded synergistic\b",
    r"\bsynergies\b",
    r"\bholistic paradigm\b",
    r"\bthought leader\b",
    r"\bvisionary maven\b",
    r"\bvalue-add proposition\b",
    r"\bleveraged holistic\b",
]

# Ground-truth authorized numbers and metrics for Manav Mate
GROUND_TRUTH_NUMBERS: Set[str] = {
    "40", "40%", "1000", "1,000", "10", "30", "30%", "14", "14+", "98", "98%",
    "50", "50+", "200", "200+", "133", "12", "48", "99.4", "99.4%", "35", "35%",
    "800", "800ms", "12", "24", "24%", "45", "7", "5000", "5,000", "5,000+",
    "8", "11", "16", "2022", "2025", "2026", "0", "1", "2", "3"
}


class WritingQualityAudit:
    """Performs static linting and rewriting on resume content to guarantee builder standards."""

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Removes em dashes, double dashes, and corporate buzzwords while preserving whitespace."""
        if not text:
            return ""

        # 1. Clean em dashes and double hyphens
        cleaned = EM_DASH_RE.sub(", ", text)

        # 2. Clean weak openers at start of line/bullet
        for weak in WEAK_OPENERS:
            pattern = re.compile(r"^\W*" + re.escape(weak) + r"\b", re.IGNORECASE)
            if pattern.search(cleaned):
                rep = OPENER_REPLACEMENTS.get(weak, "executed")
                cleaned = pattern.sub(rep.capitalize(), cleaned)

        # 3. Strip corporate clichés
        for buzz in CORPORATE_BUZZWORDS:
            cleaned = re.sub(buzz, "led", cleaned, flags=re.IGNORECASE)

        # 4. Clean up punctuation artifacts
        cleaned = re.sub(r"[^\S\r\n]+", " ", cleaned).strip()
        cleaned = re.sub(r"\s*,\s*,", ",", cleaned)
        cleaned = re.sub(r"\s*,\s*\.", ".", cleaned)
        return cleaned

    @classmethod
    def audit_bullet(cls, bullet: str) -> Tuple[bool, List[str]]:
        """Audits a single bullet against word count, forbidden characters, and hallucinated numbers."""
        issues: List[str] = []
        words = bullet.split()

        # Word count check
        if len(words) > 35:
            issues.append(f"Bullet exceeds 35 words ({len(words)} words)")

        # Em dash check
        if "—" in bullet or "--" in bullet:
            issues.append("Contains forbidden em dash or double hyphen")

        # Weak opener check
        lower_bullet = bullet.lower()
        for weak in WEAK_OPENERS:
            if lower_bullet.startswith(weak):
                issues.append(f"Starts with weak opener '{weak}'")

        # Number preservation check (anti-hallucination)
        found_numbers = re.findall(r"\b\d+(?:[.,]\d+)?%?\+?\b", bullet)
        for num in found_numbers:
            clean_num = num.strip("+%")
            if clean_num not in GROUND_TRUTH_NUMBERS and num not in GROUND_TRUTH_NUMBERS:
                issues.append(f"Potentially unauthorized metric detected: '{num}'")

        return len(issues) == 0, issues
