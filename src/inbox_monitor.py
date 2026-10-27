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
from dotenv import load_dotenv

load_dotenv()

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
        self.email_user = email_user if email_user is not None else (os.getenv("SMTP_USER") or os.getenv("EMAIL_USER", "manavmate53@gmail.com"))
        raw_pw = email_password if email_password is not None else (os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD", ""))
        self.email_password = raw_pw.replace(" ", "")


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
            recent_ids = email_ids[-max_emails:]

            # Exclude commercial noise keywords
            promotional_noise = ["order", "delivered", "delivery", "cashback", "sale", "discount", "statement", "otp", "debit card", "credit card", "promo", "newsletter", "webinar", "digest"]

            recruitment_keywords = [
                "application", "job", "career", "interview", "candidate", "hiring",
                "talent", "recruitment", "shortlisted", "assessment", "screening",
                "next steps", "profile", "resume", "cv", "round 1", "round 2",
                "position", "opportunity", "product manager", "apm"
            ]

            id_set = b",".join(recent_ids)
            status, msg_data = mail.fetch(id_set, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
            if status != "OK" or not msg_data:
                mail.logout()
                return []

            for response_part in reversed(msg_data):
                if isinstance(response_part, tuple) and len(response_part) > 1:
                    msg = email.message_from_bytes(response_part[1])
                    subject = clean_header_str(msg.get("Subject", ""))
                    sender = clean_header_str(msg.get("From", ""))
                    date = clean_header_str(msg.get("Date", ""))


                    sender_lower = sender.lower()
                    subject_lower = subject.lower()

                    # Skip obvious commercial noise
                    if any(noise in subject_lower for noise in promotional_noise) and not any(rk in subject_lower for rk in ["application", "interview", "job", "career"]):
                        continue

                    matched_company = None
                    for comp in tracked_companies:
                        comp_clean = comp.lower().strip()
                        # Ensure company name is at least 3 chars to avoid false substring matches
                        if len(comp_clean) >= 3:
                            if f"@{comp_clean}." in sender_lower or f" {comp_clean} " in f" {sender_lower} " or f" {comp_clean} " in f" {subject_lower} ":
                                matched_company = comp
                                break

                    has_recruitment_intent = any(kw in subject_lower or kw in sender_lower for kw in recruitment_keywords)

                    is_interview = any(kw in subject_lower for kw in [
                        "interview", "invitation to interview", "shortlisted",
                        "schedule an interview", "interview with", "round 1",
                        "next steps", "screening call"
                    ])

                    is_rejection = any(kw in subject_lower for kw in [
                        "unfortunately", "not moving forward", "other candidates",
                        "update on your application", "status of your application"
                    ])

                    if (matched_company and has_recruitment_intent) or is_interview or is_rejection:
                        msg_id = response_part[0].split()[0].decode() if isinstance(response_part[0], bytes) else "msg"
                        replies_found.append({
                            "id": msg_id,
                            "company": matched_company or "Recruitment Update",
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
