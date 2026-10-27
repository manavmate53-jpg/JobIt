import os
import pytest
from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import ScoringEngine
from src.tailor_engine import TailorEngine


def test_5x_cv_pattern_variations():
    engine = ScoringEngine()
    tailor = TailorEngine()

    job = ScrapedJob(
        company="Korbit AI",
        role="Product Manager",
        job_url="https://wellfound.com/jobs/korbit-ai-product-manager-code-review-849102",
        source="Wellfound",
        location="Remote Worldwide",
        experience_years="1-3 years",
        raw_description=(
            "Korbit AI is building an autonomous AI code reviewer powered by LLMs. "
            "We are seeking an AI Product Manager to lead model benchmark evaluation, token latency budgets, "
            "and PRD specifications for GitHub integrations. Requirements: LLM prompt engineering, "
            "NVIDIA NIM or inference pipelines, user telemetry, and strong developer empathy."
        )
    )

    eval_result = engine.evaluate(job)
    patterns = tailor.generate_5x_patterns(job, eval_result)

    assert len(patterns) == 5, f"Expected 5 pattern variations, got {len(patterns)}"

    expected_slugs = [
        "Pattern1_AI_Specialist",
        "Pattern2_Founder_Ops",
        "Pattern3_Technical_PM",
        "Pattern4_Growth_Marketplace",
        "Pattern5_Agile_CIPM"
    ]

    for idx, p in enumerate(patterns):
        assert p["slug"] == expected_slugs[idx]
        assert p["ats_score"] >= 75.0, f"{p['slug']} score {p['ats_score']} is below 75"
        assert p["is_single_page"] is True, f"{p['slug']} exceeded single page A4 budget"
        assert os.path.exists(p["html_path"]), f"HTML path missing for {p['slug']}"
        assert os.path.exists(p["md_path"]), f"Markdown path missing for {p['slug']}"
        assert os.path.exists(p["pdf_path"]), f"PDF path missing for {p['slug']}"
        assert os.path.exists(p["ats_report_path"]), f"ATS report missing for {p['slug']}"

        # Verify PDF non-empty
        assert os.path.getsize(p["pdf_path"]) > 10000

        # Verify no em dashes or corporate buzzwords
        with open(p["md_path"], "r", encoding="utf-8") as f:
            md_text = f.read()
        assert "—" not in md_text
        assert " -- " not in md_text
        assert "spearheaded" not in md_text.lower()
        assert "synergistic" not in md_text.lower()

        # Verify candidate truth maintained
        assert "HireFlo India" in md_text
        assert "NeoManpower" in md_text
        assert "40%" in md_text or "50+" in md_text
