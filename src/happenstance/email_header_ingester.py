"""Privacy-preserving Email Header Ingester for Happenstance AI.

Only reads message headers (From, To, Date, Message-ID, Subject) to calculate
interaction frequency, recency, and directionality. NEVER accesses email bodies.
"""

from __future__ import annotations

import datetime
import email.utils
import imaplib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.happenstance.models import Direction, InteractionEdge, InteractionType, PersonNode
from src.happenstance.relationship_graph import RelationshipGraph

logger = logging.getLogger(__name__)


def extract_email_and_name(raw_header: str) -> Tuple[str, str]:
    """Extracts clean email and display name from a raw header like 'John Doe <john@example.com>'."""
    if not raw_header:
        return "", ""
    name, addr = email.utils.parseaddr(raw_header)
    addr = addr.lower().strip()
    if not name and addr:
        name = addr.split("@")[0].replace(".", " ").title()
    return addr, name.strip()


class EmailHeaderIngester:
    """Ingests email communication metadata without storing email bodies."""

    def __init__(self, graph: RelationshipGraph, user_email: str):
        self.graph = graph
        self.user_email = user_email.lower().strip()

    def ingest_header_records(self, records: List[Dict[str, Any]]) -> int:
        """Ingests a list of pre-extracted email header dictionaries."""
        count = 0
        for rec in records:
            from_raw = rec.get("from", "")
            to_raw = rec.get("to", "")
            date_raw = rec.get("date")
            subject = rec.get("subject", "")

            from_email, from_name = extract_email_and_name(from_raw)
            to_email, to_name = extract_email_and_name(to_raw)

            if not from_email or not to_email:
                continue

            # Determine direction relative to user
            is_from_me = (from_email == self.user_email)
            is_to_me = (to_email == self.user_email)

            if is_from_me and not is_to_me:
                direction = Direction.OUTBOUND
                other_email = to_email
                other_name = to_name
            elif is_to_me and not is_from_me:
                direction = Direction.INBOUND
                other_email = from_email
                other_name = from_name
            else:
                # Self-email or unrelated
                continue

            # Parse date
            dt = datetime.datetime.now(datetime.timezone.utc)
            if isinstance(date_raw, datetime.datetime):
                dt = date_raw if date_raw.tzinfo else date_raw.replace(tzinfo=datetime.timezone.utc)
            elif isinstance(date_raw, str):
                try:
                    parsed_tuple = email.utils.parsedate_tz(date_raw)
                    if parsed_tuple:
                        timestamp = email.utils.mktime_tz(parsed_tuple)
                        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                except Exception:
                    pass

            # Create or update contact node
            domain = other_email.split("@")[1] if "@" in other_email else None
            person = PersonNode(
                id=other_email,
                name=other_name or other_email.split("@")[0].title(),
                primary_email=other_email,
                domain=domain,
                metadata={"source": "EmailHeaders"}
            )
            self.graph.add_person(person)

            # Record interaction edge
            edge = InteractionEdge(
                source_id=self.graph.root_id if is_from_me else other_email,
                target_id=other_email if is_from_me else self.graph.root_id,
                interaction_type=InteractionType.EMAIL,
                timestamp=dt,
                direction=direction,
                thread_count=1,
                subject_summary=subject[:80] if subject else "Email interaction"
            )
            self.graph.add_interaction(edge)
            count += 1

        return count

    def sync_imap_headers(
        self,
        host: str = "imap.gmail.com",
        port: int = 993,
        username: Optional[str] = None,
        password: Optional[str] = None,
        folder: str = "INBOX",
        limit: int = 100
    ) -> int:
        """Connects safely via IMAP to read metadata headers without downloading bodies."""
        user = username or self.user_email
        if not user or not password:
            logger.warning("IMAP sync skipped: Missing credentials.")
            return 0

        clean_pw = password.replace(" ", "")
        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(user, clean_pw)
            mail.select(folder, readonly=True)

            status, messages = mail.search(None, "ALL")
            if status != "OK" or not messages[0]:
                mail.logout()
                return 0

            msg_ids = messages[0].split()
            # Take most recent messages
            recent_ids = msg_ids[-limit:]

            records = []
            for m_id in recent_ids:
                # Fetch BODY.PEEK[HEADER.FIELDS (FROM TO DATE SUBJECT MESSAGE-ID)]
                # strictly ensures zero body content is touched or downloaded
                res, data = mail.fetch(m_id, "(BODY.PEEK[HEADER.FIELDS (FROM TO DATE SUBJECT MESSAGE-ID)])")
                if res == "OK" and data and len(data) > 0 and isinstance(data[0], tuple):
                    raw_header = data[0][1].decode("utf-8", errors="replace")
                    msg = email.message_from_string(raw_header)
                    records.append({
                        "from": msg.get("From", ""),
                        "to": msg.get("To", ""),
                        "date": msg.get("Date", ""),
                        "subject": msg.get("Subject", "")
                    })

            mail.close()
            mail.logout()

            return self.ingest_header_records(records)
        except Exception as e:
            logger.error(f"Error syncing IMAP headers: {e}")
            return 0
