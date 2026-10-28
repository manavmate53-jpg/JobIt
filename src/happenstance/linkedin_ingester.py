"""Comprehensive LinkedIn Data Export Ingester for Happenstance AI.

Parses:
- Connections.csv (direct connection list)
- Invitations.csv (incoming & outgoing connection requests with profile URLs)
- messages.csv (actual message threads, frequency, timestamps, directionality)
- Company Follows.csv (target followed organizations)
"""

from __future__ import annotations

import csv
import datetime
import io
import os
import re
import zipfile
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from src.happenstance.models import Direction, InteractionEdge, InteractionType, PersonNode
from src.happenstance.relationship_graph import RelationshipGraph


class LinkedInIngester:
    """Ingests LinkedIn connection exports into the relationship graph."""

    def __init__(self, graph: RelationshipGraph):
        self.graph = graph

    def ingest_zip(self, zip_path: str, extract_dir: Optional[str] = None) -> Dict[str, int]:
        """Extracts and ingests a full LinkedIn export zip file."""
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"LinkedIn ZIP file not found: {zip_path}")

        target_dir = extract_dir or os.path.join(os.path.dirname(zip_path), "extracted_linkedin")
        os.makedirs(target_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)

        return self.ingest_archive_dir(target_dir)

    def ingest_archive_dir(self, dir_path: str) -> Dict[str, int]:
        """Scans a directory for LinkedIn CSV files and ingests them all."""
        stats = {
            "connections": 0,
            "invitations": 0,
            "messages": 0,
            "company_follows": 0,
            "total_nodes_added": 0,
        }

        # 1. Ingest Connections.csv if available
        conn_path = os.path.join(dir_path, "Connections.csv")
        if os.path.exists(conn_path):
            stats["connections"] = self.ingest_csv_file(conn_path)

        # 2. Ingest Invitations.csv
        inv_path = os.path.join(dir_path, "Invitations.csv")
        if os.path.exists(inv_path):
            stats["invitations"] = self.ingest_invitations_file(inv_path)

        # 3. Ingest messages.csv
        msg_path = os.path.join(dir_path, "messages.csv")
        if os.path.exists(msg_path):
            stats["messages"] = self.ingest_messages_file(msg_path)

        # 4. Ingest Company Follows.csv
        cf_path = os.path.join(dir_path, "Company Follows.csv")
        if os.path.exists(cf_path):
            stats["company_follows"] = self.ingest_company_follows(cf_path)

        stats["total_nodes_added"] = len(self.graph.nodes)
        return stats

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

            node_id = email.lower() if email else f"li_{re.sub(r'[^a-z0-9]', '_', full_name.lower())}"

            connected_dt = datetime.datetime.now(datetime.timezone.utc)
            if connected_on_str:
                for fmt in ("%d %b %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        connected_dt = datetime.datetime.strptime(connected_on_str, fmt).replace(tzinfo=datetime.timezone.utc)
                        break
                    except ValueError:
                        pass

            domain = None
            if company:
                clean_comp = re.sub(r"[^a-z0-9]", "", company.lower())
                if clean_comp:
                    domain = f"{clean_comp}.com"

            tags = self._extract_tags(position)

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

    def ingest_invitations_file(self, file_path: str) -> int:
        """Parses Invitations.csv for contact nodes and connection dates."""
        count = 0
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                from_name = (row.get("From") or "").strip()
                to_name = (row.get("To") or "").strip()
                sent_at = (row.get("Sent At") or "").strip()
                direction_str = (row.get("Direction") or "").upper().strip()
                inviter_url = (row.get("inviterProfileUrl") or "").strip()
                invitee_url = (row.get("inviteeProfileUrl") or "").strip()
                message = (row.get("Message") or "").strip()

                is_outgoing = "OUTGOING" in direction_str or from_name == "Manav Mate"
                other_name = to_name if is_outgoing else from_name
                other_url = invitee_url if is_outgoing else inviter_url

                if not other_name or other_name == "Manav Mate":
                    continue

                node_id = self._id_from_name_or_url(other_name, other_url)

                dt = datetime.datetime.now(datetime.timezone.utc)
                if sent_at:
                    for fmt in ("%m/%d/%y, %I:%M %p", "%Y-%m-%d %H:%M:%S", "%b %d, %Y"):
                        try:
                            dt = datetime.datetime.strptime(sent_at, fmt).replace(tzinfo=datetime.timezone.utc)
                            break
                        except ValueError:
                            pass

                person = PersonNode(
                    id=node_id,
                    name=other_name,
                    linkedin_url=other_url or None,
                    tags=["LinkedIn Connection"],
                    metadata={"source": "Invitations", "sent_at": sent_at}
                )
                self.graph.add_person(person)

                edge = InteractionEdge(
                    source_id=self.graph.root_id if is_outgoing else node_id,
                    target_id=node_id if is_outgoing else self.graph.root_id,
                    interaction_type=InteractionType.LINKEDIN,
                    timestamp=dt,
                    direction=Direction.OUTBOUND if is_outgoing else Direction.INBOUND,
                    thread_count=1,
                    subject_summary=f"LinkedIn Invitation: {message[:60]}" if message else "LinkedIn Connection Invitation"
                )
                self.graph.add_interaction(edge)
                count += 1

        return count

    def ingest_messages_file(self, file_path: str) -> int:
        """Parses messages.csv, reconstructing conversation threads, counts, and directionality."""
        conversations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                conv_id = row.get("CONVERSATION ID", "").strip()
                if not conv_id:
                    continue
                conversations[conv_id].append(row)

        count = 0
        for conv_id, msgs in conversations.items():
            # Identify other participant
            other_name = None
            other_url = None
            user_sent_count = 0
            other_sent_count = 0
            latest_dt = datetime.datetime.now(datetime.timezone.utc)
            subjects = []

            for m in msgs:
                from_n = (m.get("FROM") or "").strip()
                to_n = (m.get("TO") or "").strip()
                sender_url = (m.get("SENDER PROFILE URL") or "").strip()
                recip_url = (m.get("RECIPIENT PROFILE URLS") or "").strip()
                date_str = (m.get("DATE") or "").strip()
                subj = (m.get("SUBJECT") or "").strip()

                if subj and subj not in subjects:
                    subjects.append(subj)

                if from_n == "Manav Mate":
                    user_sent_count += 1
                    if to_n and not other_name:
                        other_name = to_n
                        other_url = recip_url
                else:
                    other_sent_count += 1
                    if from_n and not other_name:
                        other_name = from_n
                        other_url = sender_url

                if date_str:
                    try:
                        clean_date = date_str.replace(" UTC", "")
                        dt = datetime.datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
                        if dt > latest_dt or latest_dt == datetime.datetime.now(datetime.timezone.utc):
                            latest_dt = dt
                    except Exception:
                        pass

            if not other_name:
                continue

            node_id = self._id_from_name_or_url(other_name, other_url)

            # Determine directionality
            if user_sent_count > 0 and other_sent_count > 0:
                direction = Direction.BIDIRECTIONAL
            elif user_sent_count > 0:
                direction = Direction.OUTBOUND
            else:
                direction = Direction.INBOUND

            total_msgs = user_sent_count + other_sent_count

            person = PersonNode(
                id=node_id,
                name=other_name,
                linkedin_url=other_url or None,
                tags=["Message Contact", "Active Network"],
                metadata={"source": "LinkedIn Messages", "total_messages": total_msgs}
            )
            self.graph.add_person(person)

            edge = InteractionEdge(
                source_id=self.graph.root_id if user_sent_count > other_sent_count else node_id,
                target_id=node_id if user_sent_count > other_sent_count else self.graph.root_id,
                interaction_type=InteractionType.LINKEDIN,
                timestamp=latest_dt,
                direction=direction,
                thread_count=total_msgs,
                subject_summary=f"LinkedIn Thread ({total_msgs} msgs): {', '.join(subjects[:2]) if subjects else 'Chat'}"
            )
            self.graph.add_interaction(edge)
            count += 1

        return count

    def ingest_company_follows(self, file_path: str) -> int:
        """Parses followed companies to enrich graph metadata."""
        count = 0
        followed_orgs = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = (row.get("Organization") or "").strip()
                if org:
                    followed_orgs.append(org)
                    count += 1
        if self.graph.root_id in self.graph.nodes:
            self.graph.nodes[self.graph.root_id].metadata["followed_companies"] = followed_orgs
        return count

    def _id_from_name_or_url(self, name: str, url: Optional[str] = None) -> str:
        """Generates deterministic clean identifier."""
        if url and "/in/" in url:
            slug = url.split("/in/")[1].strip("/").lower()
            if slug:
                return f"li_{slug}"
        clean_name = re.sub(r"[^a-z0-9]", "_", name.lower().strip())
        return f"li_{clean_name}"

    def _extract_tags(self, position: Optional[str]) -> List[str]:
        tags = []
        if not position:
            return tags
        p_lower = position.lower()
        if "product" in p_lower:
            tags.append("Product")
        if "founder" in p_lower or "ceo" in p_lower:
            tags.append("Founder")
        if "investor" in p_lower or "partner" in p_lower or "vc" in p_lower:
            tags.append("VC")
        if "engineer" in p_lower or "tech" in p_lower:
            tags.append("Engineering")
        if "operations" in p_lower or "ops" in p_lower:
            tags.append("Operations")
        return tags
