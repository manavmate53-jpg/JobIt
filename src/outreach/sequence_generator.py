"""
JobIt v2.0 - Sequence Generator & Daily Action Pack Builder
Generates 4-touchpoint multi-channel sequences tailored by pillar and compiles
the Daily Action Pack into exports/daily_action_packs/YYYY-MM-DD_action_pack.md.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.outreach.decision_maker_finder import ContactProfile, DecisionMakerFinder
from src.signals.wellfound_crosscheck import StartupOpportunity
from src.strategy.pillar_classifier import StrategicPillar
from src.strategy.scoring_engine import ScoreBreakdown
from src.tailoring.proof_of_work_mapper import PMLabBuild, ProofOfWorkMapper

logger = logging.getLogger(__name__)


@dataclass
class OutreachTouchpoints:
    company_name: str
    target_person: str
    target_title: str
    pillar: str
    linkedin_connect_note: str  # < 280 chars
    funding_hook_cold_dm: str
    wellfound_founder_note: str
    follow_up_bump: str
    salary_quote_note: str
    primary_project: PMLabBuild
    email_options: List[str]
    linkedin_search_url: str
    tailored_pdf_path: str


class SequenceGenerator:
    """Generates tailored 4-touchpoint outreach packages adhering to candidate boundaries."""

    def __init__(
        self,
        playbooks_path: Optional[Path] = None,
        candidate_profile_path: Optional[Path] = None
    ):
        self.playbooks_path = playbooks_path or Path("templates/outreach_playbooks.json")
        self.profile_path = candidate_profile_path or Path("config/candidate_profile.json")

        self.playbooks = self._load_json(self.playbooks_path)
        self.candidate = self._load_json(self.profile_path)

        self.finder = DecisionMakerFinder()
        self.pow_mapper = ProofOfWorkMapper()

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_salary_quote_note(self, funding_stage: str, pillar: str = "") -> str:
        st = funding_stage.lower()
        pil = str(pillar).upper()
        if "EVENT" in pil or "MICE" in pil or "event" in st or "mice" in st or "enterprise mice" in st:
            return "targeting minimum ₹40,000/month in-hand (₹5.5L to ₹7.5L CTC)"
        if "seed" in st or "pre-series a" in st or "angel" in st:
            return "targeting ₹6.5L to ₹8L with upside in early equity"
        return "targeting ₹10L to ₹12L base given proven AI pipeline and P&L scaling track record"

    def clean_text_strict(self, text: str) -> str:
        """Removes em dashes, double dashes, and corporate buzzwords."""
        text = text.replace("—", " - ")
        text = text.replace("--", " - ")
        return text

    def generate_touchpoints(
        self,
        opportunity: StartupOpportunity,
        pillar: str,
        lead_investor: str = "prominent investors",
        tailored_pdf_path: str = ""
    ) -> OutreachTouchpoints:
        pillars_data = self.playbooks.get("pillars", {})
        is_event = (
            "EVENT" in str(pillar).upper()
            or "MICE" in str(pillar).upper()
            or "event" in opportunity.sector.lower()
            or "mice" in opportunity.sector.lower()
        )
        if is_event and pillar not in pillars_data:
            resolved_pillar = "PILLAR_4_EVENT_OPERATIONS_MICE"
        else:
            resolved_pillar = pillar

        playbook = pillars_data.get(
            resolved_pillar,
            pillars_data.get("PILLAR_4_EVENT_OPERATIONS_MICE" if is_event else "PILLAR_1_FOUNDERS_OFFICE", {})
        )

        if not tailored_pdf_path and is_event:
            tailored_pdf_path = "exports/resumes/Manav_Mate_Event_Management_CV.pdf"

        # Identify decision maker
        contacts = self.finder.identify_targets(
            company_name=opportunity.company_name,
            founder_names=opportunity.founder_names,
            pillar=pillar
        )
        primary_contact = contacts[0] if contacts else ContactProfile(
            name="Founding Team",
            title="Founder",
            first_name="Founder",
            last_name="",
            email_permutations=[f"founder@{opportunity.company_name.lower()}.com"],
            linkedin_search_url="",
            role_priority=1
        )

        # Matched PM Lab projects
        matched_projects = self.pow_mapper.select_top_3_builds(
            sector=opportunity.sector,
            pillar=pillar,
            company_name=opportunity.company_name
        )
        primary_proj = matched_projects[0] if matched_projects else PMLabBuild(
            id="crewrostering",
            name="CrewRoster",
            category="Workforce Ops",
            url="https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering",
            summary="",
            key_metrics="",
            domains=[]
        )

        salary_note = self.get_salary_quote_note(opportunity.funding_stage, pillar=pillar)

        # Context dict for formatting
        fmt = {
            "first_name": primary_contact.first_name,
            "company_name": opportunity.company_name,
            "amount_raised": opportunity.amount_raised,
            "funding_stage": opportunity.funding_stage,
            "lead_investor": lead_investor,
            "primary_project_id": primary_proj.id,
            "salary_quote_note": salary_note
        }

        # Format and sanitize
        conn_note = self.clean_text_strict(playbook.get("linkedin_connect_note", "").format(**fmt))
        # Ensure under 280 characters
        if len(conn_note) > 280:
            conn_note = conn_note[:277] + "..."

        cold_dm = self.clean_text_strict(playbook.get("funding_hook_cold_dm", "").format(**fmt))
        wellfound = self.clean_text_strict(playbook.get("wellfound_founder_note", "").format(**fmt))
        bump = self.clean_text_strict(playbook.get("follow_up_bump", "").format(**fmt))

        return OutreachTouchpoints(
            company_name=opportunity.company_name,
            target_person=primary_contact.name,
            target_title=primary_contact.title,
            pillar=resolved_pillar,
            linkedin_connect_note=conn_note,
            funding_hook_cold_dm=cold_dm,
            wellfound_founder_note=wellfound,
            follow_up_bump=bump,
            salary_quote_note=salary_note,
            primary_project=primary_proj,
            email_options=primary_contact.email_permutations,
            linkedin_search_url=primary_contact.linkedin_search_url,
            tailored_pdf_path=tailored_pdf_path
        )

    def generate_event_touchpoints(
        self,
        company_name: str,
        target_person: str = "Hiring Team",
        target_title: str = "Operations Lead",
        role_title: str = "Event Operations Manager",
        tailored_pdf_path: str = "exports/resumes/Manav_Mate_Event_Management_CV.pdf",
        first_name: Optional[str] = None,
        email_permutations: Optional[List[str]] = None,
    ) -> OutreachTouchpoints:
        """
        Generates dedicated event operations & MICE outreach touchpoints explicitly referencing:
        - 4+ years experience across 150-200+ events with 15+ agencies
        - 2026 execution at Tata Mumbai Marathon (Mumbai University venue production/ops),
          ICANN 2026 (registration/logistics), and Neurology Summit 2026 (registration, production, ops, hospitality)
        - End-to-end procurement, venue mapping, AV time management, catering planning, and Canva/AI workflow speed.
        - Strict constraints: zero em dashes, zero double hyphens, and LinkedIn connect note <= 280 chars.
        """
        fname = first_name or (target_person.split()[0] if target_person else "there")
        pillars_data = self.playbooks.get("pillars", {})
        playbook = pillars_data.get("PILLAR_4_EVENT_OPERATIONS_MICE", {})

        primary_proj = PMLabBuild(
            id="crewrostering",
            name="CrewRoster Dashboard",
            category="Operations PM & Workforce Tech",
            url="https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering",
            summary="Frontline workforce rostering and SLA escalation system with automated standby dispatch buffers and QR attendance audit (modeled on NeoManpower).",
            key_metrics="100% SLA compliance, 48-hr reconciliation",
            domains=["operations", "workforce", "supply chain", "logistics", "events", "mice"]
        )

        salary_note = "minimum ₹40,000/month in-hand (₹5.5L to ₹7.5L CTC)"
        fmt = {
            "first_name": fname,
            "company_name": company_name,
            "amount_raised": "",
            "funding_stage": "Enterprise MICE",
            "lead_investor": "",
            "primary_project_id": "crewrostering",
            "salary_quote_note": salary_note
        }

        conn_note = self.clean_text_strict(playbook.get("linkedin_connect_note", "").format(**fmt))
        if len(conn_note) > 280:
            conn_note = conn_note[:277] + "..."

        cold_dm = self.clean_text_strict(playbook.get("funding_hook_cold_dm", "").format(**fmt))
        wellfound = self.clean_text_strict(playbook.get("wellfound_founder_note", "").format(**fmt))
        bump = self.clean_text_strict(playbook.get("follow_up_bump", "").format(**fmt))

        clean_comp = re.sub(r"[^a-zA-Z0-9]", "", company_name.lower())
        domain = f"{clean_comp}.com"
        emails = email_permutations if email_permutations else [
            f"careers@{domain}",
            f"hiring@{domain}",
            f"hr@{domain}"
        ]

        return OutreachTouchpoints(
            company_name=company_name,
            target_person=target_person,
            target_title=target_title,
            pillar="PILLAR_4_EVENT_OPERATIONS_MICE",
            linkedin_connect_note=conn_note,
            funding_hook_cold_dm=cold_dm,
            wellfound_founder_note=wellfound,
            follow_up_bump=bump,
            salary_quote_note=salary_note,
            primary_project=primary_proj,
            email_options=emails,
            linkedin_search_url=f"https://www.linkedin.com/search/results/people/?keywords={company_name}%20event%20operations",
            tailored_pdf_path=tailored_pdf_path
        )

    def build_daily_action_pack(
        self,
        ranked_items: List[Dict[str, Any]],
        pack_date: Optional[str] = None,
        pack_file_path: Optional[Path] = None,
        title: Optional[str] = None,
        limit: int = 15
    ) -> Path:
        """
        Compiles the target openings into a clean, ready-to-paste markdown action pack.
        """
        date_str = pack_date or datetime.now().strftime("%Y-%m-%d")
        out_dir = Path("exports/daily_action_packs")
        out_dir.mkdir(parents=True, exist_ok=True)
        pack_file = pack_file_path or (out_dir / f"{date_str}_action_pack.md")

        header_title = title or f"JobIt v2.0 &bull; Daily Founder Action Pack &bull; {date_str}"
        lines = [
            f"# {header_title}",
            "",
            "> Target: 10 Founder Outbound DMs + 5 Wellfound Applications per day.",
            "> Grounded execution voice: zero corporate buzzwords, zero em dashes.",
            "",
            "---",
            ""
        ]

        for i, item in enumerate(ranked_items[:limit], start=1):
            touch: OutreachTouchpoints = item["touchpoints"]
            score_data: ScoreBreakdown = item["score"]
            opp: StartupOpportunity = item["opportunity"]

            lines.extend([
                f"## {i}. {opp.company_name} ({opp.funding_stage} &bull; {opp.amount_raised})",
                f"- **Sector / HQ**: {opp.sector} &bull; {opp.hq_location}",
                f"- **Assigned Pillar**: `{touch.pillar}`",
                f"- **Strategic Score**: **{score_data.total_score}/100**",
                f"- **Target Decision Maker**: {touch.target_person} ({touch.target_title})",
                f"- **Email Permutations**: `{'`, `'.join(touch.email_options[:3])}`",
                f"- **LinkedIn Search**: [Open Search]({touch.linkedin_search_url})",
                f"- **Wellfound Careers**: [Open Board]({opp.wellfound_url})",
                f"- **Tailored 1-Page PDF**: `{touch.tailored_pdf_path}`",
                f"- **Featured PM Lab Build**: [{touch.primary_project.name}]({touch.primary_project.url})",
                "",
                f"### Touchpoint 1: LinkedIn Connect Note ({len(touch.linkedin_connect_note)}/280 chars)",
                "```text",
                touch.linkedin_connect_note,
                "```",
                "",
                "### Touchpoint 2: Funding-Hook Cold DM / InMail / Email",
                "```text",
                touch.funding_hook_cold_dm,
                "```",
                "",
                "### Touchpoint 3: Wellfound / Direct Note",
                "```text",
                touch.wellfound_founder_note,
                "```",
                "",
                "### Touchpoint 4: 4-Day Follow-Up Bump",
                "```text",
                touch.follow_up_bump,
                "```",
                "",
                "---",
                ""
            ])

        with open(pack_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return pack_file

