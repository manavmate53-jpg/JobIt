"""ATS Resume & Cover Letter Tailoring Engine.

Inspired by Resume-Matcher's modular architecture:
- ATSScorer: 5-signal deterministic ATS score breakdown (keywords, skills, title, completeness, dates).
- BulletSelector: Dynamic achievement relevance scoring and ordering.
- KeywordAligner: Natural JD keyword extraction and competency alignment.
- WritingQualityAudit: Em dash scrubbing, weak opener removal, and metric preservation.
- PageFitValidator: Single-page A4 vertical height and word budget enforcement.
"""

from __future__ import annotations

import json
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
from src.services.ats_scorer import ATSScorer, ATSReport
from src.services.bullet_selector import BulletSelector
from src.services.keyword_aligner import KeywordAligner
from src.services.writing_quality import WritingQualityAudit
from src.services.page_fit import PageFitValidator

logger = logging.getLogger(__name__)


def clean_filename(name: str) -> str:
    """Sanitizes company or role name for file naming."""
    clean = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[-\s]+", "_", clean)


class TailorEngine:
    """Generates tailored ATS resumes and builder cover letters leveraging Resume-Matcher services."""

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

        # Resume-Matcher inspired services
        self.ats_scorer = ATSScorer()
        self.bullet_selector = BulletSelector()
        self.keyword_aligner = KeywordAligner()

    def tailor(self, job: ScrapedJob, eval_result: Optional[EvaluationResult] = None) -> Dict[str, Any]:
        """Runs end-to-end tailoring for a job posting. Generates HTML, PDF, MD, ATS Report, and Cover Letter."""
        safe_company = clean_filename(job.company)
        
        # 1. Generate Resume files and ATS Report
        resume_outputs = self.generate_resume(job, eval_result, safe_company)
        
        # 2. Generate Cover Letter
        letter_outputs = self.generate_cover_letter(job, eval_result, safe_company)
        
        combined = {**resume_outputs, **letter_outputs}
        return combined

    def generate_resume(
        self,
        job: ScrapedJob,
        eval_result: Optional[EvaluationResult],
        safe_company: str
    ) -> Dict[str, Any]:
        """Generates tailored HTML, Markdown, PDF resumes, and comprehensive ATS Match Report."""
        jd_text = f"{job.role} {job.raw_description}"
        base_ctx = self.profile_engine.get_template_context()

        # Step 1: Align Keywords using KeywordAligner
        alignment = self.keyword_aligner.align_keywords(base_ctx["skills"], jd_text)
        tailored_skills = alignment["aligned_skills"]
        priority_kw = alignment["priority_keywords"]

        # Step 2: Dynamically rank achievements using BulletSelector
        tailored_experience = self.bullet_selector.rank_experience_bullets(
            base_ctx["work_experience"],
            jd_text=jd_text,
            max_bullets_per_role=5
        )

        # Step 3: Prioritize interactive projects based on JD domain
        tailored_projects = self.bullet_selector.rank_featured_projects(
            base_ctx["featured_projects"],
            jd_text=jd_text
        )

        # Step 4: Craft tailored summary with injected keywords and target role
        keywords_str = ", ".join(priority_kw[:3])
        tailored_summary = (
            f"Early-career {job.role} and former founder with hands-on background in "
            f"0-to-1 product discovery, technical PRDs, and delivery. At HireFlo India, drove a 40% reduction in "
            f"Llama 3.1 inference compute costs via NVIDIA NIM and improved user onboarding completion by 30%. "
            f"Previously bootstrapped NeoManpower to 50+ B2B enterprise clients and 200+ on-ground deployments "
            f"with zero SLA breaches. Adept in {keywords_str}, SQL telemetry, and cross-functional execution."
        )
        tailored_summary = WritingQualityAudit.clean_text(tailored_summary)

        # Step 5: Assemble tailored context
        context = dict(base_ctx)
        context["summary"] = tailored_summary
        context["skills"] = tailored_skills
        context["work_experience"] = tailored_experience
        context["featured_projects"] = tailored_projects

        # Step 6: Single-Page Budget Enforcement (PageFitValidator)
        context = PageFitValidator.enforce_single_page(context)
        is_fit, total_words, fit_warnings = PageFitValidator.audit_context(context)

        # Step 7: Render HTML & Markdown
        html_template = self.jinja_env.get_template("resume_template.html")
        html_content = html_template.render(**context)

        md_template = self.jinja_env.get_template("resume_template.md")
        md_content = md_template.render(**context)

        # Step 8: Compute ATS Score Report (ATSScorer)
        resume_plain_text = f"{context['name']} {context['summary']} {json.dumps(context['skills'])} {json.dumps(context['work_experience'])}"
        ats_report = self.ats_scorer.evaluate(
            resume_text=resume_plain_text,
            resume_context=context,
            job_role=job.role,
            job_description=jd_text
        )

        html_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_CV.html"
        md_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_CV.md"
        pdf_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_CV.pdf"
        report_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_ATS_Report.json"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "job": {"company": job.company, "role": job.role},
                "ats_report": ats_report.model_dump(),
                "page_fit": {
                    "is_single_page_guaranteed": is_fit,
                    "total_words": total_words,
                    "warnings": fit_warnings
                }
            }, f, indent=2)

        # Step 9: Render single-page PDF via Playwright
        self._export_pdf(html_path, pdf_path)

        return {
            "html_path": str(html_path),
            "md_path": str(md_path),
            "pdf_path": str(pdf_path),
            "ats_report_path": str(report_path),
            "ats_score": ats_report.overall_score,
            "ats_report": ats_report
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
            try:
                from weasyprint import HTML
                HTML(str(html_path)).write_pdf(str(pdf_path))
            except Exception as w_err:
                logger.error(f"Both Playwright and Weasyprint PDF exports failed: {w_err}")

    def generate_cover_letter(
        self,
        job: ScrapedJob,
        eval_result: Optional[EvaluationResult],
        safe_company: str
    ) -> Dict[str, str]:
        """Generates crisp under-130-word human builder cover letter note."""
        hiring_person = job.hr_name or "Hiring Team"
        
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
        rendered = WritingQualityAudit.clean_text(rendered)

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
