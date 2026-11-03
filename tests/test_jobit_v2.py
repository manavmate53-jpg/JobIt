"""
Unit and integration tests for JobIt v2.0:
Fresh Capital Signal Scraper, 3-Pillar Classifier, Gatekeeper Filter,
Scoring Rubric, 1-Page A4 CV Generation, Outreach Sequences & Telemetry Database.
"""

import json
import os
import re
from pathlib import Path
import pytest

from src.signals.funding_scraper import FundingSignal, FundingSignalScraper
from src.signals.wellfound_crosscheck import WellfoundCrossChecker
from src.signals.job_board_scraper import StartupJobBoardScraper
from src.strategy.gatekeeper_filter import GatekeeperFilter
from src.strategy.pillar_classifier import PillarClassifier, StrategicPillar
from src.strategy.scoring_engine import StrategyScoringEngine
from src.tailoring.proof_of_work_mapper import ProofOfWorkMapper
from src.tailoring.pillar_cv_generator import PillarCVGenerator
from src.outreach.decision_maker_finder import DecisionMakerFinder
from src.outreach.sequence_generator import SequenceGenerator
from src.analytics.telemetry_db import TelemetryDB


def test_funding_signal_scraper():
    scraper = FundingSignalScraper()
    signals = scraper.get_verified_signals()
    assert len(signals) >= 10, "Should have at least 10 verified funded startup signals"
    
    # Check signal fields
    first = signals[0]
    assert first.company_name
    assert first.funding_stage in ["Seed", "Pre-Series A", "Series A", "Series B"]
    assert first.sector
    assert first.hq_location
    assert len(first.founder_names) >= 1


def test_gatekeeper_blocks_enterprise_banks_and_it_mncs():
    gk = GatekeeperFilter()

    # Legacy banks must fail
    res_idfc = gk.evaluate(company_name="IDFC First Bank", role_title="Product Manager")
    assert not res_idfc.passed
    assert "BLACKLIST_BANK" in res_idfc.flags

    res_dbs = gk.evaluate(company_name="DBS Bank", role_title="Associate Product Manager")
    assert not res_dbs.passed
    assert "BLACKLIST_BANK" in res_dbs.flags

    # IT services MNCs must fail
    res_tcs = gk.evaluate(company_name="TCS", role_title="Product Manager")
    assert not res_tcs.passed
    assert "BLACKLIST_IT_MNC" in res_tcs.flags

    res_accenture = gk.evaluate(company_name="Accenture", role_title="Product Operations")
    assert not res_accenture.passed
    assert "BLACKLIST_IT_MNC" in res_accenture.flags

    # Seniority traps must fail
    res_senior = gk.evaluate(company_name="FintechStartup", role_title="Senior Product Manager")
    assert not res_senior.passed
    assert "SENIORITY_OVERFLOW" in res_senior.flags

    # Funded startup must pass
    res_portkey = gk.evaluate(company_name="Portkey", role_title="Associate Product Manager")
    assert res_portkey.passed


def test_pillar_classification():
    classifier = PillarClassifier()

    # Pillar 1: Founder's Office
    p1 = classifier.classify(title="Founder's Office", stage="Seed")
    assert p1.pillar == StrategicPillar.FOUNDERS_OFFICE
    assert p1.suggested_ctc_band["quoted"] == 9.0

    # Pillar 2: Product Operations
    p2 = classifier.classify(title="Product Operations Manager", stage="Series A")
    assert p2.pillar == StrategicPillar.PRODUCT_OPERATIONS

    # Pillar 3: AI APM
    p3 = classifier.classify(title="Associate Product Manager", description="AI Systems", stage="Series A")
    assert p3.pillar == StrategicPillar.AI_APM
    assert p3.suggested_ctc_band["quoted"] == 12.5


def test_scoring_rubric():
    engine = StrategyScoringEngine()

    # Mumbai-based Seed startup with high pillar fit
    score_data, classification = engine.evaluate(
        company_name="Finvolv",
        role_title="Founder's Office",
        funding_stage="Pre-Series A",
        sector="Fintech",
        location="Mumbai",
        description="Lending workflows and verification"
    )

    assert score_data.qualified
    assert score_data.total_score >= 80
    assert score_data.funding_stage_score == 25
    assert score_data.location_score == 25  # Local Mumbai advantage


def test_proof_of_work_mapping():
    mapper = ProofOfWorkMapper()

    # Fintech domain
    fintech_builds = mapper.select_top_3_builds(sector="Fintech / Payments", pillar="AI_APM")
    ids = [b.id for b in fintech_builds]
    assert "payrouter" in ids
    assert "verishield" in ids

    # Logistics domain
    logistics_builds = mapper.select_top_3_builds(sector="Logistics / Quick Commerce", pillar="PRODUCT_OPERATIONS")
    ids = [b.id for b in logistics_builds]
    assert "crewrostering" in ids
    assert "flashqueue" in ids


def test_cv_templates_have_zero_em_dashes(tmp_path):
    gen = PillarCVGenerator(output_dir=tmp_path)

    for pillar, template in [
        ("PILLAR_1_FOUNDERS_OFFICE", "resume_pillar1_founders_office.html"),
        ("PILLAR_2_PRODUCT_OPERATIONS", "resume_pillar2_prod_ops.html"),
        ("PILLAR_3_AI_APM", "resume_pillar3_ai_apm.html")
    ]:
        html = gen.render_html(
            company_name="TestStartup",
            role_title="Product Manager",
            pillar=pillar,
            sector="Fintech"
        )
        assert "—" not in html, f"Em dash found in {template}"
        assert "--" not in html, f"Double dash found in {template}"
        assert "Manav Mate" in html
        assert "Bachelor of Commerce (B.Com)" in html


def test_outreach_sequence_constraints():
    crosschecker = WellfoundCrossChecker()
    seq_gen = SequenceGenerator()

    signal = FundingSignal(
        company_name="SuperOps",
        funding_stage="Series B",
        amount_raised="$12.4M",
        investors=["Matrix Partners"],
        sector="B2B SaaS / IT Ops",
        hq_location="Mumbai",
        founder_names=["Arvind Parthiban"],
        announcement_date="2026-01-15",
        source="YourStory",
        source_url="https://test.com"
    )
    opp = crosschecker.match_opportunity(signal)

    touchpoints = seq_gen.generate_touchpoints(
        opportunity=opp,
        pillar="PILLAR_2_PRODUCT_OPERATIONS",
        lead_investor="Matrix Partners"
    )

    # LinkedIn Connect Note length constraint
    assert len(touchpoints.linkedin_connect_note) <= 280, "LinkedIn Connect Note must be <= 280 characters"
    assert "—" not in touchpoints.linkedin_connect_note, "No em dashes allowed"
    assert "—" not in touchpoints.funding_hook_cold_dm, "No em dashes allowed"
    assert "NeoManpower" in touchpoints.funding_hook_cold_dm
    assert "HireFlo" in touchpoints.funding_hook_cold_dm


def test_telemetry_database(tmp_path):
    db_file = tmp_path / "test_telemetry.db"
    db = TelemetryDB(db_path=db_file)

    # Record signal
    sig_id = db.record_signal({
        "company_name": "TestAI",
        "funding_stage": "Seed",
        "amount_raised": "$2M",
        "sector": "AI",
        "hq_location": "Mumbai",
        "founder_names": ["Test Founder"],
        "source": "Inc42",
        "source_url": "https://test.com"
    })
    assert sig_id > 0

    # Record opportunity
    opp_id = db.record_opportunity(
        company_name="TestAI",
        role_title="Founder's Office",
        pillar="PILLAR_1_FOUNDERS_OFFICE",
        score=85,
        expected_ctc_quote="₹8.5L - ₹10L"
    )
    assert opp_id > 0

    # Log outreach
    log_id = db.log_outreach(
        company_name="TestAI",
        channel="linkedin_connect",
        touchpoint_type="connect_note",
        message_text="Hi test",
        opportunity_id=opp_id
    )
    assert log_id > 0

    # Check metrics
    summary = db.get_funnel_summary()
    assert summary["signals_captured"] == 1
    assert summary["opportunities_identified"] == 1
    assert summary["qualified_opportunities"] == 1
    assert summary["outreach_sent"] == 1

