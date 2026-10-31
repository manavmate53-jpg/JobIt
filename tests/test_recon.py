"""Unit & Schema Validation Tests for Engine YING (Reconnaissance)."""

import json
import os
import pytest
from core.enricher import ContactEnricher, normalize_domain
from engines.ying_recon import YingReconEngine


def test_domain_normalization():
    assert normalize_domain("Zepto Pvt Ltd") == "zepto.co"
    assert normalize_domain("Jupiter Money Technologies") == "jupitermoney.com"
    assert normalize_domain("PostHog Inc") == "posthog.com"
    assert normalize_domain("Cursor") == "anysphere.co"
    assert normalize_domain("Generic Brand Solutions") == "genericbrand.com"


def test_contact_refinery_enrichment():
    enricher = ContactEnricher(enable_live_smtp=False)
    lead = enricher.enrich_contact(
        full_name="Sarah Jenkins",
        company_name="Zepto",
        title="VP of Product",
        linkedin_url="https://www.linkedin.com/in/sarah-jenkins"
    )

    assert lead["name"] == "Sarah Jenkins"
    assert lead["domain"] == "zepto.co"
    assert lead["primary_email"] == "sarah.jenkins@zepto.co"
    assert "sarah@zepto.co" in lead["email_permutations"]
    assert lead["confidence_score"] >= 65
    assert lead["primary_channel"] == "linkedin_dm"


def test_ying_recon_dry_run_and_schema_validation(tmp_path):
    engine = YingReconEngine(dry_run=True)
    engine.reports_dir = str(tmp_path)

    artifact = engine.run(limit_per_company=2)

    # 1. Structure Verification
    assert "timestamp" in artifact
    assert "summary" in artifact
    assert "leads" in artifact
    assert "reverse_engineered_profiles" in artifact
    assert "active_posts" in artifact
    assert "teardown_vectors" in artifact

    # 2. Leads Integrity
    assert len(artifact["leads"]) > 0
    first_lead = artifact["leads"][0]
    assert "primary_email" in first_lead
    assert "mx_host" in first_lead

    # 3. Vector 1: Reverse-Engineered Profiles Integrity
    assert len(artifact["reverse_engineered_profiles"]) > 0
    first_hire = artifact["reverse_engineered_profiles"][0]
    assert "skills" in first_hire
    assert len(first_hire["skills"]) >= 3
    assert "tech_stack" in first_hire
    assert "project_architectures" in first_hire

    # 4. Vector 2: Active Posts Integrity
    assert len(artifact["active_posts"]) > 0
    first_post = artifact["active_posts"][0]
    assert "suggested_comment" in first_post
    assert len(first_post["suggested_comment"]) > 10

    # 5. Vector 3: Teardown Vector & Value-Drop Pitch
    assert len(artifact["teardown_vectors"]) > 0
    first_td = artifact["teardown_vectors"][0]
    assert "problem_area" in first_td
    assert "outreach_pitch" in first_td
    assert "subject" in first_td["outreach_pitch"]
    assert "body" in first_td["outreach_pitch"]

    # 6. Disk Persistence Verification
    json_file = os.path.join(str(tmp_path), "recon_latest.json")
    md_file = os.path.join(str(tmp_path), "recon_latest.md")
    assert os.path.exists(json_file)
    assert os.path.exists(md_file)

    with open(json_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
        assert loaded["cycle"] == "6_hour_recon"

