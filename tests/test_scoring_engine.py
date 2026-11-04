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


def test_gatekeeper_blocks_legacy_bank_and_mnc():
    engine = ScoringEngine()
    bank_job = ScrapedJob(
        company="HDFC Bank",
        role="Product Manager",
        job_url="https://hdfc.com/pm",
        source="Naukri",
        location="Mumbai",
        raw_description="Manage core banking features."
    )
    res_bank = engine.evaluate(bank_job)
    assert res_bank.is_filtered_out is True
    assert res_bank.decision == "SKIP"
    assert "Blacklisted" in res_bank.filter_reason

    mnc_job = ScrapedJob(
        company="Accenture",
        role="Associate Product Manager",
        job_url="https://accenture.com/apm",
        source="LinkedIn",
        location="Bengaluru",
        raw_description="Consulting tech delivery."
    )
    res_mnc = engine.evaluate(mnc_job)
    assert res_mnc.is_filtered_out is True
    assert res_mnc.decision == "SKIP"
    assert "Blacklisted" in res_mnc.filter_reason


def test_pillar_pipeline_classification_and_boost():
    engine = ScoringEngine()
    fo_job = ScrapedJob(
        company="Stealth AI",
        role="Founder's Office",
        job_url="https://stealthai.com/fo",
        source="Wellfound",
        location="Mumbai",
        experience_years="1-3 years",
        raw_description="Work directly with founders on commercial ops, PRDs, and 0-to-1 execution."
    )
    res_fo = engine.evaluate(fo_job)
    assert res_fo.is_filtered_out is False
    assert res_fo.fit_score >= 75
    assert res_fo.decision == "APPLY"
    assert res_fo.pillar == "PILLAR_1_FOUNDERS_OFFICE"
    assert "Founder" in res_fo.pillar_label
    assert len(res_fo.matched_lab_builds) > 0
    assert res_fo.suggested_ctc_quoted == 7.0  # Calibrated down by 2L for Seed/Pre-series A

    ops_job = ScrapedJob(
        company="KiteLogistics",
        role="Product Operations Manager",
        job_url="https://kitelogistics.com/ops",
        source="Instahyre",
        location="Mumbai",
        experience_years="1-2 years",
        raw_description="Manage field dispatch operations, shift workflows, and SLA metrics."
    )
    res_ops = engine.evaluate(ops_job)
    assert res_ops.is_filtered_out is False
    assert res_ops.fit_score >= 75
    assert res_ops.decision == "APPLY"
    assert res_ops.pillar == "PILLAR_2_PRODUCT_OPERATIONS"
    assert len(res_ops.matched_lab_builds) > 0
