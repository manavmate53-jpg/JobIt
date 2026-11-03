"""
JobIt v2.0 - Pillar CV Generator
Generates strict 1-page A4 HTML and PDF resumes tailored to the assigned pillar,
with dynamic proof-of-work project mapping.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import jinja2

from src.tailoring.proof_of_work_mapper import ProofOfWorkMapper

logger = logging.getLogger(__name__)


class PillarCVGenerator:
    """Generates 1-page A4 PDF resumes tailored to specific startups and strategic pillars."""

    def __init__(
        self,
        candidate_profile_path: Optional[Path] = None,
        templates_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        self.profile_path = candidate_profile_path or Path("config/candidate_profile.json")
        self.templates_dir = templates_dir or Path("templates")
        self.output_dir = output_dir or Path("exports/resumes")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.candidate_data = self._load_candidate_profile()
        self.pow_mapper = ProofOfWorkMapper()

        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=jinja2.select_autoescape(["html", "xml"])
        )

    def _load_candidate_profile(self) -> Dict[str, Any]:
        if self.profile_path.exists():
            with open(self.profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_template_name(self, pillar: str) -> str:
        pil = str(pillar).upper()
        if "FOUNDER" in pil or "PILLAR_1" in pil:
            return "resume_pillar1_founders_office.html"
        if "PRODUCT_OPERATIONS" in pil or "PILLAR_2" in pil or "OPS" in pil:
            return "resume_pillar2_prod_ops.html"
        return "resume_pillar3_ai_apm.html"

    def render_html(
        self,
        company_name: str,
        role_title: str,
        pillar: str,
        sector: str = ""
    ) -> str:
        template_name = self.get_template_name(pillar)
        template = self.jinja_env.get_template(template_name)

        # Select top 3 PM Lab builds matching the target company
        matched_projects = self.pow_mapper.select_top_3_builds(
            sector=sector,
            pillar=pillar,
            company_name=company_name
        )

        rendered = template.render(
            candidate=self.candidate_data.get("personal", {}),
            target_company=company_name,
            target_role=role_title,
            projects=[
                {
                    "name": p.name,
                    "category": p.category,
                    "url": p.url,
                    "summary": p.summary,
                    "key_metrics": p.key_metrics
                }
                for p in matched_projects
            ]
        )
        return rendered

    def generate_cv(
        self,
        company_name: str,
        role_title: str,
        pillar: str,
        sector: str = "",
        generate_pdf: bool = True
    ) -> Dict[str, Path]:
        """
        Renders HTML and compiles single-page A4 PDF.
        Returns paths to generated HTML and PDF files.
        """
        clean_company = re.sub(r"[^a-zA-Z0-9]", "_", company_name).strip("_")
        clean_pillar = pillar.split("_")[-1].lower() if "_" in pillar else pillar.lower()
        base_name = f"Manav_Mate_{clean_company}_{clean_pillar}"

        html_content = self.render_html(
            company_name=company_name,
            role_title=role_title,
            pillar=pillar,
            sector=sector
        )

        html_path = self.output_dir / f"{base_name}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        pdf_path = self.output_dir / f"{base_name}.pdf"

        if generate_pdf:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
                    page.pdf(
                        path=str(pdf_path),
                        format="A4",
                        print_background=True,
                        margin={"top": "6mm", "right": "8mm", "bottom": "5mm", "left": "8mm"}
                    )
                    browser.close()
                logger.info("Generated PDF: %s", pdf_path)
            except Exception as exc:
                logger.warning("Playwright PDF generation skipped: %s. HTML saved at %s", exc, html_path)

        return {"html": html_path, "pdf": pdf_path if pdf_path.exists() else html_path}
