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
