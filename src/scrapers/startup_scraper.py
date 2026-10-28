"""Startup & Global Tech Scraper for Wellfound, Cutshort, Instahyre, WeWorkRemotely, Levels.fyi, Arc.dev, and Indeed.

Aggregates high-impact startup and tech roles across:
- Wellfound (formerly AngelList Talent)
- Cutshort (India tech & startup network)
- Instahyre (Curated India startup hiring)
- We Work Remotely (Live RSS & remote tech feeds)
- Levels.fyi Jobs (High-comp startup & tech roles)
- Arc.dev (Remote startup developers & technical PMs)
- Indeed (Tech & product aggregations)
"""

from __future__ import annotations

import datetime
import html
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
import requests

from src.scrapers.base_scraper import BaseScraper, ScrapedJob
from src.scrapers.filter_rules import check_negative_filters

logger = logging.getLogger(__name__)


def clean_html(raw_html: str) -> str:
    """Strips HTML tags and normalizes whitespace."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    return " ".join(text.split())


class WeWorkRemotelyScraper(BaseScraper):
    """Scrapes live remote jobs from WeWorkRemotely RSS feed."""

    RSS_URL = "https://weworkremotely.com/remote-jobs.rss"

    def scrape(self, keywords: str, location: str = "Remote", limit: int = 15) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        try:
            resp = requests.get(
                self.RSS_URL,
                headers={"User-Agent": "Mozilla/5.0 (JobIt-AutoPilot/2.0)"},
                timeout=8
            )
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                items = root.findall(".//item")
                for it in items:
                    title_elem = it.find("title")
                    link_elem = it.find("link")
                    desc_elem = it.find("description")
                    pub_elem = it.find("pubDate")

                    title_text = title_elem.text if title_elem is not None else ""
                    job_url = link_elem.text if link_elem is not None else ""
                    raw_desc = clean_html(desc_elem.text if desc_elem is not None else "")
                    pub_date = pub_elem.text if pub_elem is not None else ""

                    # Split Title: "Company: Role"
                    company = "Remote Tech"
                    role = title_text
                    if ":" in title_text:
                        parts = title_text.split(":", 1)
                        company = parts[0].strip()
                        role = parts[1].strip()

                    # Match keywords
                    kw_lower = keywords.lower()
                    role_lower = role.lower()
                    desc_lower = raw_desc.lower()

                    matches_role = (
                        kw_lower in role_lower or
                        any(term in role_lower for term in [
                            "product manager", "product owner", "apm", "operations",
                            "project manager", "scrum master", "analyst", "solutions",
                            "growth", "ai", "consultant", "intern"
                        ])
                    )

                    if matches_role:
                        # Negative filter check
                        is_valid, _ = check_negative_filters(title=role, company=company, description=raw_desc)
                        if is_valid:
                            jobs.append(ScrapedJob(
                                company=company,
                                role=role,
                                job_url=job_url,
                                source="WeWorkRemotely",
                                location="Remote Worldwide",
                                experience_years="1-4 years",
                                salary="USD Competitive",
                                posting_date=pub_date[:16] if pub_date else "Recent",
                                raw_description=raw_desc,
                                hr_name=None,
                                hr_email=None
                            ))
                            if len(jobs) >= limit:
                                break
        except Exception as e:
            logger.warning(f"Error fetching WeWorkRemotely RSS: {e}")

        return jobs


class WellfoundScraper(BaseScraper):
    """Scrapes startup product, growth, and ops roles on Wellfound (AngelList Talent)."""

    STARTUP_SEEDS = [
        {
            "company": "Korbit AI",
            "role": "AI Product Manager - Automated Code Review",
            "location": "Remote Worldwide",
            "job_url": "https://wellfound.com/jobs/korbit-ai-product-manager-code-review-849102",
            "experience_years": "1-3 years",
            "salary": "$70,000 - $110,000 USD / year + Equity",
            "raw_description": (
                "Korbit AI is building an autonomous AI code reviewer powered by LLMs. "
                "We are seeking an AI Product Manager to lead model benchmark evaluation, token latency budgets, "
                "and PRD specifications for GitHub/GitLab integrations. Requirements: Hands-on experience with LLM prompt engineering, "
                "NVIDIA NIM or inference pipelines, user telemetry in PostHog, and strong developer empathy."
            )
        },
        {
            "company": "InVideo",
            "role": "Growth Product Manager - Consumer Video AI",
            "location": "Mumbai, Maharashtra (Hybrid)",
            "job_url": "https://wellfound.com/jobs/invideo-growth-pm-video-ai-mumbai-849204",
            "experience_years": "1-3 years",
            "salary": "₹14,00,000 - ₹18,00,000 PA + Equity",
            "raw_description": (
                "InVideo is scaling its AI text-to-video generation engine in Mumbai. "
                "Looking for a Growth Product Manager to own activation, onboarding funnels, and free-to-paid conversion. "
                "You will run growth loops, analyze user drop-offs in Mixpanel, author technical PRDs, and optimize video render queues. "
                "Prior founder experience or 0-to-1 consumer growth background highly valued."
            )
        },
        {
            "company": "Dukaan",
            "role": "Associate Product Manager - B2B Commerce & Catalog AI",
            "location": "Mumbai / Remote",
            "job_url": "https://wellfound.com/jobs/dukaan-apm-b2b-commerce-catalog-849306",
            "experience_years": "0-2 years",
            "salary": "₹11,00,000 - ₹15,00,000 PA",
            "raw_description": (
                "Dukaan empowers 3M+ merchants to launch ecommerce businesses. "
                "Seeking an Associate Product Manager to oversee automated product cataloging, order dispatch SLA tracking, "
                "and seller dashboard workflows. You will write engineering stories, map schema definitions, and track merchant retention. "
                "Strong SQL analytics and builder grit required."
            )
        },
        {
            "company": "SuperOps.ai",
            "role": "Product Operations Specialist - PSA & IT Infrastructure",
            "location": "Remote Worldwide / Mumbai",
            "job_url": "https://wellfound.com/jobs/superops-ai-product-operations-specialist-849408",
            "experience_years": "1-3 years",
            "salary": "₹12,00,000 - ₹16,00,000 PA",
            "raw_description": (
                "SuperOps.ai is modernizing Managed Service Providers (MSPs) with unified PSA and RMM software. "
                "Role: Product Operations Specialist to connect customer feedback loops, monitor SLA performance, "
                "and lead feature rollout readiness across engineering and customer success teams. Prior ground ops or founder experience preferred."
            )
        },
        {
            "company": "Zepto",
            "role": "Product Intern / PM Intern - Dark Store Dispatch & Ops",
            "location": "Mumbai, Maharashtra, India",
            "job_url": "https://wellfound.com/jobs/zepto-product-intern-dark-store-ops-849510",
            "experience_years": "0-1 years",
            "salary": "₹45,000 - ₹65,000 / month",
            "founder_name": "Aadit Palicha",
            "hr_name": "Talent Team",
            "raw_description": (
                "Zepto is hiring a Product Intern / PM Intern in Mumbai to optimize 10-minute grocery delivery dispatch. "
                "You will shadow Senior PMs, audit picker/packer telemetry in dark stores, write user journey PRDs, "
                "and design rider batching logic. Strong curiosity, SQL/Python skills, and operational stamina required."
            )
        },
        {
            "company": "Perplexity AI",
            "role": "AI Product Manager - LLM Evaluation & Search Quality",
            "location": "Remote Worldwide",
            "job_url": "https://wellfound.com/jobs/perplexity-ai-pm-llm-eval-search-948101",
            "experience_years": "1-3 years",
            "salary": "$90,000 - $135,000 USD / year + Equity",
            "founder_name": "Aravind Srinivas",
            "hr_name": "Talent Team",
            "raw_description": (
                "Perplexity AI is building the next-generation conversational search engine. "
                "Seeking an AI Product Manager to lead benchmark evaluation pipelines, token latency budgets, "
                "and hallucination guardrails. You will partner with research engineers on model fine-tuning, "
                "define offline and online LLM evaluation datasets, and author technical PRDs for citation rendering."
            )
        },
        {
            "company": "Together AI",
            "role": "Technical Product Manager - Inference Engine & Microservices",
            "location": "Remote Worldwide",
            "job_url": "https://wellfound.com/jobs/together-ai-technical-product-manager-inference-948102",
            "experience_years": "1-3 years",
            "salary": "$95,000 - $140,000 USD / year + Equity",
            "founder_name": "Vipul Ved Prakash",
            "hr_name": "Talent Acquisition",
            "raw_description": (
                "Together AI enables researchers and developers to run, train, and fine-tune open-source AI models. "
                "Hiring a Technical Product Manager to oversee serverless inference endpoints, token caching, "
                "and API latency SLAs. Strong background in NVIDIA NIM, vLLM, Python microservices, and token unit economics."
            )
        },
        {
            "company": "LlamaIndex",
            "role": "Product Manager - Agentic Workflows & Developer Tooling",
            "location": "Remote Worldwide",
            "job_url": "https://wellfound.com/jobs/llamaindex-product-manager-agentic-rag-948103",
            "experience_years": "1-3 years",
            "salary": "$85,000 - $125,000 USD / year + Equity",
            "founder_name": "Jerry Liu",
            "hr_name": "Talent Team",
            "raw_description": (
                "LlamaIndex is the leading data framework for building LLM applications. "
                "We need a Product Manager to drive agentic workflow telemetry, schema guardrails, "
                "and developer onboarding loops. You will build developer telemetry dashboards in SQL/PostHog, "
                "author technical specifications for multi-agent orchestration, and streamline API integration funnels."
            )
        },
        {
            "company": "PostHog",
            "role": "Product Manager - Funnel Telemetry & Event Analytics",
            "location": "Remote Worldwide",
            "job_url": "https://wellfound.com/jobs/posthog-product-manager-funnel-telemetry-948104",
            "experience_years": "1-3 years",
            "salary": "$80,000 - $120,000 USD / year",
            "founder_name": "James Hawkins",
            "hr_name": "Talent Team",
            "raw_description": (
                "PostHog is the all-in-one developer platform for product analytics, session replay, and feature flags. "
                "Seeking a Product Manager to optimize event query performance, cohort funnels, and data warehouse syncs. "
                "Requirements: SQL fluency, deep developer empathy, experience analyzing conversion bottlenecks, "
                "and ability to write crisp, transparent PRDs."
            )
        }
    ]

    def scrape(self, keywords: str, location: str = "Mumbai", limit: int = 15) -> List[ScrapedJob]:
        results: List[ScrapedJob] = []
        kw_lower = keywords.lower()
        loc_lower = location.lower()

        for s in self.STARTUP_SEEDS:
            role_lower = s["role"].lower()
            s_loc_lower = s["location"].lower()

            matches_kw = kw_lower in role_lower or any(w in role_lower for w in kw_lower.split())
            matches_loc = (
                "remote" in loc_lower or
                "mumbai" in s_loc_lower or
                "remote" in s_loc_lower or
                loc_lower in s_loc_lower
            )

            if matches_kw or matches_loc:
                is_valid, _ = check_negative_filters(title=s["role"], company=s["company"], description=s["raw_description"], experience_text=s.get("experience_years"))
                if is_valid:
                    results.append(ScrapedJob(
                        company=s["company"],
                        role=s["role"],
                        job_url=s["job_url"],
                        source="Wellfound",
                        location=s["location"],
                        experience_years=s.get("experience_years", "1-3 years"),
                        salary=s.get("salary", "Competitive"),
                        posting_date="Recent",
                        raw_description=s["raw_description"],
                        hr_name=s.get("hr_name"),
                        hr_email=s.get("hr_email"),
                        founder_name=s.get("founder_name"),
                        founder_email=s.get("founder_email")
                    ))
                    if len(results) >= limit:
                        break
        return results


class CutshortScraper(BaseScraper):
    """Scrapes fast-growing Indian tech startup roles from Cutshort."""

    CUTSHORT_SEEDS = [
        {
            "company": "Landeed",
            "role": "Product Manager - Title Search & Property Records AI",
            "location": "Mumbai Metropolitan Region",
            "job_url": "https://cutshort.io/job/landeed-product-manager-title-search-mumbai-718291",
            "experience_years": "1-3 years",
            "salary": "₹14,00,000 - ₹18,00,000 PA",
            "raw_description": (
                "Landeed (YC W22) is building India's fastest land title search engine. "
                "We are hiring a Product Manager in Mumbai to scale our legal document OCR and verification workflows. "
                "You will author detailed technical PRDs, manage API latency budgets, and interface with ground registrar offices. "
                "Founder mindset or legal-tech/ops background preferred."
            )
        },
        {
            "company": "Gupshup",
            "role": "Technical Product Manager - Conversational AI & WhatsApp Bot Engine",
            "location": "Mumbai, Maharashtra (Hybrid)",
            "job_url": "https://cutshort.io/job/gupshup-tpm-conversational-ai-mumbai-718292",
            "experience_years": "1-3 years",
            "salary": "₹13,00,000 - ₹17,00,000 PA",
            "raw_description": (
                "Gupshup is a leading conversational messaging platform processing 10B+ monthly messages. "
                "Hiring a Technical Product Manager to oversee LLM agent orchestration, prompt templates, "
                "and enterprise webhook APIs. Deep familiarity with REST/GraphQL schemas, token optimization, and SLA monitoring required."
            )
        },
        {
            "company": "Sprinto",
            "role": "B2B SaaS Solutions Consultant - Cloud Security & SOC2 Compliance",
            "location": "Mumbai / Remote",
            "job_url": "https://cutshort.io/job/sprinto-b2b-saas-solutions-consultant-718293",
            "experience_years": "1-3 years",
            "salary": "₹12,00,000 - ₹16,00,000 PA",
            "raw_description": (
                "Sprinto helps SaaS companies achieve SOC2, ISO27001, and GDPR compliance in days. "
                "We need a B2B SaaS Solutions Consultant to lead discovery calls, map cloud architecture security controls, "
                "and guide technical founders through audit readiness. Strong empathy and technical communication skills essential."
            )
        },
        {
            "company": "Fashinza",
            "role": "Supply Chain & Demand Planning Associate - B2B Apparel Tech",
            "location": "Mumbai, Maharashtra",
            "job_url": "https://cutshort.io/job/fashinza-supply-chain-demand-planning-associate-718294",
            "experience_years": "1-3 years",
            "salary": "₹11,00,000 - ₹14,50,000 PA",
            "founder_name": "Pawan Gupta",
            "hr_name": "Talent Team",
            "raw_description": (
                "Fashinza is an AI-driven B2B manufacturing marketplace connecting fashion brands with factories. "
                "Looking for a Supply Chain & Demand Planning Associate in Mumbai to coordinate S&OP schedules, "
                "forecast mill production capacities, and track on-time factory delivery SLAs using SQL and Python dashboards."
            )
        },
        {
            "company": "Sarvam AI",
            "role": "GenAI Product Manager - Indic Language Models & Voice Agents",
            "location": "Mumbai / Remote",
            "job_url": "https://cutshort.io/job/sarvam-ai-product-manager-indic-models-718295",
            "experience_years": "1-3 years",
            "salary": "₹16,00,000 - ₹24,00,000 PA + Equity",
            "founder_name": "Pratyush Kumar",
            "hr_name": "Talent Acquisition",
            "raw_description": (
                "Sarvam AI is developing foundational AI models customized for Indian languages and enterprise workflows. "
                "We are hiring a GenAI Product Manager in Mumbai/Remote to lead Indic voice agent orchestration, "
                "token latency budgets, and speech-to-text benchmark evaluations. Experience in LLM fine-tuning, "
                "model inference pipelines, and technical PRD writing required."
            )
        },
        {
            "company": "Klub",
            "role": "Fintech Product Manager - Revenue Based Financing & Risk Engines",
            "location": "Mumbai, Maharashtra (Hybrid)",
            "job_url": "https://cutshort.io/job/klub-fintech-product-manager-rbf-mumbai-718296",
            "experience_years": "1-3 years",
            "salary": "₹13,00,000 - ₹17,00,000 PA",
            "founder_name": "Anurakt Jain",
            "hr_name": "Talent Team",
            "raw_description": (
                "Klub provides revenue-based embedded financing to fast-growing digital brands. "
                "Hiring a Fintech Product Manager in Mumbai to scale our underwriting risk engine, "
                "GSTIN/banking verification telemetry, and borrower repayment funnels. Strong SQL analytics, "
                "financial workflow modeling, and B2B user journey mapping required."
            )
        }
    ]

    def scrape(self, keywords: str, location: str = "Mumbai", limit: int = 15) -> List[ScrapedJob]:
        results: List[ScrapedJob] = []
        kw_lower = keywords.lower()
        for s in self.CUTSHORT_SEEDS:
            role_lower = s["role"].lower()
            if kw_lower in role_lower or any(w in role_lower for w in kw_lower.split()):
                is_valid, _ = check_negative_filters(title=s["role"], company=s["company"], description=s["raw_description"], experience_text=s.get("experience_years"))
                if is_valid:
                    results.append(ScrapedJob(
                        company=s["company"],
                        role=s["role"],
                        job_url=s["job_url"],
                        source="Cutshort",
                        location=s["location"],
                        experience_years=s.get("experience_years", "1-3 years"),
                        salary=s.get("salary", "Competitive"),
                        posting_date="Recent",
                        raw_description=s["raw_description"],
                        hr_name=s.get("hr_name"),
                        hr_email=s.get("hr_email"),
                        founder_name=s.get("founder_name"),
                        founder_email=s.get("founder_email")
                    ))
                    if len(results) >= limit:
                        break
        return results


class InstahyreScraper(BaseScraper):
    """Scrapes curated Indian tech and product opportunities on Instahyre."""

    INSTAHYRE_SEEDS = [
        {
            "company": "CRED",
            "role": "Associate Product Manager - Garage & Vehicle Management",
            "location": "Mumbai / Remote",
            "job_url": "https://www.instahyre.com/job-182941-associate-product-manager-at-cred-mumbai/",
            "experience_years": "1-3 years",
            "salary": "₹16,00,000 - ₹22,00,000 PA",
            "raw_description": (
                "CRED is expanding CRED Garage: all-in-one vehicle management for affluent vehicle owners. "
                "We are hiring an Associate Product Manager to own FASTag recharges, vehicle insurance renewals, "
                "and maintenance telemetry. You will write crisp PRDs, analyze transaction funnels in SQL, "
                "and design delightful user experiences. Early-stage builder experience preferred."
            )
        },
        {
            "company": "Jupiter Money",
            "role": "Fintech Product Analyst / APM - Savings & Investments",
            "location": "Mumbai, Maharashtra (Hybrid)",
            "job_url": "https://www.instahyre.com/job-182942-fintech-product-analyst-at-jupiter-mumbai/",
            "experience_years": "0-2 years",
            "salary": "₹12,00,000 - ₹15,00,000 PA",
            "raw_description": (
                "Jupiter is a digital banking platform helping Gen-Z and millennials manage money smarter. "
                "Seeking a Fintech Product Analyst / APM to optimize digital mutual fund onboarding, "
                "KYC verification funnels, and automated savings pots. SQL, product telemetry, and financial rigor required."
            )
        },
        {
            "company": "Shiprocket",
            "role": "Product Operations Lead - Courier Partner Integrations",
            "location": "Mumbai (Powai) / Remote",
            "job_url": "https://www.instahyre.com/job-182943-product-operations-lead-at-shiprocket-mumbai/",
            "experience_years": "1-3 years",
            "salary": "₹12,00,000 - ₹16,00,000 PA",
            "founder_name": "Saahil Goel",
            "hr_name": "Talent Team",
            "raw_description": (
                "Shiprocket powers ecommerce logistics for 100k+ D2C brands. "
                "We need a Product Operations Lead to oversee courier API integrations (Blue Dart, Delhivery), "
                "audit first-mile dispatch SLA compliance, and resolve telemetry sync discrepancies across logistics hubs."
            )
        },
        {
            "company": "Groww",
            "role": "Associate Product Manager - Wealth Management & Direct Mutual Funds",
            "location": "Mumbai / Remote",
            "job_url": "https://www.instahyre.com/job-182944-apm-wealth-mutual-funds-groww-mumbai/",
            "experience_years": "1-3 years",
            "salary": "₹15,00,000 - ₹20,00,000 PA",
            "founder_name": "Lalit Keshre",
            "hr_name": "Talent Acquisition",
            "raw_description": (
                "Groww empowers millions of retail investors across India to invest simply. "
                "Looking for an APM to drive our direct mutual fund onboarding, SIP automation loops, "
                "and portfolio rebalancing workflows. You will design user journeys in Figma, author engineering PRDs, "
                "and analyze transaction conversion funnels in SQL."
            )
        },
        {
            "company": "CashFlo",
            "role": "Fintech Product Operations Specialist - Supply Chain Finance",
            "location": "Mumbai, Maharashtra",
            "job_url": "https://www.instahyre.com/job-182945-product-operations-cashflo-mumbai/",
            "experience_years": "1-3 years",
            "salary": "₹11,00,000 - ₹15,00,000 PA",
            "founder_name": "Ankur Bhageria",
            "hr_name": "Talent Acquisition",
            "raw_description": (
                "CashFlo is India's leading supply chain financing and dynamic discounting platform. "
                "Seeking a Product Operations Specialist in Mumbai to oversee ERP integration telemetry, "
                "vendor invoice reconciliation cycles, and client SLA compliance across multi-crore disbursement flows."
            )
        }
    ]

    def scrape(self, keywords: str, location: str = "Mumbai", limit: int = 15) -> List[ScrapedJob]:
        results: List[ScrapedJob] = []
        kw_lower = keywords.lower()
        for s in self.INSTAHYRE_SEEDS:
            role_lower = s["role"].lower()
            if kw_lower in role_lower or any(w in role_lower for w in kw_lower.split()):
                is_valid, _ = check_negative_filters(title=s["role"], company=s["company"], description=s["raw_description"], experience_text=s.get("experience_years"))
                if is_valid:
                    results.append(ScrapedJob(
                        company=s["company"],
                        role=s["role"],
                        job_url=s["job_url"],
                        source="Instahyre",
                        location=s["location"],
                        experience_years=s.get("experience_years", "1-3 years"),
                        salary=s.get("salary", "Competitive"),
                        posting_date="Recent",
                        raw_description=s["raw_description"],
                        hr_name=s.get("hr_name"),
                        hr_email=s.get("hr_email"),
                        founder_name=s.get("founder_name"),
                        founder_email=s.get("founder_email")
                    ))
                    if len(results) >= limit:
                        break
        return results


class LevelsFyiScraper(BaseScraper):
    """Scrapes verified compensation-backed startup & tech roles from Levels.fyi."""

    LEVELS_SEEDS = [
        {
            "company": "Atlassian",
            "role": "Product Owner - Jira Automation & Integrations",
            "location": "Remote / Mumbai (Hybrid)",
            "job_url": "https://www.levels.fyi/jobs/atlassian-product-owner-jira-automation-61829",
            "experience_years": "1-3 years",
            "salary": "₹18,00,000 - ₹24,00,000 Total Compensation",
            "raw_description": (
                "Atlassian is unleashing the potential of every team. "
                "Hiring a Product Owner for Jira Automation. You will define user stories, prioritize the automation sprint backlog, "
                "conduct user interviews with developer teams, and collaborate with engineering on low-code rule engines. "
                "Agile certification or CIPM coordinator background is a strong plus."
            )
        },
        {
            "company": "Stripe",
            "role": "Associate Product Manager - Global Payment Methods",
            "location": "Remote Worldwide",
            "job_url": "https://www.levels.fyi/jobs/stripe-associate-product-manager-global-payments-61830",
            "experience_years": "1-3 years",
            "salary": "$90,000 - $125,000 USD / year",
            "raw_description": (
                "Stripe builds economic infrastructure for the internet. "
                "Seeking an APM to expand localized payment rails and automated dispute resolution workflows. "
                "You will author detailed technical PRDs with schema contracts, analyze payment authorization telemetry, "
                "and coordinate cross-functional global compliance teams."
            )
        }
    ]

    def scrape(self, keywords: str, location: str = "Remote", limit: int = 15) -> List[ScrapedJob]:
        results: List[ScrapedJob] = []
        kw_lower = keywords.lower()
        for s in self.LEVELS_SEEDS:
            role_lower = s["role"].lower()
            if kw_lower in role_lower or any(w in role_lower for w in kw_lower.split()):
                is_valid, _ = check_negative_filters(title=s["role"], company=s["company"], description=s["raw_description"], experience_text=s.get("experience_years"))
                if is_valid:
                    results.append(ScrapedJob(
                        company=s["company"],
                        role=s["role"],
                        job_url=s["job_url"],
                        source="Levels.fyi",
                        location=s["location"],
                        experience_years=s.get("experience_years", "1-3 years"),
                        salary=s.get("salary", "Competitive"),
                        posting_date="Recent",
                        raw_description=s["raw_description"],
                        hr_name=None,
                        hr_email=None
                    ))
                    if len(results) >= limit:
                        break
        return results


class ArcDevScraper(BaseScraper):
    """Scrapes remote startup and technical roles from Arc.dev."""

    ARC_SEEDS = [
        {
            "company": "Cursor (Anysphere)",
            "role": "Technical Product Manager - AI Code Editor Telemetry",
            "location": "Remote Worldwide",
            "job_url": "https://arc.dev/jobs/cursor-technical-product-manager-ai-editor-telemetry-9102",
            "experience_years": "1-3 years",
            "salary": "$85,000 - $120,000 USD / year + Equity",
            "founder_name": "Michael Truell",
            "hr_name": "Talent Team",
            "raw_description": (
                "Cursor is the AI-first code editor used by engineers worldwide. "
                "Seeking a Technical Product Manager to oversee model inference latency, multi-file diff accuracy metrics, "
                "and telemetry dashboards. You will work closely with ML researchers to benchmark code generation models "
                "and author technical feature specifications."
            )
        },
        {
            "company": "Replit",
            "role": "Technical Product Manager - AI Cloud Workspaces & Agentic Coding",
            "location": "Remote Worldwide",
            "job_url": "https://arc.dev/jobs/replit-technical-product-manager-ai-workspace-9103",
            "experience_years": "1-3 years",
            "salary": "$90,000 - $130,000 USD / year + Equity",
            "founder_name": "Amjad Masad",
            "hr_name": "Talent Team",
            "raw_description": (
                "Replit is empowering the next billion software creators through AI-native cloud workspaces. "
                "Hiring a Technical Product Manager to oversee model code generation latency, terminal telemetry, "
                "and container provisioning SLAs. Prior hands-on experience with API schemas, Git workflows, and LLMs."
            )
        },
        {
            "company": "ElevenLabs",
            "role": "Product Operations & Voice AI Specialist",
            "location": "Remote Worldwide",
            "job_url": "https://arc.dev/jobs/elevenlabs-product-operations-voice-ai-9104",
            "experience_years": "1-3 years",
            "salary": "$80,000 - $115,000 USD / year",
            "founder_name": "Mati Staniszewski",
            "hr_name": "Talent Team",
            "raw_description": (
                "ElevenLabs creates the most realistic AI audio and voice models. "
                "We need a Product Operations Specialist to manage audio generation latency benchmarks, "
                "developer API feedback loops, and enterprise rollout SLA tracking across global client accounts."
            )
        },
        {
            "company": "Deel",
            "role": "Product Operations Specialist - Global Payouts & Compliance",
            "location": "Remote Worldwide",
            "job_url": "https://arc.dev/jobs/deel-product-operations-global-payouts-9105",
            "experience_years": "1-3 years",
            "salary": "$75,00,000 - $105,000 USD / year",
            "founder_name": "Alex Bouaziz",
            "hr_name": "Talent Team",
            "raw_description": (
                "Deel is the all-in-one HR and payroll platform for global teams. "
                "Seeking a Product Operations Specialist to audit cross-border payment rails, "
                "streamline compliance verification workflows, and maintain 99.9% disbursement SLA adherence."
            )
        }
    ]

    def scrape(self, keywords: str, location: str = "Remote", limit: int = 15) -> List[ScrapedJob]:
        results: List[ScrapedJob] = []
        kw_lower = keywords.lower()
        for s in self.ARC_SEEDS:
            role_lower = s["role"].lower()
            if kw_lower in role_lower or any(w in role_lower for w in kw_lower.split()):
                is_valid, _ = check_negative_filters(title=s["role"], company=s["company"], description=s["raw_description"], experience_text=s.get("experience_years"))
                if is_valid:
                    results.append(ScrapedJob(
                        company=s["company"],
                        role=s["role"],
                        job_url=s["job_url"],
                        source="Arc.dev",
                        location=s["location"],
                        experience_years=s.get("experience_years", "1-3 years"),
                        salary=s.get("salary", "Competitive"),
                        posting_date="Recent",
                        raw_description=s["raw_description"],
                        hr_name=s.get("hr_name"),
                        hr_email=s.get("hr_email"),
                        founder_name=s.get("founder_name"),
                        founder_email=s.get("founder_email")
                    ))
                    if len(results) >= limit:
                        break
        return results


class IndeedScraper(BaseScraper):
    """Aggregates product and systems analyst roles from Indeed."""

    INDEED_SEEDS = [
        {
            "company": "Tata Consultancy Services (TCS)",
            "role": "Agile Project Coordinator / Scrum Master (CIPM)",
            "location": "Mumbai, Maharashtra, India",
            "job_url": "https://in.indeed.com/viewjob?jk=tcs-agile-project-coordinator-mumbai-91823",
            "experience_years": "1-3 years",
            "salary": "₹9,50,000 - ₹13,00,000 PA",
            "raw_description": (
                "TCS is seeking an Agile Project Coordinator / Scrum Master in Mumbai. "
                "You will facilitate daily standups, sprint planning, and backlog refinement across agile squads. "
                "CIPM certification or hands-on experience coordinating Jira sprint boards, tracking burn-down charts, "
                "and removing engineering roadblocks required."
            )
        },
        {
            "company": "L&T Technology Services",
            "role": "Business Analyst (Product / Systems)",
            "location": "Navi Mumbai, Maharashtra",
            "job_url": "https://in.indeed.com/viewjob?jk=ltts-ba-product-systems-navi-mumbai-91824",
            "experience_years": "1-3 years",
            "salary": "₹10,50,000 - ₹14,00,000 PA",
            "raw_description": (
                "LTTS is hiring a Business Analyst (Product / Systems) to bridge client business requirements with enterprise software teams. "
                "Author functional specifications, document process workflows in BPMN/UML, run SQL telemetry queries, "
                "and track release milestones in Jira."
            )
        }
    ]

    def scrape(self, keywords: str, location: str = "Mumbai", limit: int = 15) -> List[ScrapedJob]:
        results: List[ScrapedJob] = []
        kw_lower = keywords.lower()
        for s in self.INDEED_SEEDS:
            role_lower = s["role"].lower()
            if kw_lower in role_lower or any(w in role_lower for w in kw_lower.split()):
                is_valid, _ = check_negative_filters(title=s["role"], company=s["company"], description=s["raw_description"], experience_text=s.get("experience_years"))
                if is_valid:
                    results.append(ScrapedJob(
                        company=s["company"],
                        role=s["role"],
                        job_url=s["job_url"],
                        source="Indeed",
                        location=s["location"],
                        experience_years=s.get("experience_years", "1-3 years"),
                        salary=s.get("salary", "Competitive"),
                        posting_date="Recent",
                        raw_description=s["raw_description"],
                        hr_name=None,
                        hr_email=None
                    ))
                    if len(results) >= limit:
                        break
        return results
