"""ATS Resume & Cover Letter Tailoring Engine.

Generates single-page ATS-compliant HTML, Markdown, and PDF resumes,
plus human builder cover letters under 130 words without corporate jargon or em dashes.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from src.profile_engine import ProfileEngine, sanitize_builder_text
from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import EvaluationResult

logger = logging.getLogger(__name__)


def clean_filename(name: str) -> str:
    """Sanitizes company or role name for file naming."""
    clean = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[-\s]+", "_", clean)


class TailorEngine:
    """Generates tailored ATS resumes and builder cover letters."""

    def __init__(self, base_dir: Optional[Path] = None, profile_engine: Optional[ProfileEngine] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.profile_engine = profile_engine or ProfileEngine()
        self.templates_dir = self.base_dir / "templates"
        self.exports_resumes_dir = self.base_dir / "exports" / "resumes"
        self.exports_letters_dir = self.base_dir / "exports" / "cover_letters"

        self.exports_resumes_dir.mkdir(parents=True, exist_ok=True)
        self.exports_letters_dir.mkdir(parents=True, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False
        )

    def tailor(self, job: ScrapedJob, eval_result: Optional[EvaluationResult] = None) -> Dict[str, str]:
        """Runs end-to-end tailoring for a job posting. Generates HTML, PDF, MD, and Cover Letter."""
        safe_company = clean_filename(job.company)
        
        # 1. Generate Resume files
        resume_paths = self.generate_resume(job, eval_result, safe_company)
        
        # 2. Generate Cover Letter
        letter_paths = self.generate_cover_letter(job, eval_result, safe_company)
        
        combined = {**resume_paths, **letter_paths}
        return combined

    def generate_resume(self, job: ScrapedJob, eval_result: Optional[EvaluationResult], safe_company: str) -> Dict[str, str]:
        """Generates tailored HTML, Markdown, and PDF resumes."""
        job_text = f"{job.role} {job.raw_description}".lower()
        matching_skills = eval_result.matching_skills if eval_result else ["Technical PRDs", "SQL", "AI Systems"]

        # Craft grounded, keyword-tailored summary
        keywords_str = ", ".join(matching_skills[:4])
        tailored_summary = (
            f"Early-career tech Product Manager and former founder with hands-on background in "
            f"0-to-1 product discovery, technical PRDs, and delivery. At HireFlo India, drove a 40% reduction in "
            f"Llama 3.1 inference compute costs via NVIDIA NIM and improved user onboarding completion by 30%. "
            f"Previously bootstrapped NeoManpower to 50+ B2B enterprise clients and 200+ on-ground deployments "
            f"with zero SLA breaches. Adept in {keywords_str}, SQL telemetry, and cross-functional execution."
        )
        tailored_summary = sanitize_builder_text(tailored_summary)

        context = self.profile_engine.get_template_context(
            tailored_keywords=matching_skills,
            custom_summary=tailored_summary
        )

        # Highlight the most relevant project first based on job requirements
        if "ai" in job_text or "llm" in job_text or "prompt" in job_text:
            context["featured_projects"] = sorted(
                context["featured_projects"],
                key=lambda p: 0 if "EvalGuard" in p["name"] else 1
            )
        elif "fintech" in job_text or "kyc" in job_text or "compliance" in job_text:
            context["featured_projects"] = sorted(
                context["featured_projects"],
                key=lambda p: 0 if "VeriShield" in p["name"] else 1
            )
        elif "logistics" in job_text or "marketplace" in job_text or "operations" in job_text:
            context["featured_projects"] = sorted(
                context["featured_projects"],
                key=lambda p: 0 if "AutoMatch" in p["name"] else 1
            )

        # Render HTML
        html_template = self.jinja_env.get_template("resume_template.html")
        html_content = html_template.render(**context)

        # Render Markdown
        md_template = self.jinja_env.get_template("resume_template.md")
        md_content = md_template.render(**context)

        html_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_CV.html"
        md_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_CV.md"
        pdf_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_CV.pdf"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Generate single-page PDF via Playwright
        self._export_pdf(html_path, pdf_path)

        return {
            "html_path": str(html_path),
            "md_path": str(md_path),
            "pdf_path": str(pdf_path)
        }

    def _export_pdf(self, html_path: Path, pdf_path: Path):
        """Converts HTML resume to single-page PDF using Playwright headless Chromium."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "8.5mm", "bottom": "8.5mm", "left": "10.5mm", "right": "10.5mm"},
                    prefer_css_page_size=True,
                )
                browser.close()
        except Exception as e:
            logger.warning(f"Playwright PDF generation failed, falling back: {e}")
            # Try weasyprint if available
            try:
                from weasyprint import HTML
                HTML(str(html_path)).write_pdf(str(pdf_path))
            except Exception as w_err:
                logger.error(f"Both Playwright and Weasyprint PDF exports failed: {w_err}")

    def generate_cover_letter(self, job: ScrapedJob, eval_result: Optional[EvaluationResult], safe_company: str) -> Dict[str, str]:
        """Generates crisp under-130-word human builder cover letter note."""
        hiring_person = job.hr_name or "Hiring Team"
        
        # Determine product focus from job role/description
        job_lower = f"{job.role} {job.raw_description}".lower()
        if "fleet" in job_lower or "delivery" in job_lower or "logistics" in job_lower:
            product_focus = "driver fleet operations and dispatch SLAs"
        elif "ai" in job_lower or "llm" in job_lower:
            product_focus = "AI workflows and inference latency optimization"
        elif "kyc" in job_lower or "fintech" in job_lower or "verification" in job_lower:
            product_focus = "automated verification and compliance funnels"
        elif "b2b" in job_lower or "enterprise" in job_lower:
            product_focus = "enterprise onboarding and customer discovery roadmaps"
        else:
            product_focus = f"core product discovery and feature delivery for {job.role}"

        template = self.jinja_env.get_template("cover_letter_template.txt")
        rendered = template.render(
            hiring_person=hiring_person,
            company=job.company,
            role=job.role,
            product_focus=product_focus
        )
        rendered = sanitize_builder_text(rendered)

        txt_path = self.exports_letters_dir / f"Manav_Mate_{safe_company}_CoverLetter.txt"
        md_path = self.exports_letters_dir / f"Manav_Mate_{safe_company}_CoverLetter.md"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Cover Letter: {job.role} at {job.company}\n\n{rendered}\n")

        return {
            "cover_letter_txt": str(txt_path),
            "cover_letter_md": str(md_path)
        }
