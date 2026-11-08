import os
import pytest
from pathlib import Path
from src.tracker_db import TrackerDB
from src.analytics.telemetry_db import TelemetryDB
from src.scrapers.base_scraper import ScrapedJob

def test_pos_firewall_tracker_db(tmp_path: Path):
    db_file = tmp_path / "test_pos_jobit.db"
    db = TrackerDB(db_path=db_file)

    job = ScrapedJob(
        company="Razorpay",
        role="Product Manager",
        job_url="https://razorpay.com/careers/pm",
        source="Careers",
        location="Mumbai"
    )
    job_id = db.upsert_job(job)

    # 1. Attempting to update status to "Applied" without proof should divert to NEEDS_HUMAN_CLICK
    db.update_status(job_id, status="Applied")
    record = db.get_job_by_id(job_id)
    assert record["status"] == "NEEDS_HUMAN_CLICK"
    assert "PoS Firewall" in record["notes"]

    # 2. Calling mark_applied_verified without an existing file should raise ValueError
    with pytest.raises(ValueError, match="PoS Firewall Rejection"):
        db.mark_applied_verified(
            job_id=job_id,
            proof_screenshot_path="/nonexistent/screenshot.png",
            submission_url="https://razorpay.com/careers/pm"
        )

    # 3. Providing a real existing screenshot file and valid URL succeeds
    fake_screenshot = tmp_path / "razorpay_proof.png"
    fake_screenshot.write_text("fake screenshot data")

    success = db.mark_applied_verified(
        job_id=job_id,
        proof_screenshot_path=str(fake_screenshot),
        submission_url="https://razorpay.com/careers/pm/confirmation"
    )
    assert success is True

    record = db.get_job_by_id(job_id)
    assert record["status"] == "APPLIED_VERIFIED"
    assert record["proof_screenshot_path"] == str(fake_screenshot)
    assert record["submission_url"] == "https://razorpay.com/careers/pm/confirmation"

def test_pos_firewall_telemetry_db(tmp_path: Path):
    db_file = tmp_path / "test_pos_jobit_v2.db"
    tdb = TelemetryDB(db_path=db_file)

    opp_id = tdb.record_opportunity(
        company_name="Cashfree",
        role_title="APM",
        pillar="PILLAR_3_AI_APM",
        score=85
    )

    # Attempting fake apply via update_status reverts to NEEDS_HUMAN_CLICK
    tdb.update_status(opp_id, "APPLIED_PORTAL")
    with tdb._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status, notes FROM opportunities WHERE id = ?", (opp_id,))
        row = cur.fetchone()
        assert row["status"] == "NEEDS_HUMAN_CLICK"
        assert "PoS Firewall" in row["notes"]

    # Valid mark_applied_verified
    fake_screenshot = tmp_path / "cashfree_proof.png"
    fake_screenshot.write_text("proof bytes")

    tdb.mark_applied_verified(
        opportunity_id=opp_id,
        proof_screenshot_path=str(fake_screenshot),
        submission_url="https://cashfree.com/applied"
    )
    with tdb._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status, proof_screenshot_path, submission_url FROM opportunities WHERE id = ?", (opp_id,))
        row = cur.fetchone()
        assert row["status"] == "APPLIED_VERIFIED"
        assert row["proof_screenshot_path"] == str(fake_screenshot)
        assert row["submission_url"] == "https://cashfree.com/applied"


class MockLocator:
    def __init__(self, visible=False, enabled=True, text=""):
        self._visible = visible
        self._enabled = enabled
        self._text = text

    def is_visible(self, timeout=None):
        return self._visible

    def is_enabled(self, timeout=None):
        return self._enabled

    def inner_text(self):
        return self._text

    @property
    def first(self):
        return self


class MockPage:
    def __init__(self, url="", content_html="", locators=None):
        self.url = url
        self._content = content_html
        self._locators = locators or {}

    def content(self):
        return self._content

    def locator(self, selector):
        for key, loc in self._locators.items():
            if key.lower() in selector.lower():
                return loc
        return MockLocator(visible=False)


def test_blacklist_apply_now_rejected_even_with_thank_you():
    from src.ats_applier import verify_confirmation_screen, assert_confirmation_screen, SubmissionIncompleteError

    # Page has both "thank you for applying" and "apply now" visible
    page = MockPage(
        url="https://in.indeed.com/viewjob?jk=2051dab3e8356d40",
        content_html="<html><body><h1>Euro Panel Products</h1><p>Thank you for viewing. Apply now</p></body></html>",
        locators={
            "apply now": MockLocator(visible=True, text="Apply now")
        }
    )

    is_verified, reason = verify_confirmation_screen(page)
    assert is_verified is False
    assert "Pre-apply blacklist marker visible: 'apply now'" in reason

    with pytest.raises(SubmissionIncompleteError, match="Pre-apply blacklist marker visible"):
        assert_confirmation_screen(page)


def test_clickable_apply_button_rejected():
    from src.ats_applier import verify_confirmation_screen, assert_confirmation_screen, SubmissionIncompleteError

    # Page has confirmation text but an Apply button is still clickable
    page = MockPage(
        url="https://jobs.lever.co/example/123",
        content_html="<html><body><p>Thank you for applying</p><button>Apply for this job</button></body></html>",
        locators={
            "button:has-text('Apply')": MockLocator(visible=True, enabled=True, text="Apply for this job")
        }
    )

    is_verified, reason = verify_confirmation_screen(page)
    assert is_verified is False
    assert "Submit/Apply button still visible and clickable" in reason

    with pytest.raises(SubmissionIncompleteError, match="Submit/Apply button still visible"):
        assert_confirmation_screen(page)


def test_indeed_without_post_apply_or_submitted_fails():
    from src.ats_applier import verify_confirmation_screen, assert_confirmation_screen, SubmissionIncompleteError

    # Indeed page with description but no confirmation markers
    page = MockPage(
        url="https://in.indeed.com/viewjob?jk=c5d94c084ced26ba",
        content_html="<html><body><h1>Corporate Events Manager</h1><p>Requirements: 4 years exp</p></body></html>",
        locators={}
    )

    is_verified, reason = verify_confirmation_screen(page)
    assert is_verified is False
    assert "Indeed submission incomplete" in reason

    with pytest.raises(SubmissionIncompleteError, match="Indeed submission incomplete"):
        assert_confirmation_screen(page)


def test_indeed_genuine_confirmation_passes():
    from src.ats_applier import verify_confirmation_screen, assert_confirmation_screen

    # Genuine Indeed post-submission confirmation
    page = MockPage(
        url="https://in.indeed.com/post-apply?jk=2051dab3e8356d40",
        content_html="<html><body><h1>Your application has been submitted</h1><p>Your application was sent to Euro Panel Products Ltd</p></body></html>",
        locators={}
    )

    is_verified, reason = verify_confirmation_screen(page)
    assert is_verified is True
    assert "Indeed post-submission confirmation verified" in reason

    # Should not raise exception
    assert_confirmation_screen(page)


def test_lever_genuine_confirmation_passes():
    from src.ats_applier import verify_confirmation_screen, assert_confirmation_screen

    page = MockPage(
        url="https://jobs.lever.co/company/thanks",
        content_html="<html><body><h1>Thank you for applying</h1><p>We have received your application.</p></body></html>",
        locators={}
    )

    is_verified, reason = verify_confirmation_screen(page)
    assert is_verified is True
    assert "Lever post-submission confirmation verified" in reason


def test_greenhouse_genuine_confirmation_passes():
    from src.ats_applier import verify_confirmation_screen, assert_confirmation_screen

    page = MockPage(
        url="https://boards.greenhouse.io/company/confirmation",
        content_html="<html><body><h1>Application submitted!</h1><p>Thanks for applying to our team.</p></body></html>",
        locators={}
    )

    is_verified, reason = verify_confirmation_screen(page)
    assert is_verified is True
    assert "Greenhouse post-submission confirmation verified" in reason


