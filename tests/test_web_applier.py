import os
import pytest
from src.scrapers.base_scraper import ScrapedJob
from src.web_applier import PortalWebApplier


def test_portal_web_applier_session_dirs():
    applier = PortalWebApplier()
    naukri_session = applier.get_session_path("naukri")
    linkedin_session = applier.get_session_path("linkedin")

    assert naukri_session.exists()
    assert linkedin_session.exists()
    assert os.path.isdir(applier.applications_dir)


def test_web_apply_missing_pdf():
    applier = PortalWebApplier()
    job = ScrapedJob(
        company="TestCorp",
        role="Product Manager",
        job_url="https://example.com/job",
        source="LinkedIn"
    )
    res = applier.apply(job, pdf_path="/non/existent/path.pdf", dry_run=True)
    assert res["success"] is False
    assert res["status"] == "ERROR"
