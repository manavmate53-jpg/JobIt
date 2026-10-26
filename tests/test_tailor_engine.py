import os
import pytest
from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import ScoringEngine
from src.tailor_engine import TailorEngine


def test_resume_and_cover_letter_generation():
    engine = ScoringEngine()
    tailor = TailorEngine()

    job = ScrapedJob(
        company="TestCorp AI",
        role="Product Manager",
        job_url="https://example.com/testcorp",
        source="LinkedIn",
        location="Mumbai",
        experience_years="1-3 years",
        raw_description="Design AI workflows, track token unit economics, and write PRDs in Jira."
    )

    eval_result = engine.evaluate(job)
    outputs = tailor.tailor(job, eval_result)

    assert os.path.exists(outputs["html_path"])
    assert os.path.exists(outputs["md_path"])
    assert os.path.exists(outputs["pdf_path"])
    assert os.path.exists(outputs["cover_letter_txt"])

    # Verify PDF has non-trivial size
    assert os.path.getsize(outputs["pdf_path"]) > 10000

    # Verify Cover Letter word count and tone
    with open(outputs["cover_letter_txt"], "r", encoding="utf-8") as f:
        content = f.read()
    
    words = content.split()
    assert len(words) <= 130
    assert "—" not in content
    assert "--" not in content
