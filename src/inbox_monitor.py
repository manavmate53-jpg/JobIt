"""Inbox & Recruiter Reply Monitor for JobIt.

Connects securely via IMAP to monitor incoming recruiter replies, interview invites,
and status updates for tracked job applications.
"""

from __future__ import annotations

import email
from email.header import decode_header
import imaplib
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def clean_header_str(val: Any) -> str:
    """Decodes MIME encoded header strings."""
    if not val:
        return ""
    decoded_parts = decode_header(val)
    out = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            out.append(part.decode(encoding or "utf-8", errors="ignore"))
        else:
            out.append(str(part))
    return " ".join(out).strip()


class InboxMonitor:
    """Scans user inbox for responses from companies tracked in JobIt applications."""

    def __init__(
        self,
        imap_server: Optional[str] = None,
        email_user: Optional[str] = None,
        email_password: Optional[str] = None,
    ):
        self.imap_server = imap_server or os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.email_user = email_user or os.getenv("SMTP_USER") or os.getenv("EMAIL_USER", "manavmate53@gmail.com")
        self.email_password = email_password or os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD", "")

    def is_configured(self) -> bool:
        """Checks if IMAP credentials are provided."""
        return bool(self.email_user and self.email_password and "your_gmail" not in self.email_password)

    def check_for_replies(self, tracked_companies: List[str], max_emails: int = 50) -> List[Dict[str, Any]]:
        """Connects to IMAP server and checks recent emails for replies from tracked companies."""
        if not self.is_configured():
            logger.warning("IMAP inbox credentials not configured in .env.")
            return []

        replies_found = []
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_password)
            mail.select("INBOX")

            # Search recent emails
            status, messages = mail.search(None, "ALL")
            if status != "OK" or not messages[0]:
                mail.logout()
                return []

            email_ids = messages[0].split()
            # Check latest max_emails
            recent_ids = email_ids[-max_emails:]

            for eid in reversed(recent_ids):
                status, msg_data = mail.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = clean_header_str(msg.get("Subject", ""))
                        sender = clean_header_str(msg.get("From", ""))
                        date = clean_header_str(msg.get("Date", ""))

                        # Check if sender matches any tracked company or relevant recruitment terms
                        sender_lower = sender.lower()
                        subject_lower = subject.lower()

                        matched_company = None
                        for comp in tracked_companies:
                            comp_clean = comp.lower().strip()
                            if comp_clean and comp_clean in sender_lower or comp_clean in subject_lower:
                                matched_company = comp
                                break

                        # Identify intent keywords
                        is_interview = any(kw in subject_lower for kw in ["interview", "discussion", "shortlisted", "next steps", "round 1", "connect"])
                        is_rejection = any(kw in subject_lower for kw in ["unfortunately", "not moving forward", "other candidates", "update on your application"])

                        if matched_company or is_interview or is_rejection:
                            replies_found.append({
                                "id": eid.decode(),
                                "company": matched_company or "Unknown",
                                "sender": sender,
                                "subject": subject,
                                "date": date,
                                "is_interview": is_interview,
                                "is_rejection": is_rejection,
                            })

            mail.logout()
        except Exception as e:
            logger.error(f"Error accessing IMAP inbox: {e}")

        return replies_found
