import os
from pathlib import Path
import pytest
from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import EvaluationResult
from src.tracker_db import TrackerDB


def test_tracker_db_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test_jobit.db"
    db = TrackerDB(db_path=db_file)

    job = ScrapedJob(
        company="AlphaCorp",
        role="Product Manager",
        job_url="https://alphacorp.com/pm",
        source="LinkedIn",
        location="Mumbai"
    )
    eval_res = EvaluationResult(
        deterministic_score=35,
        semantic_score=50,
        fit_score=85,
        decision="APPLY",
        matching_skills=["PRD", "SQL"],
        gap_analysis="None",
        recommended_angle="Highlight EvalGuard AI"
    )

    job_id = db.upsert_job(job, eval_res)
    assert job_id > 0

    record = db.get_job_by_id(job_id)
    assert record["company"] == "AlphaCorp"
    assert record["fit_score"] == 85
    assert record["decision"] == "APPLY"

    # Status update
    updated = db.update_status(job_id, status="Tailored", tailored_cv_path="/path/to/cv.pdf")
    assert updated is True

    record2 = db.get_job_by_id(job_id)
    assert record2["status"] == "Tailored"
    assert record2["tailored_cv_path"] == "/path/to/cv.pdf"
