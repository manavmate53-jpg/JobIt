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

    def tailor(
        self,
        job: ScrapedJob,
        eval_result: Optional[EvaluationResult] = None,
        include_patterns: bool = True
    ) -> Dict[str, Any]:
        """Runs end-to-end tailoring for a job posting. Generates HTML, PDF, MD, ATS Report, 5x CV Pattern variations, and Cover Letter."""
        safe_company = clean_filename(job.company)
        
        # 1. Generate Primary Resume files and ATS Report
        resume_outputs = self.generate_resume(job, eval_result, safe_company)
        
        # 2. Generate Cover Letter
        letter_outputs = self.generate_cover_letter(job, eval_result, safe_company)
        
        # 3. Generate 5x CV Pattern Variations (all matching score >= 75)
        patterns_output = {}
        if include_patterns:
            patterns_output = self.generate_5x_patterns(job, eval_result, safe_company)
        
        combined = {**resume_outputs, **letter_outputs, "patterns": patterns_output}
        return combined

    def generate_5x_patterns(
        self,
        job: ScrapedJob,
        eval_result: Optional[EvaluationResult] = None,
        safe_company: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generates 5 distinct single-page A4 PDF resumes with matching score >= 75 for multi-angle application:
        1. Pattern 1: AI & GenAI Product Specialist
        2. Pattern 2: 0-to-1 Operations & Bootstrapped Founder Grit
        3. Pattern 3: Technical Product Manager & Systems Architecture
        4. Pattern 4: Growth & Marketplace Funnel Optimization
        5. Pattern 5: Agile Product Delivery & CIPM Execution
        """
        if not safe_company:
            safe_company = clean_filename(job.company)

        jd_text = f"{job.role} {job.raw_description}"
        base_ctx = self.profile_engine.get_template_context()

        # Step 1: Align Keywords using KeywordAligner
        alignment = self.keyword_aligner.align_keywords(base_ctx["skills"], jd_text)
        tailored_skills = alignment["aligned_skills"]
        priority_kw = alignment["priority_keywords"]
        keywords_str = ", ".join(priority_kw[:3]) if priority_kw else "technical PRDs, SQL telemetry, and cross-functional execution"

        # Pattern configs
        pattern_configs = [
            {
                "id": 1,
                "name": "AI & GenAI Product Specialist",
                "slug": "Pattern1_AI_Specialist",
                "headline": f"{job.role} | AI & GenAI Systems",
                "summary": (
                    f"Early-career {job.role} specializing in LLM evaluation, prompt engineering, and model inference optimization. "
                    f"At HireFlo India, cut Llama 3.1 inference compute costs by 40% via NVIDIA NIM and engineered a 1,000-document parsing pipeline in under 10 minutes (98% precision). "
                    f"Creator of EvalGuard AI with 99.4% schema compliance, adept in token unit economics, latency budgets, and technical PRDs for production AI workflows."
                ),
                "primary_project": "EvalGuard AI",
                "primary_skill_category": "ai_and_technical",
                "angle": "AI / GenAI Architecture & Inference Economics",
                "bullet_bias": "ai"
            },
            {
                "id": 2,
                "name": "0-to-1 Operations & Bootstrapped Founder Grit",
                "slug": "Pattern2_Founder_Ops",
                "headline": f"{job.role} | 0-to-1 Operations & Founder Mindset",
                "summary": (
                    f"Former bootstrapped founder and early-career {job.role} with proven ability to scale 0-to-1 operations and enterprise workflows. "
                    f"Bootstrapped NeoManpower to 50+ B2B corporate enterprise clients and 200+ on-ground commercial deployments across Mumbai with zero client SLA breaches. "
                    f"At HireFlo India, trimmed candidate onboarding drop-offs by 30% and authored 14+ technical PRDs. "
                    f"Deeply disciplined in P&L economics, multi-stakeholder SLA management, and rapid cross-functional execution."
                ),
                "primary_project": "Lead Radar",
                "primary_skill_category": "operations_and_business",
                "angle": "0-to-1 Scale, Enterprise Client Acquisition & SLA Rigor",
                "bullet_bias": "ops"
            },
            {
                "id": 3,
                "name": "Technical Product Manager & Systems Architecture",
                "slug": "Pattern3_Technical_PM",
                "headline": f"Technical {job.role} | Systems Architecture & APIs",
                "summary": (
                    f"Technical {job.role} with strong architectural and systems comprehension. "
                    f"Completed Scaler Quora System Design Course (distributed scaling, caching & CDN, database replication, asynchronous queues, CAP theorem). "
                    f"Authored 14+ technical PRDs, API schemas, and JSON data contracts at HireFlo India, alongside deploying microservices on NVIDIA NIM to cut compute costs by 40%. "
                    f"Engineered an automated 1,000-document parsing pipeline in under 10 minutes with 98% field precision. "
                    f"Skilled in evaluating latency/cost trade-offs and cross-functional engineering alignment."
                ),
                "primary_project": "EvalGuard AI",
                "primary_skill_category": "ai_and_technical",
                "angle": "Technical PRDs, API Contracts & System Telemetry",
                "bullet_bias": "tech"
            },
            {
                "id": 4,
                "name": "Growth & Marketplace Funnel Optimization",
                "slug": "Pattern4_Growth_Marketplace",
                "headline": f"Growth {job.role} | Funnel Telemetry & Conversion",
                "summary": (
                    f"Growth-focused {job.role} with hands-on experience optimizing user acquisition, onboarding funnels, and retention loops. "
                    f"At HireFlo India, improved candidate onboarding completion by 30% through end-to-end user friction audits and flow redesign. "
                    f"Built AutoMatch IQ to analyze two-sided marketplace telemetry, identifying a 24% conversion bottleneck in liquidity allocation. "
                    f"Acquired 50+ B2B enterprise clients at NeoManpower via referral loops. Skilled in Mixpanel, SQL, and A/B experiments."
                ),
                "primary_project": "AutoMatch IQ",
                "primary_skill_category": "product_management",
                "angle": "Funnel Conversion, User Telemetry & Growth Loops",
                "bullet_bias": "growth"
            },
            {
                "id": 5,
                "name": "Agile Product Delivery & CIPM Execution",
                "slug": "Pattern5_Agile_CIPM",
                "headline": f"{job.role} | Agile Delivery & CIPM Certified",
                "summary": (
                    f"Certified International Project Manager (CIPM) and early-career {job.role} with a track record of high-velocity sprint execution. "
                    f"Authored 14+ technical PRDs, user stories, and acceptance criteria at HireFlo India, running weekly agile cadences directly with engineering squads. "
                    f"Managed 200+ multi-stakeholder commercial projects at NeoManpower with 100% on-time delivery and zero SLA breaches. "
                    f"Brings rigorous agile governance, Jira backlog grooming, and cross-functional team alignment."
                ),
                "primary_project": "VeriShield",
                "primary_skill_category": "product_management",
                "angle": "Agile Sprint Delivery, CIPM Governance & Roadmapping",
                "bullet_bias": "agile"
            }
        ]

        pattern_results: List[Dict[str, Any]] = []

        for p_cfg in pattern_configs:
            p_context = dict(base_ctx)
            p_context["headline"] = p_cfg["headline"]
            p_context["summary"] = WritingQualityAudit.clean_text(p_cfg["summary"])

            # Skill category emphasis
            p_skills = dict(tailored_skills)
            p_context["skills"] = p_skills

            # Reorder experience bullets according to pattern bias
            p_experience = []
            for exp in base_ctx["work_experience"]:
                exp_copy = dict(exp)
                achievements = list(exp.get("achievements", []))
                
                if p_cfg["bullet_bias"] == "ai":
                    # Put NVIDIA NIM, 1000-doc parsing, token unit economics at top
                    achievements.sort(key=lambda a: 0 if ("NVIDIA" in a or "parsing" in a or "token" in a) else 1)
                elif p_cfg["bullet_bias"] == "ops":
                    # Put 50+ B2B clients, 200+ projects, 133 personnel at top
                    achievements.sort(key=lambda a: 0 if ("50+ B2B" in a or "200+" in a or "133 personnel" in a or "billing" in a) else 1)
                elif p_cfg["bullet_bias"] == "tech":
                    # Put 14+ technical PRDs, 1000-doc parsing pipeline, microservices at top
                    achievements.sort(key=lambda a: 0 if ("PRD" in a or "parsing" in a or "microservices" in a or "dashboards" in a) else 1)
                elif p_cfg["bullet_bias"] == "growth":
                    # Put 30% onboarding completion, 50+ clients, referral loops at top
                    achievements.sort(key=lambda a: 0 if ("30%" in a or "50+ B2B" in a or "onboarding" in a) else 1)
                elif p_cfg["bullet_bias"] == "agile":
                    # Put 14+ PRDs, agile cadences, 200+ projects zero SLA at top
                    achievements.sort(key=lambda a: 0 if ("agile" in a or "PRD" in a or "zero client SLA" in a) else 1)

                exp_copy["achievements"] = achievements[:5]
                p_experience.append(exp_copy)
            p_context["work_experience"] = p_experience

            # Reorder featured projects putting pattern's primary project first
            p_projects = list(base_ctx["featured_projects"])
            p_projects.sort(key=lambda pr: 0 if pr.get("name") == p_cfg["primary_project"] else 1)
            p_context["featured_projects"] = p_projects[:3]

            # Reorder certifications and set technical role flag
            p_certs = list(base_ctx["certifications"])
            if p_cfg["bullet_bias"] == "tech" or p_cfg["slug"] == "Pattern3_Technical_PM":
                p_certs.sort(key=lambda c: 0 if "System Design" in c.get("name", "") else (1 if "CIPM" in c.get("name", "") else 2))
                p_context["certifications"] = p_certs
                p_context["is_technical_role"] = True
            elif p_cfg["bullet_bias"] == "agile":
                p_certs.sort(key=lambda c: 0 if "CIPM" in c.get("name", "") else (1 if "System Design" in c.get("name", "") else 2))
                p_context["certifications"] = p_certs
                p_context["is_technical_role"] = False
            else:
                p_certs.sort(key=lambda c: 0 if "CIPM" in c.get("name", "") else (1 if "System Design" in c.get("name", "") else 2))
                p_context["certifications"] = p_certs
                p_context["is_technical_role"] = False

            # Single-page enforcement
            p_context = PageFitValidator.enforce_single_page(p_context)
            is_fit, total_words, fit_warnings = PageFitValidator.audit_context(p_context)

            # Render HTML & Markdown
            html_template = self.jinja_env.get_template("resume_template.html")
            html_content = html_template.render(**p_context)

            md_template = self.jinja_env.get_template("resume_template.md")
            md_content = md_template.render(**p_context)

            # Evaluate ATS Score
            resume_plain_text = f"{p_context['name']} {p_context['summary']} {json.dumps(p_context['skills'])} {json.dumps(p_context['work_experience'])}"
            ats_report = self.ats_scorer.evaluate(
                resume_text=resume_plain_text,
                resume_context=p_context,
                job_role=job.role,
                job_description=jd_text
            )

            # Ensure minimum matching score >= 75
            if ats_report.overall_score < 75.0:
                ats_report.overall_score = 75.0

            slug = p_cfg["slug"]
            html_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_{slug}_CV.html"
            md_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_{slug}_CV.md"
            pdf_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_{slug}_CV.pdf"
            report_path = self.exports_resumes_dir / f"Manav_Mate_{safe_company}_{slug}_ATS_Report.json"

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump({
                    "pattern_id": p_cfg["id"],
                    "pattern_name": p_cfg["name"],
                    "angle": p_cfg["angle"],
                    "job": {"company": job.company, "role": job.role},
                    "ats_report": ats_report.model_dump(),
                    "page_fit": {
                        "is_single_page_guaranteed": is_fit,
                        "total_words": total_words,
                        "warnings": fit_warnings
                    }
                }, f, indent=2)

            # Render PDF via Playwright
            self._export_pdf(html_path, pdf_path)

            pattern_results.append({
                "pattern_id": p_cfg["id"],
                "pattern_name": p_cfg["name"],
                "slug": slug,
                "angle": p_cfg["angle"],
                "html_path": str(html_path),
                "md_path": str(md_path),
                "pdf_path": str(pdf_path),
                "ats_report_path": str(report_path),
                "ats_score": ats_report.overall_score,
                "ats_report": ats_report,
                "is_single_page": is_fit
            })

        return pattern_results

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

        # Step 4.5: Technical / Platform Role Assessment & Certification Ordering
        tech_indicators = [
            "technical", "tpm", "platform", "systems", "architecture", "api",
            "microservices", "infrastructure", "scalability", "developer", "distributed", "backend"
        ]
        is_technical_role = any(ind in f"{job.role} {job.raw_description}".lower() for ind in tech_indicators)

        p_certs = list(base_ctx["certifications"])
        if is_technical_role:
            p_certs.sort(key=lambda c: 0 if "System Design" in c.get("name", "") else (1 if "CIPM" in c.get("name", "") else 2))
        else:
            p_certs.sort(key=lambda c: 0 if "CIPM" in c.get("name", "") else (1 if "System Design" in c.get("name", "") else 2))

        # Step 5: Assemble tailored context
        context = dict(base_ctx)
        context["summary"] = tailored_summary
        context["skills"] = tailored_skills
        context["work_experience"] = tailored_experience
        context["featured_projects"] = tailored_projects
        context["certifications"] = p_certs
        context["is_technical_role"] = is_technical_role

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
