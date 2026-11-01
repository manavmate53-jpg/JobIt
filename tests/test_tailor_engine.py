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


def test_dynamic_project_selection_categories():
    tailor = TailorEngine()
    projects = tailor.profile_engine.profile.featured_projects
    proj_dicts = [p.model_dump() for p in projects]

    # 1. Fintech JD -> PayRouter Engine & VeriShield lead
    fintech_ranked = tailor.bullet_selector.rank_featured_projects(
        proj_dicts,
        jd_text="Leading payment gateway integration, smart routing, checkout MDR fees, and KYC fraud verification."
    )
    assert fintech_ranked[0]["name"] == "PayRouter Engine"
    assert any(p["name"] == "VeriShield" for p in fintech_ranked[:2])

    # 2. High Scale / Infrastructure JD -> FlashQueue Simulator leads
    scale_ranked = tailor.bullet_selector.rank_featured_projects(
        proj_dicts,
        jd_text="High concurrency distributed systems architecture, caching, virtual waiting room, and traffic surge rate limiting."
    )
    assert scale_ranked[0]["name"] == "FlashQueue Simulator"
    assert any(p["name"] == "PayRouter Engine" for p in scale_ranked[:3])

    # 3. Operations / Marketplace JD -> CrewRoster Dashboard & AutoMatch IQ lead
    ops_ranked = tailor.bullet_selector.rank_featured_projects(
        proj_dicts,
        jd_text="Frontline workforce operations, shift rostering, attendance dispatch logistics, and two-sided marketplace discovery."
    )
    assert ops_ranked[0]["name"] == "CrewRoster Dashboard"
    assert any(p["name"] == "AutoMatch IQ" for p in ops_ranked[:2])

    # 4. B2B SaaS / AI JD -> EvalGuard AI leads
    ai_ranked = tailor.bullet_selector.rank_featured_projects(
        proj_dicts,
        jd_text="Production LLM agents, prompt evaluation, JSON schema guardrails, and token unit economics."
    )
    assert ai_ranked[0]["name"] == "EvalGuard AI"


def test_master_cv_generation():
    tailor = TailorEngine()
    outputs = tailor.generate_master_cv(output_name="Test_Manav_Mate_Master_CV")

    assert os.path.exists(outputs["html_path"])
    assert os.path.exists(outputs["md_path"])
    assert os.path.exists(outputs["pdf_path"])
    assert outputs["is_single_page"] is True
    assert os.path.getsize(outputs["pdf_path"]) > 10000

    with open(outputs["md_path"], "r", encoding="utf-8") as f:
        md_text = f.read()

    # Verify candidate ground truth and credentials
    assert "Manav Mate" in md_text
    assert "Jogeshwari East, Mumbai" in md_text
    assert "Scaler" in md_text
    assert "Quora System Design" in md_text
    assert "CIPM" in md_text
    assert "HireFlo India" in md_text
    assert "NeoManpower" in md_text
    assert "PayRouter Engine" in md_text or "FlashQueue Simulator" in md_text
    assert "—" not in md_text
    assert " -- " not in md_text
