"""Unified Manager connecting Happenstance AI Relationship Intelligence with JobIt."""

from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.happenstance.models import (
    Direction,
    InteractionEdge,
    InteractionType,
    PersonNode,
    RelationshipStrength,
    WarmIntroPath,
)
from src.happenstance.relationship_graph import RelationshipGraph
from src.happenstance.strength_engine import RelationshipScorer
from src.happenstance.intent_parser import IntentParser, StructuredQuery
from src.happenstance.path_finder import PathFinder
from src.happenstance.intro_generator import WarmIntroGenerator
from src.happenstance.linkedin_ingester import LinkedInIngester
from src.happenstance.email_header_ingester import EmailHeaderIngester
from src.scrapers.base_scraper import ScrapedJob

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "network_graph.json"
)


class HappenstanceManager:
    """Coordinates relationship intelligence, graph persistence, and warm job referral matching."""

    def __init__(self, graph_path: str = DEFAULT_GRAPH_PATH):
        self.graph_path = graph_path
        self.graph = self._load_or_initialize_graph()
        self.scorer = RelationshipScorer(half_life_days=90.0)
        self.parser = IntentParser()
        self.finder = PathFinder(self.graph, self.scorer)
        self.generator = WarmIntroGenerator(candidate_name="Manav Mate", candidate_email="manavmate53@gmail.com")

    def _load_or_initialize_graph(self) -> RelationshipGraph:
        """Loads persistent graph or initializes with candidate profile & demo network."""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, "r", encoding="utf-8") as f:
                    return RelationshipGraph.from_json(f.read())
            except Exception as e:
                logger.warning(f"Error loading graph from {self.graph_path}: {e}. Creating new graph.")

        graph = RelationshipGraph(root_id="me")
        graph.nodes["me"].name = "Manav Mate"
        graph.nodes["me"].primary_email = "manavmate53@gmail.com"
        graph.nodes["me"].headline = "Product Manager | 0-to-1 Builder (CIPM Certified)"
        graph.nodes["me"].tags = ["Product Manager", "Founder", "Candidate"]

        # Seed with high-intent demo network bridges to kickstart relationship intelligence
        self._seed_default_network(graph)
        self._save_graph(graph)
        return graph

    def _save_graph(self, graph: Optional[RelationshipGraph] = None) -> None:
        """Persists graph to JSON store."""
        g = graph or self.graph
        os.makedirs(os.path.dirname(os.path.abspath(self.graph_path)), exist_ok=True)
        with open(self.graph_path, "w", encoding="utf-8") as f:
            f.write(g.to_json())

    def _seed_default_network(self, graph: RelationshipGraph) -> None:
        """Seeds default high-trust bridges and startup connections for testing warm referrals."""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Bridge 1: Rohan Deshmukh (Staff ML Engineer at AI Labs - Strong Connection)
        rohan = PersonNode(
            id="rohan.deshmukh@gmail.com",
            name="Rohan Deshmukh",
            primary_email="rohan.deshmukh@gmail.com",
            headline="Staff Machine Learning Engineer at AI Labs",
            company="AI Labs",
            location="San Francisco / Mumbai",
            tags=["Friend", "Engineer", "AI", "Infrastructure"]
        )
        graph.add_person(rohan)
        graph.add_interaction(InteractionEdge(
            source_id="me", target_id=rohan.id,
            interaction_type=InteractionType.CALENDAR,
            timestamp=now - datetime.timedelta(days=7),
            direction=Direction.BIDIRECTIONAL,
            thread_count=3,
            subject_summary="AI Inference Architecture Catch-up"
        ))
        graph.add_interaction(InteractionEdge(
            source_id="me", target_id=rohan.id,
            interaction_type=InteractionType.EMAIL,
            timestamp=now - datetime.timedelta(days=2),
            direction=Direction.BIDIRECTIONAL,
            thread_count=5,
            subject_summary="Re: Llama 3.1 fine-tuning benchmarks"
        ))

        # Bridge 2: Sneha Kapoor (Principal at Nexus Venture Partners - Moderate Connection)
        sneha = PersonNode(
            id="sneha.kapoor@venture.com",
            name="Sneha Kapoor",
            primary_email="sneha.kapoor@venture.com",
            headline="Principal at Nexus Venture Partners",
            company="Nexus Venture Partners",
            location="Mumbai",
            tags=["VC", "Investor", "Fintech", "SaaS"]
        )
        graph.add_person(sneha)
        graph.add_interaction(InteractionEdge(
            source_id="me", target_id=sneha.id,
            interaction_type=InteractionType.EMAIL,
            timestamp=now - datetime.timedelta(days=45),
            direction=Direction.BIDIRECTIONAL,
            thread_count=2,
            subject_summary="B2B SaaS Market Trends"
        ))

        # Bridge 3: Amit Verma (Ex-Colleague from NeoManpower Operations - Strong Connection)
        amit = PersonNode(
            id="amit.verma@neomanpower.in",
            name="Amit Verma",
            primary_email="amit.verma@neomanpower.in",
            headline="Head of Business Operations",
            company="NeoManpower",
            location="Mumbai",
            tags=["Operations", "Colleague", "B2B"]
        )
        graph.add_person(amit)
        graph.add_interaction(InteractionEdge(
            source_id="me", target_id=amit.id,
            interaction_type=InteractionType.EMAIL,
            timestamp=now - datetime.timedelta(days=5),
            direction=Direction.BIDIRECTIONAL,
            thread_count=6,
            subject_summary="Quarterly Operations & SLA Audit"
        ))

        # Target 1: Aravind Srinivas (Founder & CEO, Perplexity AI) -> Connected to Rohan
        aravind = PersonNode(
            id="aravind@perplexity.ai",
            name="Aravind Srinivas",
            primary_email="aravind@perplexity.ai",
            headline="Founder & CEO",
            company="Perplexity AI",
            domain="perplexity.ai",
            location="San Francisco / Remote",
            tags=["Founder", "CEO", "AI", "Search"]
        )
        graph.add_person(aravind)
        graph.add_interaction(InteractionEdge(
            source_id=rohan.id, target_id=aravind.id,
            interaction_type=InteractionType.EMAIL,
            timestamp=now - datetime.timedelta(days=12),
            direction=Direction.BIDIRECTIONAL,
            thread_count=4,
            subject_summary="Search evaluation benchmarks"
        ))

        # Target 2: Suumit Shah (Founder & CEO, Dukaan) -> Connected to Sneha
        suumit = PersonNode(
            id="suumit@mydukaan.io",
            name="Suumit Shah",
            primary_email="suumit@mydukaan.io",
            headline="Founder & CEO",
            company="Dukaan",
            domain="mydukaan.io",
            location="Mumbai / Remote",
            tags=["Founder", "CEO", "Ecommerce", "AI"]
        )
        graph.add_person(suumit)
        graph.add_interaction(InteractionEdge(
            source_id=sneha.id, target_id=suumit.id,
            interaction_type=InteractionType.CALENDAR,
            timestamp=now - datetime.timedelta(days=30),
            direction=Direction.BIDIRECTIONAL,
            thread_count=2,
            subject_summary="Dukaan Merchant Growth Review"
        ))

        # Target 3: Aadit Palicha (Founder & CEO, Zepto) -> Connected to Amit Verma
        aadit = PersonNode(
            id="aadit@zepto.co",
            name="Aadit Palicha",
            primary_email="aadit@zepto.co",
            headline="Founder & CEO",
            company="Zepto",
            domain="zepto.co",
            location="Mumbai",
            tags=["Founder", "CEO", "Quick Commerce", "Logistics"]
        )
        graph.add_person(aadit)
        graph.add_interaction(InteractionEdge(
            source_id=amit.id, target_id=aadit.id,
            interaction_type=InteractionType.EMAIL,
            timestamp=now - datetime.timedelta(days=20),
            direction=Direction.BIDIRECTIONAL,
            thread_count=3,
            subject_summary="Dark store staffing and logistics dispatch"
        ))

        # Target 4: Lalit Keshre (Founder & CEO, Groww) -> Connected to Sneha
        lalit = PersonNode(
            id="lalit@groww.in",
            name="Lalit Keshre",
            primary_email="lalit@groww.in",
            headline="Founder & CEO",
            company="Groww",
            domain="groww.in",
            location="Mumbai / Remote",
            tags=["Founder", "CEO", "Fintech", "Investments"]
        )
        graph.add_person(lalit)
        graph.add_interaction(InteractionEdge(
            source_id=sneha.id, target_id=lalit.id,
            interaction_type=InteractionType.EMAIL,
            timestamp=now - datetime.timedelta(days=25),
            direction=Direction.BIDIRECTIONAL,
            thread_count=2,
            subject_summary="Fintech market discussion"
        ))

    def find_warm_paths_for_job(self, job: ScrapedJob) -> List[WarmIntroPath]:
        """Scans the relationship graph for warm introduction paths matching the job opening."""
        # Clean company name
        company_clean = job.company.strip()
        role_keywords = [w for w in job.role.split() if len(w) > 3]

        return self.finder.find_paths_to_company(
            company_name=company_clean,
            target_role_keywords=role_keywords
        )

    def generate_referral_package(self, path: WarmIntroPath, job: ScrapedJob) -> Dict[str, Any]:
        """Generates complete warm referral package for a job."""
        return self.generator.generate_referral_package(path, target_role=job.role)

    def query(self, prompt: str) -> List[WarmIntroPath]:
        """Executes a plain English relationship search query."""
        parsed = self.parser.parse(prompt)
        return self.finder.search(parsed)

    def import_linkedin_csv(self, file_path: str) -> int:
        """Imports LinkedIn Connections.csv into the graph."""
        ingester = LinkedInIngester(self.graph)
        count = ingester.ingest_csv_file(file_path)
        self._save_graph()
        return count

    def sync_gmail_headers(self, limit: int = 50) -> int:
        """Safely syncs email headers from user's Gmail using environment credentials."""
        user = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
        raw_pw = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
        password = raw_pw.replace(" ", "") if raw_pw else None

        if not user or not password:
            logger.warning("Gmail sync skipped: Missing credentials in environment.")
            return 0

        ingester = EmailHeaderIngester(self.graph, user_email=user)
        count = ingester.sync_imap_headers(
            host="imap.gmail.com",
            port=993,
            username=user,
            password=password,
            folder="INBOX",
            limit=limit
        )
        if count > 0:
            self._save_graph()
        return count
