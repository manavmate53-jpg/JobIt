import pytest
from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import ScoringEngine


def test_deterministic_scoring_mumbai_entry_ai():
    engine = ScoringEngine()
    job = ScrapedJob(
        company="FastAI",
        role="Associate Product Manager",
        job_url="https://example.com/apm-ai",
        source="LinkedIn",
        location="Mumbai, Maharashtra",
        experience_years="1-3 years",
        raw_description="Looking for an APM with AI PRD knowledge, SQL telemetry, and prompt engineering."
    )
    score = engine.compute_deterministic_score(job)
    # 15 (location) + 15 (experience) + 10 (domain) = 40
    assert score == 40


def test_evaluation_pipeline_apply_decision():
    engine = ScoringEngine()
    job = ScrapedJob(
        company="Zepto",
        role="Associate Product Manager - Fleet",
        job_url="https://example.com/zepto-test",
        source="LinkedIn",
        location="Mumbai",
        experience_years="1-2 years",
        raw_description="Manage fleet SLA, SQL analytics, wireframing in Figma, and operations planning."
    )
    res = engine.evaluate(job)
    assert res.fit_score >= 75
    assert res.decision == "APPLY"
    assert len(res.matching_skills) > 0
    assert len(res.recommended_angle) > 0


def test_evaluation_pipeline_filtered_out():
    engine = ScoringEngine()
    job = ScrapedJob(
        company="Sleepwell Foam Ltd",
        role="Production Supervisor",
        job_url="https://example.com/foam",
        source="Web",
        location="Mumbai",
        raw_description="Mattress and foam production line controller"
    )
    res = engine.evaluate(job)
    assert res.is_filtered_out is True
    assert res.fit_score == 0
    assert res.decision == "SKIP"


def test_technical_pm_system_architecture_scoring():
    engine = ScoringEngine()
    job = ScrapedJob(
        company="ScaleInfra",
        role="Technical Product Manager - API Platform",
        job_url="https://example.com/tpm-scale",
        source="Arc.dev",
        location="Remote",
        raw_description="Own microservices API platform, evaluating system architecture, latency trade-offs, and database scaling."
    )
    res = engine.evaluate(job)
    assert res.fit_score >= 80
    assert res.decision == "APPLY"
    assert any("System Architecture" in s for s in res.matching_skills)
    assert "Scaler" in res.gap_analysis or "Scaler" in res.recommended_angle
