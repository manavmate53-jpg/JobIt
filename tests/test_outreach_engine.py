import os
import pytest
from src.scrapers.base_scraper import ScrapedJob
from src.outreach_engine import OutreachEngine, ContactEnricher


def test_contact_permutations():
    enricher = ContactEnricher()
    perms = enricher.generate_permutations("Rohan Deshmukh", "zepto.co")
    assert "rohan.deshmukh@zepto.co" in perms
    assert "rohan@zepto.co" in perms


def test_outreach_dry_run_safety():
    engine = OutreachEngine()
    job = ScrapedJob(
        company="BrowserStack",
        role="Associate Product Manager",
        job_url="https://example.com/bs-apm",
        source="Naukri",
        hr_name="Divya Kulkarni",
        hr_email="divya.kulkarni@browserstack.com"
    )

    result = engine.process_outreach(job, pdf_path=None, dry_run=True)
    assert result["mode"] == "DRY_RUN"
    assert result["dispatched"] is False
    assert os.path.exists(result["draft_txt_path"])
    assert result["draft"]["linkedin_note_chars"] <= 300
    assert "—" not in result["draft"]["email_body"]


def test_anti_bounce_shield_blocks_unverified():
    engine = OutreachEngine()
    # Job without verified email
    job = ScrapedJob(
        company="BrowserStack",
        role="Associate Product Manager",
        job_url="https://example.com/bs-apm",
        source="Naukri",
        hr_name="Divya Kulkarni",
        hr_email=None  # Unverified
    )

    # Attempting to dispatch with dry_run=False should be blocked by the shield
    result = engine.process_outreach(job, pdf_path=None, dry_run=False)
    assert result["dispatched"] is False
    assert "Failsafe Deliverability Shield" in result["smtp_details"]["error"]


def test_dual_outreach_generation():
    engine = OutreachEngine()
    job = ScrapedJob(
        company="Perplexity AI",
        role="AI Product Manager - LLM Evaluation & Search Quality",
        job_url="https://wellfound.com/jobs/perplexity-ai-pm-llm-eval-search-948101",
        source="Wellfound",
        founder_name="Aravind Srinivas",
        hr_name="Talent Team"
    )

    dual = engine.process_dual_outreach(job, pdf_path=None, dry_run=True)
    assert "founder" in dual
    assert "ta" in dual

    # Check founder outreach
    founder_draft = dual["founder"]["draft"]
    assert founder_draft["contact"]["name"] == "Aravind Srinivas"
    assert founder_draft["linkedin_note_chars"] <= 300
    assert "bootstrapped" in founder_draft["email_body"].lower() or "nvidia nim" in founder_draft["email_body"].lower()
    assert "—" not in founder_draft["email_body"]

    # Check TA outreach
    ta_draft = dual["ta"]["draft"]
    assert ta_draft["contact"]["name"] == "Talent Acquisition Team" or "Talent" in ta_draft["contact"]["name"]
    assert ta_draft["linkedin_note_chars"] <= 300
    assert "—" not in ta_draft["email_body"]
    assert os.path.exists(dual["founder"]["draft_txt_path"])
    assert os.path.exists(dual["ta"]["draft_txt_path"])
