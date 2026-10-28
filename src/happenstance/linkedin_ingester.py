"""LinkedIn connections CSV ingester for Happenstance AI."""

from __future__ import annotations

import csv
import datetime
import io
import os
import re
from typing import List, Optional

from src.happenstance.models import Direction, InteractionEdge, InteractionType, PersonNode
from src.happenstance.relationship_graph import RelationshipGraph


class LinkedInIngester:
    """Ingests LinkedIn connection exports into the relationship graph."""

    def __init__(self, graph: RelationshipGraph):
        self.graph = graph

    def ingest_csv_file(self, file_path: str) -> int:
        """Parses a standard LinkedIn Connections.csv file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LinkedIn CSV file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return self.ingest_csv_content(content)

    def ingest_csv_content(self, csv_content: str) -> int:
        """Parses CSV string content and populates the graph."""
        lines = csv_content.splitlines()
        # LinkedIn export CSVs often have introductory notes or empty lines at the top
        start_idx = 0
        for i, line in enumerate(lines):
            if "First Name" in line and "Last Name" in line:
                start_idx = i
                break

        reader = csv.DictReader(lines[start_idx:])
        count = 0

        for row in reader:
            first = row.get("First Name", "").strip()
            last = row.get("Last Name", "").strip()
            if not first and not last:
                continue

            full_name = f"{first} {last}".strip()
            email = row.get("Email Address", "").strip() or None
            company = row.get("Company", "").strip() or None
            position = row.get("Position", "").strip() or None
            connected_on_str = row.get("Connected On", "").strip()

            # Normalize ID
            if email:
                node_id = email.lower()
            else:
                slug = re.sub(r"[^a-z0-9]", "_", full_name.lower())
                node_id = f"li_{slug}"

            # Parse connected date
            connected_dt = datetime.datetime.now(datetime.timezone.utc)
            if connected_on_str:
                for fmt in ("%d %b %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        connected_dt = datetime.datetime.strptime(connected_on_str, fmt).replace(tzinfo=datetime.timezone.utc)
                        break
                    except ValueError:
                        pass

            # Infer domain
            domain = None
            if company:
                clean_comp = re.sub(r"[^a-z0-9]", "", company.lower())
                if clean_comp:
                    domain = f"{clean_comp}.com"

            tags = []
            if position:
                p_lower = position.lower()
                if "product" in p_lower:
                    tags.append("Product")
                if "founder" in p_lower or "ceo" in p_lower:
                    tags.append("Founder")
                if "investor" in p_lower or "partner" in p_lower or "vc" in p_lower:
                    tags.append("VC")
                if "engineer" in p_lower or "tech" in p_lower:
                    tags.append("Engineering")

            person = PersonNode(
                id=node_id,
                name=full_name,
                primary_email=email,
                headline=position,
                company=company,
                domain=domain,
                tags=tags,
                metadata={"source": "LinkedIn", "connected_on": connected_on_str}
            )
            self.graph.add_person(person)

            # Record initial LinkedIn connection edge
            edge = InteractionEdge(
                source_id=self.graph.root_id,
                target_id=node_id,
                interaction_type=InteractionType.LINKEDIN,
                timestamp=connected_dt,
                direction=Direction.BIDIRECTIONAL,
                thread_count=1,
                subject_summary=f"Connected on LinkedIn ({connected_on_str})"
            )
            self.graph.add_interaction(edge)
            count += 1

        return count
