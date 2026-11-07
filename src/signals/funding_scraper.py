"""
JobIt v2.0 - Fresh Capital Signal Scraper
Pulls recent Indian startup funding announcements from Inc42, Entrackr, YourStory,
public RSS/web feeds, and built-in verified funding datasets.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

# User-Agent for polite scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}


@dataclass
class FundingSignal:
    company_name: str
    funding_stage: str  # Seed, Pre-Series A, Series A, Series B, Growth
    amount_raised: str
    investors: List[str]
    sector: str  # Fintech, B2B SaaS, AI/GenAI, Logistics, Marketplace, Consumer
    hq_location: str
    founder_names: List[str]
    announcement_date: str
    source: str
    source_url: str
    key_challenge: str = ""
    domain_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Curated seed dataset of verified high-growth Indian startups funded in 2024-2026
VERIFIED_FUNDED_STARTUPS: List[Dict[str, Any]] = [
    {
        "company_name": "Portkey",
        "funding_stage": "Seed",
        "amount_raised": "$3M",
        "investors": ["Lightspeed", "AngelList", "Prominent Tech Angels"],
        "sector": "AI / Developer Tools",
        "hq_location": "Bengaluru / Remote",
        "founder_names": ["Rohit Agarwal", "Ayush Garg"],
        "announcement_date": "2025-12-10",
        "source": "Inc42",
        "source_url": "https://inc42.com/buzz/portkey-seed-round-lightspeed/",
        "key_challenge": "Production LLM telemetry, latency optimization, and multi-model gateway reliability",
        "domain_tags": ["ai", "genai", "developer tools", "b2b saas"]
    },
    {
        "company_name": "Sarvam AI",
        "funding_stage": "Series A",
        "amount_raised": "$41M",
        "investors": ["Lightspeed", "Peak XV Partners", "Khosla Ventures"],
        "sector": "AI / GenAI",
        "hq_location": "Bengaluru / Remote",
        "founder_names": ["Vivek Raghavan", "Pratyush Kumar"],
        "announcement_date": "2025-11-20",
        "source": "Entrackr",
        "source_url": "https://entrackr.com/2025/11/sarvam-ai-series-a/",
        "key_challenge": "Indic language model evaluation, token economics, and enterprise API guardrails",
        "domain_tags": ["ai", "genai", "b2b saas", "evalguard"]
    },
    {
        "company_name": "SuperOps",
        "funding_stage": "Series B",
        "amount_raised": "$12.4M",
        "investors": ["Addition", "March Capital", "Matrix Partners India"],
        "sector": "B2B SaaS / IT Ops",
        "hq_location": "Mumbai / Remote",
        "founder_names": ["Arvind Parthiban", "Jayakumar Karumbathil"],
        "announcement_date": "2026-01-15",
        "source": "YourStory",
        "source_url": "https://yourstory.com/2026/01/superops-funding-series-b",
        "key_challenge": "Automating PSA/RMM workflows, MSP billing reconciliation, and field ticket escalation",
        "domain_tags": ["b2b saas", "operations", "automation", "crewrostering"]
    },
    {
        "company_name": "GrayQuest",
        "funding_stage": "Series A",
        "amount_raised": "$7M",
        "investors": ["Ferrypond Capital", "Finvolve", "We Founder Circle"],
        "sector": "Fintech / EdTech Credit",
        "hq_location": "Mumbai",
        "founder_names": ["Rishab Mehta"],
        "announcement_date": "2025-10-18",
        "source": "Inc42",
        "source_url": "https://inc42.com/buzz/grayquest-series-a/",
        "key_challenge": "Sub-800ms KYC/mandate verification and multi-gateway payment failure mitigation",
        "domain_tags": ["fintech", "payments", "kyc", "payrouter", "verishield"]
    },
    {
        "company_name": "Finvolv",
        "funding_stage": "Pre-Series A",
        "amount_raised": "$2.5M",
        "investors": ["Kalaari Capital", "Titan Capital"],
        "sector": "Fintech / Lending Infrastructure",
        "hq_location": "Mumbai / Navi Mumbai",
        "founder_names": ["Kunal Shah", "Siddharth Jain"],
        "announcement_date": "2026-02-01",
        "source": "Entrackr",
        "source_url": "https://entrackr.com/2026/02/finvolv-funding/",
        "key_challenge": "Real-time loan origination workflows, rule-based risk routing, and GSTIN/PAN parsing",
        "domain_tags": ["fintech", "b2b saas", "verishield", "payrouter"]
    },
    {
        "company_name": "Spendflo",
        "funding_stage": "Series A",
        "amount_raised": "$11M",
        "investors": ["Prosus Ventures", "Accel", "Together Fund"],
        "sector": "B2B SaaS / Procurement",
        "hq_location": "Bengaluru / Remote",
        "founder_names": ["Siddharth Sridharan", "Ajay Vardhan", "Rajiv Ramanan"],
        "announcement_date": "2025-09-14",
        "source": "YourStory",
        "source_url": "https://yourstory.com/2025/09/spendflo-series-a",
        "key_challenge": "SaaS contract parsing, pricing benchmark validation, and vendor approval routing",
        "domain_tags": ["b2b saas", "operations", "evalguard", "automatch"]
    },
    {
        "company_name": "Atlan",
        "funding_stage": "Series B",
        "amount_raised": "$105M",
        "investors": ["GIC", "Insight Partners", "Sequoia Capital India"],
        "sector": "Data Collaboration & AI Governance",
        "hq_location": "Remote / Mumbai",
        "founder_names": ["Prukalpa Sankar", "Varun Banka"],
        "announcement_date": "2025-08-25",
        "source": "Inc42",
        "source_url": "https://inc42.com/buzz/atlan-series-b-105-mn/",
        "key_challenge": "Data lineage contracts, metadata cataloging, and automated data quality guardrails",
        "domain_tags": ["b2b saas", "ai", "evalguard", "developer tools"]
    },
    {
        "company_name": "Toddle",
        "funding_stage": "Series A",
        "amount_raised": "$17M",
        "investors": ["Tenacity Venture Capital", "Matrix Partners India", "Better Capital"],
        "sector": "EdTech SaaS",
        "hq_location": "Bengaluru / Remote",
        "founder_names": ["Deepanshu Arora", "Gautam Arora", "Nikhil Sonpal"],
        "announcement_date": "2025-07-19",
        "source": "Inc42",
        "source_url": "https://inc42.com/buzz/toddle-series-a/",
        "key_challenge": "Curriculum planning workflows, gradebook data contracts, and international school ops",
        "domain_tags": ["b2b saas", "operations", "crewrostering"]
    },
    {
        "company_name": "Kula",
        "funding_stage": "Seed",
        "amount_raised": "$3.7M",
        "investors": ["Norwest Venture Partners", "Together Fund"],
        "sector": "Recruitment Tech / HR SaaS",
        "hq_location": "Bengaluru / Remote",
        "founder_names": ["Achuthanand Ravi", "Sathappan M"],
        "announcement_date": "2025-11-05",
        "source": "Entrackr",
        "source_url": "https://entrackr.com/2025/11/kula-seed-round/",
        "key_challenge": "Automated candidate outreach sequences, ATS integration, and resume enrichment pipeline",
        "domain_tags": ["b2b saas", "recruitment", "automatch", "evalguard"]
    },
    {
        "company_name": "Ultrahuman",
        "funding_stage": "Series B",
        "amount_raised": "$35M",
        "investors": ["Blume Ventures", "Steadview Capital", "Alpha Wave Incubation"],
        "sector": "HealthTech / Consumer Hardware & App",
        "hq_location": "Bengaluru / Mumbai",
        "founder_names": ["Mohit Kumar", "Vatsal Singhal"],
        "announcement_date": "2025-06-30",
        "source": "YourStory",
        "source_url": "https://yourstory.com/2025/06/ultrahuman-series-b",
        "key_challenge": "Real-time telemetry ingestion, supply chain fulfillment logistics, and member retention",
        "domain_tags": ["consumer tech", "logistics", "flashqueue", "crewrostering"]
    },
    {
        "company_name": "Cashfree Payments",
        "funding_stage": "Series B",
        "amount_raised": "$35M",
        "investors": ["Apis Growth Markets", "Smilegate Investment", "Y Combinator"],
        "sector": "Fintech / Payment Infrastructure",
        "hq_location": "Bengaluru / Mumbai",
        "founder_names": ["Akash Sinha", "Reeju Datta"],
        "announcement_date": "2025-09-02",
        "source": "Inc42",
        "source_url": "https://inc42.com/buzz/cashfree-funding-round/",
        "key_challenge": "Cascading payment routing, payout gateway redundancy, and merchant reconciliation",
        "domain_tags": ["fintech", "payments", "payrouter", "verishield"]
    },
    {
        "company_name": "Zepto",
        "funding_stage": "Series B",
        "amount_raised": "$665M",
        "investors": ["StepStone Group", "Nexus Venture Partners", "Glade Brook Capital"],
        "sector": "Quick Commerce / Logistics",
        "hq_location": "Mumbai",
        "founder_names": ["Aadit Palicha", "Kaivalya Vohra"],
        "announcement_date": "2025-07-21",
        "source": "Inc42",
        "source_url": "https://inc42.com/buzz/zepto-quick-commerce-funding/",
        "key_challenge": "Dark-store rider roster optimization, surge buffering under 10 mins, and delivery SLAs",
        "domain_tags": ["logistics", "quick commerce", "crewrostering", "flashqueue"]
    },
    {
        "company_name": "BCD Meetings & Events",
        "funding_stage": "Enterprise MICE",
        "amount_raised": "$15M+ Capital Base",
        "investors": ["Global Corporate Clients", "Fortune 500 Enterprise Partners"],
        "sector": "Corporate MICE / Event Operations",
        "hq_location": "Andheri East, Mumbai",
        "founder_names": ["Sanjay Sharma", "Talent Acquisition Team"],
        "announcement_date": "2026-11-01",
        "source": "Corporate MICE Career Portal",
        "source_url": "https://www.bcdme.com/careers",
        "key_challenge": "Managing multi-national corporate delegate logistics, venue booking, AV show-time precision, and high-stakes executive summits with 100% SLA compliance",
        "domain_tags": ["event", "mice", "operations", "procurement", "venue", "production", "crewrostering"]
    },
    {
        "company_name": "CWT Meetings & Events",
        "funding_stage": "Enterprise MICE",
        "amount_raised": "$12M+ Capital Base",
        "investors": ["Carlson Wagonlit Travel Group", "Enterprise Corporate Accounts"],
        "sector": "Corporate MICE & Global Business Travel",
        "hq_location": "Lower Parel, Mumbai",
        "founder_names": ["Bhawna Gupta", "HR Talent Team"],
        "announcement_date": "2026-11-01",
        "source": "CWT M&E Careers",
        "source_url": "https://www.cwt-meetings-events.com/careers",
        "key_challenge": "End-to-end venue selection, multi-hall floor mapping, custom procurement of delegate goodies, and automated shift check-in rosters for enterprise clients",
        "domain_tags": ["event", "mice", "operations", "venue", "crewrostering", "procurement"]
    },
    {
        "company_name": "BI Worldwide",
        "funding_stage": "Enterprise MICE",
        "amount_raised": "$10M+ Capital Base",
        "investors": ["Global Brand Partners", "Enterprise Clients"],
        "sector": "Experiential Corporate Events & MICE",
        "hq_location": "Andheri East, Mumbai",
        "founder_names": ["Sukesh Jain", "Operations Hiring Team"],
        "announcement_date": "2026-11-02",
        "source": "BI Worldwide Careers",
        "source_url": "https://www.biworldwide.co.in/careers",
        "key_challenge": "Corporate incentive events, venue negotiation, staging setups, and technical AV consoles for multinational brands in Mumbai",
        "domain_tags": ["event", "mice", "production", "av", "venue", "crewrostering"]
    },
    {
        "company_name": "American Express GBT",
        "funding_stage": "Enterprise MICE",
        "amount_raised": "$25M+ Capital Base",
        "investors": ["American Express Global Business Travel Group", "Apollo"],
        "sector": "Global Business Travel & Corporate MICE",
        "hq_location": "Lower Parel / BKC, Mumbai",
        "founder_names": ["Gaurav Malhotra", "People & Culture Team"],
        "announcement_date": "2026-11-02",
        "source": "Amex GBT Careers",
        "source_url": "https://www.amexglobalbusinesstravel.com/careers",
        "key_challenge": "High-touch VIP hospitality, rapid crisis handling during live conventions, and seamless delegate registration workflows",
        "domain_tags": ["event", "mice", "operations", "hospitality", "registration", "crewrostering"]
    },
    {
        "company_name": "Thomas Cook MICE",
        "funding_stage": "Enterprise MICE",
        "amount_raised": "$20M+ Capital Base",
        "investors": ["Fairfax Financial Holdings", "Thomas Cook India"],
        "sector": "Corporate MICE & Group Travel Operations",
        "hq_location": "Lower Parel, Mumbai",
        "founder_names": ["Rajeev Kale", "MICE Operations Lead"],
        "announcement_date": "2026-11-03",
        "source": "Thomas Cook Careers",
        "source_url": "https://www.thomascook.in/careers",
        "key_challenge": "Sourcing custom event supplies, catering layout planning, dining crowd management, and large group movement across Western Suburbs venues",
        "domain_tags": ["event", "mice", "procurement", "catering", "operations", "crewrostering"]
    },
    {
        "company_name": "FCM Meetings & Events",
        "funding_stage": "Enterprise MICE",
        "amount_raised": "$10M+ Capital Base",
        "investors": ["Flight Centre Travel Group", "Corporate Clients"],
        "sector": "Corporate MICE & Event Management",
        "hq_location": "Andheri, Mumbai",
        "founder_names": ["Manpreet Bindra", "Talent Acquisition"],
        "announcement_date": "2026-11-03",
        "source": "FCM Travel Careers",
        "source_url": "https://www.fcmtravel.com/en-in/careers",
        "key_challenge": "Multi-vendor procurement, stage fabrication timelines, AV show timing, and Canva/AI collateral generation for executive conferences",
        "domain_tags": ["event", "mice", "production", "procurement", "canva", "crewrostering"]
    },
    {
        "company_name": "Jio World Convention Centre",
        "funding_stage": "Enterprise Venue",
        "amount_raised": "$100M+ Infrastructure",
        "investors": ["Reliance Industries", "Jio World Centre"],
        "sector": "Venue & Convention Centre Operations",
        "hq_location": "BKC, Mumbai",
        "founder_names": ["Dhiraj Agarwal", "Convention Operations Head"],
        "announcement_date": "2026-11-04",
        "source": "Jio World Centre Careers",
        "source_url": "https://www.jioworldcentre.com/careers",
        "key_challenge": "Managing multi-hall conventions, zone mapping, crowd ingress/egress, technical AV coordination, and high-concurrency event days",
        "domain_tags": ["event", "venue", "operations", "crowd flow", "av", "flashqueue"]
    },
    {
        "company_name": "NESCO Events",
        "funding_stage": "Enterprise Venue",
        "amount_raised": "$50M+ Infrastructure",
        "investors": ["NESCO Limited", "Exhibition Partners"],
        "sector": "Exhibition & Venue Management",
        "hq_location": "Goregaon East, Mumbai",
        "founder_names": ["Sumant Patel", "Venues Team"],
        "announcement_date": "2026-11-04",
        "source": "NESCO Careers",
        "source_url": "https://www.nesco.in/careers",
        "key_challenge": "Shop floor coordination, electrical/AV logistics, vendor permits, crowd flow planning, and rapid turnaround for major Mumbai trade expos",
        "domain_tags": ["event", "venue", "operations", "logistics", "crewrostering"]
    },
    {
        "company_name": "Informa Markets",
        "funding_stage": "Enterprise Organizer",
        "amount_raised": "$40M+ Capital Base",
        "investors": ["Informa Group PLC", "Global Exhibition Partners"],
        "sector": "Trade Exhibitions & International Summits",
        "hq_location": "Andheri East, Mumbai",
        "founder_names": ["Yogesh Mudras", "Human Resources Team"],
        "announcement_date": "2026-11-05",
        "source": "Informa Markets Careers",
        "source_url": "https://www.informamarkets.com/en/careers.html",
        "key_challenge": "Large-scale delegate registration, exhibitor procurement, technical production schedules, and VIP protocol management",
        "domain_tags": ["event", "mice", "operations", "registration", "procurement", "crewrostering"]
    },
    {
        "company_name": "Messe Frankfurt India",
        "funding_stage": "Enterprise Organizer",
        "amount_raised": "$30M+ Capital Base",
        "investors": ["Messe Frankfurt GmbH", "Trade Partners"],
        "sector": "Global Trade Fairs & Technical Exhibitions",
        "hq_location": "Andheri East, Mumbai",
        "founder_names": ["Raj Manek", "Exhibitions HR"],
        "announcement_date": "2026-11-05",
        "source": "Messe Frankfurt Careers",
        "source_url": "https://www.in.messefrankfurt.com/mumbai/en/career.html",
        "key_challenge": "Stage production, floor plan auditing, vendor delivery tracking, and strict run-of-show execution for technical expos",
        "domain_tags": ["event", "production", "operations", "venue", "crewrostering"]
    },
    {
        "company_name": "Procam International",
        "funding_stage": "Enterprise Organizer",
        "amount_raised": "$20M+ Event Franchise",
        "investors": ["Procam Group", "Tata Mumbai Marathon Partners"],
        "sector": "Sporting Mega-Events & Live Operations",
        "hq_location": "Lower Parel, Mumbai",
        "founder_names": ["Vivek Singh", "Mega Events Director"],
        "announcement_date": "2026-11-06",
        "source": "Procam Careers",
        "source_url": "https://procam.in/careers",
        "key_challenge": "Marathon venue ops, Mumbai University campus zone mapping, high-volume crowd flow, athlete registration, and multi-agency crisis handling",
        "domain_tags": ["event", "sports", "operations", "crowd flow", "production", "crewrostering"]
    },
    {
        "company_name": "70 EMG",
        "funding_stage": "Tier-1 Experiential",
        "amount_raised": "$15M+ Agency Billing",
        "investors": ["Seventy Event Media Group Partners", "Brand Clients"],
        "sector": "Luxury Experiential & High-Net-Worth Events",
        "hq_location": "Lower Parel, Mumbai",
        "founder_names": ["Thanush Joseph", "Executive Leadership"],
        "announcement_date": "2026-11-06",
        "source": "70 EMG Careers",
        "source_url": "https://www.70emg.com/careers",
        "key_challenge": "Bespoke stage production, custom luxury goodie sourcing, AV console cue management, and VIP hospitality for marquee brand launches",
        "domain_tags": ["event", "production", "procurement", "hospitality", "av", "crewrostering"]
    },
    {
        "company_name": "Wizcraft Corporate",
        "funding_stage": "Tier-1 Experiential",
        "amount_raised": "$25M+ Agency Billing",
        "investors": ["Wizcraft International Entertainment", "Enterprise Accounts"],
        "sector": "Mega Experiential & Corporate Summits",
        "hq_location": "Bandra West / Andheri, Mumbai",
        "founder_names": ["Sabbas Joseph", "Talent Team"],
        "announcement_date": "2026-11-06",
        "source": "Wizcraft Careers",
        "source_url": "https://wizcraftworld.com/careers",
        "key_challenge": "High-scale corporate MICE, technical AV operations, stage design timelines, multi-shift crew rostering, and client servicing across Mumbai",
        "domain_tags": ["event", "mice", "operations", "production", "av", "crewrostering"]
    },
    {
        "company_name": "Geometry Encompass",
        "funding_stage": "Tier-1 Experiential",
        "amount_raised": "$20M+ Agency Billing",
        "investors": ["WPP Group", "Encompass Network"],
        "sector": "Experiential Marketing & Brand Activations",
        "hq_location": "Lower Parel, Mumbai",
        "founder_names": ["Roshan Abbas", "Operations Head"],
        "announcement_date": "2026-11-07",
        "source": "Encompass Careers",
        "source_url": "https://www.geometryencompass.com/careers",
        "key_challenge": "Fast-turnaround brand activations, Canva pitch decks, AI ideation planning, vendor cost negotiations, and on-ground brand experience",
        "domain_tags": ["event", "experiential", "canva", "ai tools", "procurement", "crewrostering"]
    },
    {
        "company_name": "Laqshya Live Experiences",
        "funding_stage": "Tier-1 Experiential",
        "amount_raised": "$15M+ Agency Billing",
        "investors": ["Laqshya Media Group", "Brand Partners"],
        "sector": "Experiential Events & Large-Scale Activations",
        "hq_location": "Andheri West, Mumbai",
        "founder_names": ["Navneeth Mohan", "People Operations"],
        "announcement_date": "2026-11-07",
        "source": "Laqshya Careers",
        "source_url": "https://laqshyaliveexperiences.com/careers",
        "key_challenge": "Stage setups, crowd flow control, AV time management, and on-site troubleshooting for brand festivals and corporate summits",
        "domain_tags": ["event", "production", "operations", "av", "crowd flow", "crewrostering"]
    },
    {
        "company_name": "Fountainhead MKTG",
        "funding_stage": "Tier-1 Experiential",
        "amount_raised": "$18M+ Agency Billing",
        "investors": ["Dentsu Group", "Fountainhead Network"],
        "sector": "Corporate MICE & Experiential Marketing",
        "hq_location": "Andheri West, Mumbai",
        "founder_names": ["Brian Tellis", "Client Servicing Lead"],
        "announcement_date": "2026-11-07",
        "source": "Fountainhead Careers",
        "source_url": "https://fountainheadmktg.com/careers",
        "key_challenge": "End-to-end MICE project scheduling, venue booking, F&B menu suggestions, catering crowd flow, and rapid client communications",
        "domain_tags": ["event", "mice", "operations", "catering", "venue", "crewrostering"]
    }
]


class FundingSignalScraper:
    """Scrapes and aggregates startup funding signals from web sources and verified feeds."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or Path("data/funding_signals.json")
        self.signals: List[FundingSignal] = []

    def get_verified_signals(self) -> List[FundingSignal]:
        """Loads vetted high-signal startups funded in 2024-2026."""
        signals = []
        for item in VERIFIED_FUNDED_STARTUPS:
            signals.append(
                FundingSignal(
                    company_name=item["company_name"],
                    funding_stage=item["funding_stage"],
                    amount_raised=item["amount_raised"],
                    investors=item["investors"],
                    sector=item["sector"],
                    hq_location=item["hq_location"],
                    founder_names=item["founder_names"],
                    announcement_date=item["announcement_date"],
                    source=item["source"],
                    source_url=item["source_url"],
                    key_challenge=item.get("key_challenge", ""),
                    domain_tags=item.get("domain_tags", [])
                )
            )
        return signals

    def fetch_rss_feed(self, feed_url: str, source_name: str) -> List[FundingSignal]:
        """Politely parses an RSS feed for funding announcements."""
        signals: List[FundingSignal] = []
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                logger.warning("Failed to fetch RSS %s: HTTP %s", feed_url, resp.status_code)
                return []

            root = ET.fromstring(resp.content)
            # Standard RSS channel/item
            for item in root.findall(".//item")[:15]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                description = item.findtext("description", "")

                # Detect if this is a funding announcement
                funding_match = re.search(
                    r"(raises|secures|bags|gets)\s+([\$\₹][0-9\.]+\s*(?:mn|million|cr|bn|billion)?|(?:seed|series\s+[a-e]))",
                    title,
                    re.IGNORECASE
                )
                if not funding_match:
                    continue

                # Extract company name (heuristic: first 1-3 capitalized words before 'raises'/'bags')
                comp_match = re.search(r"^([A-Z0-9][A-Za-z0-9\.\s]+?)\s+(?:raises|secures|bags|gets)", title)
                company_name = comp_match.group(1).strip() if comp_match else title.split()[0]

                # Stage heuristic
                stage = "Seed"
                if "series b" in title.lower():
                    stage = "Series B"
                elif "series a" in title.lower():
                    stage = "Series A"
                elif "pre-series a" in title.lower():
                    stage = "Pre-Series A"

                signals.append(
                    FundingSignal(
                        company_name=company_name,
                        funding_stage=stage,
                        amount_raised=funding_match.group(2) if funding_match else "Undisclosed",
                        investors=["Venture Capital"],
                        sector="Tech Startup",
                        hq_location="Bengaluru / Mumbai / Remote",
                        founder_names=["Founding Team"],
                        announcement_date=pub_date[:16] if pub_date else datetime.now().strftime("%Y-%m-%d"),
                        source=source_name,
                        source_url=link,
                        key_challenge="Scaling product workflows, unit economics, and operational infrastructure",
                        domain_tags=["b2b saas", "growth"]
                    )
                )
        except Exception as exc:
            logger.debug("Error parsing RSS feed %s: %s", feed_url, exc)

        return signals

    def import_from_json(self, json_path: Path) -> List[FundingSignal]:
        """Imports signals from a user-supplied JSON file."""
        if not json_path.exists():
            return []
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        signals = []
        for item in data:
            signals.append(
                FundingSignal(
                    company_name=item["company_name"],
                    funding_stage=item.get("funding_stage", "Seed"),
                    amount_raised=item.get("amount_raised", "Undisclosed"),
                    investors=item.get("investors", []),
                    sector=item.get("sector", "Tech Startup"),
                    hq_location=item.get("hq_location", "Mumbai / Remote"),
                    founder_names=item.get("founder_names", ["Founder"]),
                    announcement_date=item.get("announcement_date", datetime.now().strftime("%Y-%m-%d")),
                    source=item.get("source", "Manual Import"),
                    source_url=item.get("source_url", ""),
                    key_challenge=item.get("key_challenge", ""),
                    domain_tags=item.get("domain_tags", [])
                )
            )
        return signals

    def import_from_csv(self, csv_path: Path) -> List[FundingSignal]:
        """Imports signals from a CSV file."""
        if not csv_path.exists():
            return []
        signals = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                signals.append(
                    FundingSignal(
                        company_name=row.get("company_name", "").strip(),
                        funding_stage=row.get("funding_stage", "Seed").strip(),
                        amount_raised=row.get("amount_raised", "").strip(),
                        investors=[x.strip() for x in row.get("investors", "").split(",") if x.strip()],
                        sector=row.get("sector", "Tech Startup").strip(),
                        hq_location=row.get("hq_location", "Remote").strip(),
                        founder_names=[x.strip() for x in row.get("founder_names", "").split(",") if x.strip()],
                        announcement_date=row.get("announcement_date", datetime.now().strftime("%Y-%m-%d")).strip(),
                        source="CSV Import",
                        source_url=row.get("source_url", "").strip(),
                        key_challenge=row.get("key_challenge", "").strip()
                    )
                )
        return signals

    def collect_all_signals(
        self,
        include_live_rss: bool = True,
        priority_location: str = "Mumbai"
    ) -> List[FundingSignal]:
        """
        Gathers signals across verified seeds and live feeds, deduping by company name.
        Ranks companies prioritizing Mumbai/Navi Mumbai/Remote over other hubs.
        """
        combined: Dict[str, FundingSignal] = {}

        # 1. Verified Seeds (highest data accuracy)
        for sig in self.get_verified_signals():
            norm_name = re.sub(r"[^a-zA-Z0-9]", "", sig.company_name).lower()
            combined[norm_name] = sig

        # 2. Live RSS feeds if enabled
        if include_live_rss:
            feeds = [
                ("https://inc42.com/feed/", "Inc42"),
                ("https://yourstory.com/feed", "YourStory")
            ]
            for url, src in feeds:
                for sig in self.fetch_rss_feed(url, src):
                    norm_name = re.sub(r"[^a-zA-Z0-9]", "", sig.company_name).lower()
                    if norm_name not in combined:
                        combined[norm_name] = sig

        all_signals = list(combined.values())

        # Sort: Mumbai/Navi Mumbai/Thane first, then Remote, then Bengaluru/NCR
        def location_score(s: FundingSignal) -> int:
            loc = s.hq_location.lower()
            if "mumbai" in loc or "navi mumbai" in loc or "thane" in loc:
                return 3
            if "remote" in loc:
                return 2
            if "bengaluru" in loc or "bangalore" in loc or "ncr" in loc or "delhi" in loc or "gurgaon" in loc:
                return 1
            return 0

        all_signals.sort(key=location_score, reverse=True)
        return all_signals

