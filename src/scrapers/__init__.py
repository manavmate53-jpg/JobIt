"""Scraper package exports and unified scraper manager."""

from __future__ import annotations

import logging
from typing import List
from src.scrapers.base_scraper import BaseScraper, ScrapedJob
from src.scrapers.filter_rules import check_negative_filters
from src.scrapers.linkedin_scraper import LinkedInScraper
from src.scrapers.naukri_scraper import NaukriScraper

logger = logging.getLogger(__name__)


def scrape_portals(portal: str = "all", keywords: str = "Product Manager", location: str = "Mumbai", limit: int = 20) -> List[ScrapedJob]:
    """Unified entrypoint to scrape jobs across LinkedIn, Naukri, or both."""
    scrapers: List[BaseScraper] = []
    p = portal.lower()
    
    if p in ("linkedin", "all"):
        scrapers.append(LinkedInScraper())
    if p in ("naukri", "all"):
        scrapers.append(NaukriScraper())

    results: List[ScrapedJob] = []
    per_scraper_limit = limit if len(scrapers) == 1 else (limit // 2 + 2)

    for scraper in scrapers:
        try:
            found = scraper.scrape(keywords=keywords, location=location, limit=per_scraper_limit)
            results.extend(found)
        except Exception as e:
            logger.error(f"Error executing scraper {scraper.__class__.__name__}: {e}")

    # Deduplicate by job_url
    deduped: List[ScrapedJob] = []
    seen_urls = set()
    for j in results:
        if j.job_url not in seen_urls:
            seen_urls.add(j.job_url)
            deduped.append(j)

    return deduped[:limit]
