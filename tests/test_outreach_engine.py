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
