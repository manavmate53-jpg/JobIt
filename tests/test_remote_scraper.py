"""Tests for Remote Worldwide Job Scraper."""

from src.scrapers.remote_scraper import RemoteJobScraper, clean_html_text


def test_clean_html_text():
    raw = "<p>Product Manager needed at <strong>TechCorp</strong>.<br>Apply now!</p>"
    cleaned = clean_html_text(raw)
    assert cleaned == "Product Manager needed at TechCorp. Apply now!"


def test_remote_scraper_pm_match_rules():
    scraper = RemoteJobScraper()
    # Positive matches
    assert scraper._is_pm_match("Associate Product Manager", "Product Manager") is True
    assert scraper._is_pm_match("Junior Product Manager - AI", "Junior Product Manager") is True
    assert scraper._is_pm_match("Product Operations Lead", "Product Operations") is True
    assert scraper._is_pm_match("Technical Product Manager", "Technical Product Manager") is True
    
    # Negative matches
    assert scraper._is_pm_match("Key Account Manager Danish Market", "Product Manager") is False
    assert scraper._is_pm_match("Clinical Data Manager", "Product Manager") is False
    assert scraper._is_pm_match("Lead Product Designer", "Product Manager") is False
    assert scraper._is_pm_match("Rails Software Engineer", "Product Manager") is False


def test_remote_scraper_benchmark_fallback():
    scraper = RemoteJobScraper()
    jobs = scraper.scrape(keywords="Associate Product Manager", limit=5)
    assert len(jobs) > 0
    # Every job must have company, role, job_url, and location
    for j in jobs:
        assert j.company != ""
        assert j.role != ""
        assert j.job_url.startswith("http")
        assert "Remote" in j.location or "Worldwide" in j.location
