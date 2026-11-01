"""Automated Email OTP & Verification Code Listener for JobIt.

Polls candidate Gmail via IMAP to automatically capture OTP / verification codes
sent by LinkedIn, Naukri, TurboHire, or application portals without requiring manual copy-pasting.
"""

from __future__ import annotations

import email
import imaplib
import logging
import os
import re
import time
from email.header import decode_header
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger("jobit.otp_listener")


class EmailOTPListener:
    """Extracts OTP / verification codes from incoming candidate emails via IMAP."""

    def __init__(self, env_path: Optional[str] = None):
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        self.imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.email_user = os.getenv("EMAIL_USER", "manavmate53@gmail.com")
        self.email_password = os.getenv("EMAIL_PASSWORD")

    def is_configured(self) -> bool:
        return bool(self.email_user and self.email_password)

    def _clean_header(self, raw_header: str) -> str:
        if not raw_header:
            return ""
        decoded_parts = decode_header(raw_header)
        text = ""
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                text += content.decode(encoding or "utf-8", errors="ignore")
            else:
                text += str(content)
        return text

    def fetch_latest_otp(
        self,
        sender_keyword: Optional[str] = None,
        max_wait_seconds: int = 60,
        poll_interval_seconds: int = 4,
    ) -> Optional[str]:
        """Polls inbox for the most recent OTP/verification code matching sender."""
        if not self.is_configured():
            logger.warning("IMAP credentials not configured. Cannot poll for OTP.")
            return None

        logger.info(
            f"Listening for verification code (Sender: {sender_keyword or 'Any'}, Timeout: {max_wait_seconds}s)..."
        )
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            try:
                mail = imaplib.IMAP4_SSL(self.imap_server)
                mail.login(self.email_user, self.email_password)
                mail.select("INBOX")

                # Search criteria: look for messages matching sender or subject cues
                search_query = 'OR (SUBJECT "code") (SUBJECT "PIN")'
                if sender_keyword:
                    search_query = f'(FROM "{sender_keyword}")'

                status, data = mail.search(None, search_query)
                if status == "OK" and data[0]:
                    msg_ids = data[0].split()
                    if msg_ids:
                        # Check the most recent 3 messages
                        for mid in reversed(msg_ids[-3:]):
                            status, msg_data = mail.fetch(mid, "(RFC822)")
                            if status != "OK":
                                continue
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)

                            subject = self._clean_header(msg.get("Subject", ""))
                            from_addr = self._clean_header(msg.get("From", ""))

                            # Extract body content
                            body_text = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        body_text += part.get_payload(decode=True).decode(
                                            "utf-8", errors="ignore"
                                        )
                            else:
                                body_text = msg.get_payload(decode=True).decode(
                                    "utf-8", errors="ignore"
                                )

                            full_content = f"{subject}\n{body_text}"

                            # Regex search for 6-digit or 4-digit code
                            # Priority 1: explicitly labeled as code, pin, verification, otp
                            match = re.search(
                                r"(?:code|pin|otp|verification)[\s\:\-\w]*?\b(\d{4,6})\b",
                                full_content,
                                re.IGNORECASE,
                            )
                            if match:
                                otp = match.group(1)
                                logger.info(
                                    f"Captured OTP '{otp}' from sender '{from_addr}' (Subject: {subject[:40]})"
                                )
                                mail.logout()
                                return otp

                            # Priority 2: standalone 6-digit code in subject
                            subject_match = re.search(r"\b(\d{6})\b", subject)
                            if subject_match:
                                otp = subject_match.group(1)
                                logger.info(
                                    f"Captured OTP '{otp}' from subject '{subject[:40]}'"
                                )
                                mail.logout()
                                return otp

                mail.logout()
            except Exception as e:
                logger.debug(f"IMAP poll error: {e}")

            time.sleep(poll_interval_seconds)

        logger.warning(f"OTP polling timed out after {max_wait_seconds}s.")
        return None
