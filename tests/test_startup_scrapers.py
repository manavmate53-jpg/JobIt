import pytest
from src.scrapers import scrape_portals
from src.scrapers.startup_scraper import (
    WeWorkRemotelyScraper,
    WellfoundScraper,
    CutshortScraper,
    InstahyreScraper,
    LevelsFyiScraper,
    ArcDevScraper,
    IndeedScraper,
)


def test_startup_scrapers_instantiation_and_scraping():
    wf = WellfoundScraper()
    wf_jobs = wf.scrape(keywords="Product Manager", location="Mumbai", limit=5)
    assert len(wf_jobs) > 0
    assert any("Korbit" in j.company or "InVideo" in j.company or "Dukaan" in j.company for j in wf_jobs)
    # Ensure no synthetic HR emails that cause bounces
    for j in wf_jobs:
        assert j.hr_email is None

    cs = CutshortScraper()
    cs_jobs = cs.scrape(keywords="Product Manager", location="Mumbai", limit=5)
    assert len(cs_jobs) > 0
    assert any("Landeed" in j.company or "Gupshup" in j.company for j in cs_jobs)
    for j in cs_jobs:
        assert j.hr_email is None

    ih = InstahyreScraper()
    ih_jobs = ih.scrape(keywords="Product", location="Mumbai", limit=5)
    assert len(ih_jobs) > 0
    assert any("CRED" in j.company or "Jupiter" in j.company for j in ih_jobs)
    for j in ih_jobs:
        assert j.hr_email is None

    lvl = LevelsFyiScraper()
    lvl_jobs = lvl.scrape(keywords="Product", location="Remote", limit=5)
    assert len(lvl_jobs) > 0
    assert any("Atlassian" in j.company or "Stripe" in j.company for j in lvl_jobs)

    arc = ArcDevScraper()
    arc_jobs = arc.scrape(keywords="Product", location="Remote", limit=5)
    assert len(arc_jobs) > 0
    assert any("Cursor" in j.company for j in arc_jobs)

    ind = IndeedScraper()
    ind_jobs = ind.scrape(keywords="Coordinator", location="Mumbai", limit=5)
    assert len(ind_jobs) > 0
    assert any("TCS" in j.company or "L&T" in j.company for j in ind_jobs)


def test_scrape_portals_unified_startup_integration():
    wellfound_jobs = scrape_portals(portal="wellfound", keywords="Product", location="Mumbai", limit=5)
    assert len(wellfound_jobs) > 0
    assert all(j.source == "Wellfound" for j in wellfound_jobs)

    cutshort_jobs = scrape_portals(portal="cutshort", keywords="Product", location="Mumbai", limit=5)
    assert len(cutshort_jobs) > 0
    assert all(j.source == "Cutshort" for j in cutshort_jobs)

    instahyre_jobs = scrape_portals(portal="instahyre", keywords="Product", location="Mumbai", limit=5)
    assert len(instahyre_jobs) > 0
    assert all(j.source == "Instahyre" for j in instahyre_jobs)

    startups_all = scrape_portals(portal="startups", keywords="Product", location="Mumbai", limit=15)
    assert len(startups_all) >= 3
