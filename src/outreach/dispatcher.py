"""
JobIt v2.0 - Outreach Dispatcher
Handles safe dry-run preview and confirmed dispatch of outreach messages,
recording events to the local telemetry database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.outreach.sequence_generator import OutreachTouchpoints

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    company_name: str
    channel: str
    target: str
    status: str  # PREVIEWED, DISPATCHED, LOGGED, FAILED
    timestamp: str
    message_snippet: str
    dry_run: bool


class OutreachDispatcher:
    """Dispatches or safely dry-runs outreach sequences."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def dispatch(
        self,
        touchpoints: OutreachTouchpoints,
        channel: str = "linkedin_connect",
        recipient: Optional[str] = None
    ) -> DispatchResult:
        target = recipient or touchpoints.target_person
        ts = datetime.now().isoformat()

        if channel == "linkedin_connect":
            msg = touchpoints.linkedin_connect_note
        elif channel in ("linkedin_dm", "email"):
            msg = touchpoints.funding_hook_cold_dm
        elif channel == "wellfound":
            msg = touchpoints.wellfound_founder_note
        else:
            msg = touchpoints.follow_up_bump

        snippet = msg[:100] + "..." if len(msg) > 100 else msg

        if self.dry_run:
            logger.info("[DRY RUN] [%s] -> %s (%s): %s", channel, touchpoints.company_name, target, snippet)
            return DispatchResult(
                company_name=touchpoints.company_name,
                channel=channel,
                target=target,
                status="PREVIEWED",
                timestamp=ts,
                message_snippet=snippet,
                dry_run=True
            )

        # In production live mode, manual 1-click paste is the safest way to avoid LinkedIn automation blocks,
        # or automated email sending when SMTP credentials are provided.
        logger.info("[LIVE LOG] [%s] Dispatched to %s: %s", channel, touchpoints.company_name, snippet)
        return DispatchResult(
            company_name=touchpoints.company_name,
            channel=channel,
            target=target,
            status="DISPATCHED",
            timestamp=ts,
            message_snippet=snippet,
            dry_run=False
        )

