"""Calendar meeting metadata ingester for Happenstance AI."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from src.happenstance.models import Direction, InteractionEdge, InteractionType, PersonNode
from src.happenstance.relationship_graph import RelationshipGraph


class CalendarIngester:
    """Ingests meeting events to record high-signal face-to-face interaction touchpoints."""

    def __init__(self, graph: RelationshipGraph, user_email: str):
        self.graph = graph
        self.user_email = user_email.lower().strip()

    def ingest_event_records(self, events: List[Dict[str, Any]]) -> int:
        """Ingests meeting dictionaries with 'summary', 'start_time', 'attendees'."""
        count = 0
        for ev in events:
            summary = ev.get("summary", "Meeting")
            start = ev.get("start_time")
            attendees = ev.get("attendees", [])

            # Parse start time
            dt = datetime.datetime.now(datetime.timezone.utc)
            if isinstance(start, datetime.datetime):
                dt = start if start.tzinfo else start.replace(tzinfo=datetime.timezone.utc)
            elif isinstance(start, str):
                try:
                    dt = datetime.datetime.fromisoformat(start)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                except Exception:
                    pass

            for att in attendees:
                att_email = att.get("email", "").lower().strip() if isinstance(att, dict) else str(att).lower().strip()
                att_name = att.get("name", "") if isinstance(att, dict) else ""

                if not att_email or att_email == self.user_email:
                    continue

                # Add person node
                person = PersonNode(
                    id=att_email,
                    name=att_name or att_email.split("@")[0].title(),
                    primary_email=att_email,
                    metadata={"source": "Calendar"}
                )
                self.graph.add_person(person)

                # Record calendar interaction (always bidirectional, high-strength)
                edge = InteractionEdge(
                    source_id=self.graph.root_id,
                    target_id=att_email,
                    interaction_type=InteractionType.CALENDAR,
                    timestamp=dt,
                    direction=Direction.BIDIRECTIONAL,
                    thread_count=1,
                    subject_summary=f"Calendar Meeting: {summary}"
                )
                self.graph.add_interaction(edge)
                count += 1

        return count
