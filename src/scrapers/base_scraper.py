"""Base scraper abstractions and ScrapedJob model."""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class ScrapedJob(BaseModel):
    company: str
    role: str
    job_url: str
    source: str
    location: str = "Mumbai"
    experience_years: str = ""
    salary: str = ""
    posting_date: str = ""
    raw_description: str = ""
    hr_name: Optional[str] = None
    hr_email: Optional[str] = None
    scraped_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())


class BaseScraper(ABC):
    """Abstract base scraper."""

    @abstractmethod
    def scrape(self, keywords: str, location: str = "Mumbai", limit: int = 20) -> List[ScrapedJob]:
        """Scrapes job postings matching keywords and location."""
        pass
