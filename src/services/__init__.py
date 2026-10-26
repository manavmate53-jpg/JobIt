"""JobIt Tailoring & ATS Matching Services.

Adopts the modular, deterministic architecture of Resume-Matcher:
- ATSScorer: 5-signal weighted composite ATS score (keywords, skills, title, completeness, dates).
- BulletSelector: Dynamic achievement relevance scoring and ordering.
- KeywordAligner: Natural JD keyword extraction and competency alignment.
- WritingQualityAudit: Em dash scrubbing, weak opener removal, and metric preservation.
- PageFitValidator: Single-page A4 vertical height and word budget enforcement.
"""

from src.services.ats_scorer import ATSScorer, ATSReport
from src.services.bullet_selector import BulletSelector
from src.services.keyword_aligner import KeywordAligner
from src.services.writing_quality import WritingQualityAudit
from src.services.page_fit import PageFitValidator

__all__ = [
    "ATSScorer",
    "ATSReport",
    "BulletSelector",
    "KeywordAligner",
    "WritingQualityAudit",
    "PageFitValidator",
]
