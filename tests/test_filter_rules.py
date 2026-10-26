import pytest
from src.scrapers.filter_rules import check_negative_filters


def test_physical_manufacturing_filter():
    is_valid, reason = check_negative_filters(
        title="Plant Operations Manager",
        company="Sleepwell",
        description="Oversee mattress and foam production shop floor"
    )
    assert not is_valid
    assert "manufacturing" in reason.lower()


def test_pharma_brand_marketing_filter():
    is_valid, reason = check_negative_filters(
        title="Brand Manager",
        company="Pharma India",
        description="Lead HCP marketing and clinical detailing with prescribing doctors"
    )
    assert not is_valid
    assert "pharmaceutical" in reason.lower()


def test_nbfc_vehicle_filter():
    is_valid, reason = check_negative_filters(
        title="Credit Manager",
        company="FinServe",
        description="Assess construction equipment loans and tractor loans"
    )
    assert not is_valid
    assert "offline vehicle" in reason.lower()


def test_senior_years_filter():
    is_valid, reason = check_negative_filters(
        title="Product Manager",
        company="Enterprise Corp",
        description="Requires minimum 7 years of product management experience"
    )
    assert not is_valid
    assert "experience" in reason.lower() or "5+" in reason.lower()


def test_valid_apm_role():
    is_valid, reason = check_negative_filters(
        title="Associate Product Manager",
        company="AI SaaS Lab",
        description="1-2 years experience, PRDs, user onboarding, and SQL queries",
        experience_text="1-2 Yrs"
    )
    assert is_valid
    assert reason is None
