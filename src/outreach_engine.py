"""HR / TA Enrichment & Cold Outreach Engine.

Provides:
1. Contact Finder & Permutation Engine with DNS MX record verification.
2. Optional Hunter.io / Apollo API integration.
3. Outreach Drafter:
   - Direct LinkedIn connection note (under 300 chars)
   - Cold email message
4. Safe Dispatcher:
   - Mandatory --dry-run flag (default True) that saves drafts to exports/outreach_drafts/
   - Live SMTP dispatch with PDF attachment only when --send is explicitly specified.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import smtplib
import socket
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
import requests

load_dotenv()

from src.profile_engine import ProfileEngine, sanitize_builder_text
from src.scrapers.base_scraper import ScrapedJob

logger = logging.getLogger(__name__)



def derive_domain_from_company_or_url(company: str, job_url: str = "") -> str:
    """Infers official corporate domain for email permutations."""
    # Common company domain overrides
    domain_map = {
        "zepto": "zepto.co",
        "kreditbee": "kreditbee.in",
        "clear": "cleartax.in",
        "cleartax": "cleartax.in",
        "fractal": "fractal.ai",
        "fractal ai": "fractal.ai",
        "shiprocket": "shiprocket.com",
        "browserstack": "browserstack.com",
        "porter": "porter.in",
        "pocket fm": "pocketfm.com",
        "pocketfm": "pocketfm.com",
        "perfios": "perfios.com",
        "cashflo": "cashflo.io",
        "loginext": "loginextsolutions.com",
    }
    comp_clean = company.lower().strip()
    for key, dom in domain_map.items():
        if key in comp_clean:
            return dom

    # Strip punctuation and common suffixes
    clean = re.sub(r"\b(pvt|ltd|limited|inc|technologies|solutions|india|software)\b", "", comp_clean)
    clean = re.sub(r"[^a-z0-9]", "", clean)
    if clean:
        return f"{clean}.com"
    return "company.com"


FOUNDER_DIRECTORY: Dict[str, Dict[str, str]] = {
    "perplexity": {"founder": "Aravind Srinivas", "role": "Founder & CEO", "domain": "perplexity.ai"},
    "sarvam": {"founder": "Pratyush Kumar", "role": "Co-Founder", "domain": "sarvam.ai"},
    "together": {"founder": "Vipul Ved Prakash", "role": "Co-Founder & CEO", "domain": "together.ai"},
    "llamaindex": {"founder": "Jerry Liu", "role": "Co-Founder & CEO", "domain": "llamaindex.ai"},
    "posthog": {"founder": "James Hawkins", "role": "Co-Founder & CEO", "domain": "posthog.com"},
    "korbit": {"founder": "Anson Vanduren", "role": "Co-Founder & CEO", "domain": "korbit.ai"},
    "invideo": {"founder": "Sanket Shah", "role": "Founder & CEO", "domain": "invideo.io"},
    "dukaan": {"founder": "Suumit Shah", "role": "Founder & CEO", "domain": "mydukaan.io"},
    "superops": {"founder": "Arvind Parthiban", "role": "Co-Founder & CEO", "domain": "superops.ai"},
    "zepto": {"founder": "Aadit Palicha", "role": "Co-Founder & CEO", "domain": "zepto.co"},
    "landeed": {"founder": "Sanjay Mandava", "role": "Founder & CEO", "domain": "landeed.com"},
    "gupshup": {"founder": "Beerud Sheth", "role": "Co-Founder & CEO", "domain": "gupshup.io"},
    "sprinto": {"founder": "Girish Redekar", "role": "Co-Founder & CEO", "domain": "sprinto.com"},
    "fashinza": {"founder": "Pawan Gupta", "role": "Co-Founder & CEO", "domain": "fashinza.com"},
    "cred": {"founder": "Kunal Shah", "role": "Founder", "domain": "cred.club"},
    "jupiter": {"founder": "Jitendra Gupta", "role": "Founder & CEO", "domain": "jupitermoney.com"},
    "shiprocket": {"founder": "Saahil Goel", "role": "Co-Founder & CEO", "domain": "shiprocket.in"},
    "cursor": {"founder": "Michael Truell", "role": "Co-Founder & CEO", "domain": "cursor.com"},
    "anysphere": {"founder": "Michael Truell", "role": "Co-Founder & CEO", "domain": "anysphere.co"},
    "linear": {"founder": "Karri Saarinen", "role": "Co-Founder & CEO", "domain": "linear.app"},
    "elevenlabs": {"founder": "Mati Staniszewski", "role": "Co-Founder & CEO", "domain": "elevenlabs.io"},
    "replit": {"founder": "Amjad Masad", "role": "Founder & CEO", "domain": "replit.com"},
    "deel": {"founder": "Alex Bouaziz", "role": "Co-Founder & CEO", "domain": "deel.com"},
    "groww": {"founder": "Lalit Keshre", "role": "Co-Founder & CEO", "domain": "groww.in"},
    "klub": {"founder": "Anurakt Jain", "role": "Co-Founder & CEO", "domain": "klubworks.com"},
    "cashflo": {"founder": "Ankur Bhageria", "role": "Founder & CEO", "domain": "cashflo.io"},
    "porter": {"founder": "Pranav Goel", "role": "Co-Founder & CEO", "domain": "porter.in"},
    "pocket fm": {"founder": "Rohan Nayak", "role": "Co-Founder & CEO", "domain": "pocketfm.com"},
    "perfios": {"founder": "V.R. Govindarajan", "role": "Co-Founder", "domain": "perfios.com"},
    "kreditbee": {"founder": "Madhusudan Ekambaram", "role": "Co-Founder & CEO", "domain": "kreditbee.in"},
    "swiggy": {"founder": "Sriharsha Majety", "role": "Group CEO & Co-Founder", "domain": "swiggy.in"},
    "razorpay": {"founder": "Harshil Mathur", "role": "Co-Founder & CEO", "domain": "razorpay.com"},
    "atlassian": {"founder": "Mike Cannon-Brookes", "role": "Co-Founder & Co-CEO", "domain": "atlassian.com"},
    "stripe": {"founder": "Patrick Collison", "role": "Co-Founder & CEO", "domain": "stripe.com"},
    "gitlab": {"founder": "Sid Sijbrandij", "role": "Co-Founder & CEO", "domain": "gitlab.com"},
    "automattic": {"founder": "Matt Mullenweg", "role": "Founder & CEO", "domain": "automattic.com"},
    "zapier": {"founder": "Wade Foster", "role": "Co-Founder & CEO", "domain": "zapier.com"},
}


class ContactEnricher:
    """Generates email permutations and verifies MX records."""

    def __init__(self):
        self.hunter_api_key = os.getenv("HUNTER_API_KEY")
        self.apollo_api_key = os.getenv("APOLLO_API_KEY")

    def check_mx_records(self, domain: str) -> Tuple[bool, List[str]]:
        """Verifies if the domain has active DNS MX records."""
        try:
            import dns.resolver
            records = dns.resolver.resolve(domain, "MX")
            servers = [str(r.exchange).rstrip(".") for r in records]
            return True, servers
        except Exception as e:
            logger.debug(f"DNS MX lookup failed for {domain}: {e}")
            # Socket fallback check
            try:
                socket.gethostbyname(domain)
                return True, [f"A-record-fallback({domain})"]
            except Exception:
                return False, []

    def generate_permutations(self, full_name: str, domain: str) -> List[str]:
        """Generates standard corporate email permutations for a name and domain."""
        parts = [p.lower() for p in re.split(r"\s+", full_name.strip()) if p]
        if not parts:
            return [f"careers@{domain}", f"hiring@{domain}"]
        
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""

        permutations = []
        if last:
            permutations.append(f"{first}.{last}@{domain}")
            permutations.append(f"{first}@{domain}")
            permutations.append(f"{first[0]}{last}@{domain}")
            permutations.append(f"{first}{last[0]}@{domain}")
            permutations.append(f"{first}_{last}@{domain}")
            permutations.append(f"{last}.{first}@{domain}")
        else:
            permutations.append(f"{first}@{domain}")
            permutations.append(f"careers@{domain}")

        return permutations

    def find_or_enrich_contact(self, job: ScrapedJob) -> Dict[str, Any]:
        """Resolves recruiter name, best email, permutations, and MX health."""
        domain = derive_domain_from_company_or_url(job.company, job.job_url)
        mx_valid, mx_servers = self.check_mx_records(domain)

        name = job.hr_name or "Talent Acquisition"
        primary_email = job.hr_email
        is_verified = bool(primary_email)

        # If Hunter API key is provided, try enrichment
        if not primary_email and self.hunter_api_key and name != "Talent Acquisition":
            hunter_email = self._query_hunter(name, domain)
            if hunter_email:
                primary_email = hunter_email
                is_verified = True

        permutations = self.generate_permutations(name, domain)
        if not primary_email:
            primary_email = permutations[0]
            is_verified = False

        return {
            "name": name,
            "domain": domain,
            "primary_email": primary_email,
            "permutations": permutations,
            "mx_valid": mx_valid,
            "mx_servers": mx_servers,
            "is_verified": is_verified,
        }


    def find_founder_contact(self, job: ScrapedJob) -> Dict[str, Any]:
        """Resolves company founder name, corporate domain, and permutations."""
        comp_lower = job.company.lower()
        founder_name = job.founder_name
        domain = derive_domain_from_company_or_url(job.company, job.job_url)

        for key, info in FOUNDER_DIRECTORY.items():
            if key in comp_lower:
                founder_name = info["founder"]
                domain = info.get("domain", domain)
                break

        if not founder_name:
            founder_name = f"Founder of {job.company}"

        mx_valid, mx_servers = self.check_mx_records(domain)
        permutations = self.generate_permutations(founder_name, domain)
        primary_email = job.founder_email or permutations[0]
        is_verified = bool(job.founder_email)

        return {
            "name": founder_name,
            "domain": domain,
            "primary_email": primary_email,
            "permutations": permutations,
            "mx_valid": mx_valid,
            "mx_servers": mx_servers,
            "is_verified": is_verified,
            "type": "FOUNDER"
        }

    def _query_hunter(self, name: str, domain: str) -> Optional[str]:
        try:
            parts = name.split()
            first = parts[0]
            last = parts[-1] if len(parts) > 1 else ""
            url = f"https://api.hunter.io/v2/email-finder?domain={domain}&first_name={first}&last_name={last}&api_key={self.hunter_api_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return data.get("email")
        except Exception as e:
            logger.warning(f"Hunter.io lookup failed: {e}")
        return None


class OutreachEngine:
    """Drafts and safely dispatches cold recruiter outreach."""

    def __init__(self, base_dir: Optional[Path] = None, profile_engine: Optional[ProfileEngine] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.profile_engine = profile_engine or ProfileEngine()
        self.enricher = ContactEnricher()
        self.drafts_dir = self.base_dir / "exports" / "outreach_drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    def draft_outreach(self, job: ScrapedJob, pdf_path: Optional[str] = None, recipient_type: str = "TA") -> Dict[str, Any]:
        """Drafts LinkedIn connection note and cold email tailored for either FOUNDER or TA/HR."""
        short_role = job.role.split(" - ")[0].split(" (")[0]
        
        if recipient_type.upper() == "FOUNDER":
            contact = self.enricher.find_founder_contact(job)
            full_name = contact["name"]
            first_name = full_name.split()[0] if full_name else "there"

            # LinkedIn Note: strictly under 300 characters
            linkedin_note = (
                f"Hi {first_name}, saw {job.company}'s {short_role} role. Ex-bootstrapped founder (NeoManpower: 50+ B2B clients, 200+ field deployments, 0 SLA breaches). "
                f"At HireFlo I cut Llama 3.1 compute costs 40% via NVIDIA NIM. Built live PM Lab demos: "
                f"https://manavmate53-jpg.github.io/pm-product-lab/#hub - would love 15 mins to connect!"
            )
            if len(linkedin_note) > 295:
                linkedin_note = (
                    f"Hi {first_name}, saw {job.company}'s {short_role} role. Ex-founder (50+ B2B clients, 200+ ops projects 0 SLA breaches). "
                    f"At HireFlo cut Llama 3.1 compute 40% via NVIDIA NIM. Live PM Lab demos: "
                    f"https://manavmate53-jpg.github.io/pm-product-lab/#hub - would love to connect!"
                )
            if len(linkedin_note) > 295:
                linkedin_note = linkedin_note[:292] + "..."

            email_subject = f"{job.role} - Manav Mate | 0-to-1 Builder & Bootstrapped Founder"
            email_body = (
                f"Hi {first_name},\n\n"
                f"I noticed {job.company} is scaling and hiring for {job.role}.\n\n"
                f"As a former bootstrapped founder, I understand the focus required on high-velocity execution without overhead. "
                f"I bootstrapped NeoManpower from zero to 50+ B2B corporate enterprise clients and orchestrated 200+ commercial operations "
                f"across Mumbai with zero SLA breaches.\n\n"
                f"Transitioning to tech product management at HireFlo India, I owned product discovery and shipped our Llama 3.1 inference pipeline "
                f"on NVIDIA NIM, reducing compute costs by 40% while engineering a 1,000-document resume parsing pipeline in under 10 minutes (98% precision). "
                f"I also improved candidate self-serve onboarding completion by 30% through UX friction audits.\n\n"
                f"I also built live interactive systems in my PM Product Lab, including EvalGuard AI (schema guardrails & evaluation) "
                f"and AutoMatch IQ (marketplace funnel telemetry): https://manavmate53-jpg.github.io/pm-product-lab/#hub\n\n"
                f"I have attached my tailored single-page A4 resume. I would value a brief 15-minute conversation before the end of October "
                f"to discuss how my technical PRD execution and founder grit can immediately unblock roadmap priorities for {job.company}.\n\n"
                f"Best regards,\n"
                f"Manav Mate\n"
                f"+91 85915 95889 | manavmate53@gmail.com\n"
                f"Portfolio: https://manavmate53-jpg.github.io/portfolio/#hero"
            )
        else:
            contact = self.enricher.find_or_enrich_contact(job)
            hr_name = contact["name"]
            first_name = hr_name.split()[0] if hr_name else "there"

            # LinkedIn Note: strictly under 300 characters
            linkedin_note = (
                f"Hi {first_name}, saw your {job.company} {short_role} opening. Early-career PM & CIPM delivery lead. "
                f"At HireFlo I cut Llama 3.1 compute costs by 40% via NVIDIA NIM and led 14+ PRDs in Jira. "
                f"Would love to connect and share my interactive PM builds: https://manavmate53-jpg.github.io/pm-product-lab/#hub"
            )
            if len(linkedin_note) > 295:
                linkedin_note = (
                    f"Hi {first_name}, saw {job.company}'s {short_role} role. At HireFlo I cut Llama 3.1 compute costs by 40% "
                    f"and led 200+ ops deployments at NeoManpower with 0 SLA breaches. "
                    f"Would love to connect and share my PM builds: https://manavmate53-jpg.github.io/pm-product-lab/#hub"
                )
            if len(linkedin_note) > 295:
                linkedin_note = linkedin_note[:292] + "..."

            email_subject = f"Application: {job.role} - Manav Mate (ATS 80+ Match | Single-Page CV Attached)"
            email_body = (
                f"Hi {hr_name},\n\n"
                f"I am writing to apply for the {job.role} opening at {job.company}.\n\n"
                f"I am an early-career product manager and Certified International Project Manager (CIPM) with hands-on experience "
                f"in 0-to-1 product discovery, technical PRD authoring, and sprint execution directly with engineering squads.\n\n"
                f"Key highlights relevant to {job.company}:\n"
                f"- Model Compute Optimization: Cut inference compute costs by 40% on Llama 3.1 at HireFlo India by deploying self-hosted microservices via NVIDIA NIM.\n"
                f"- Data Pipeline Engineering: Built and shipped a 1,000-document parsing and extraction pipeline completing runs in under 10 minutes with 98% field precision.\n"
                f"- User Funnel Growth: Improved candidate platform onboarding completion by 30% through UX friction audits.\n"
                f"- Operational Scale: Bootstrapped NeoManpower to 50+ B2B enterprise clients and 200+ projects across Mumbai with zero SLA breaches.\n\n"
                f"Live interactive builds in my PM Product Lab: https://manavmate53-jpg.github.io/pm-product-lab/#hub\n\n"
                f"My tailored single-page A4 resume is attached. I am available for an introductory interview at your earliest convenience this week before October ends.\n\n"
                f"Warm regards,\n"
                f"Manav Mate\n"
                f"+91 85915 95889 | manavmate53@gmail.com\n"
                f"Portfolio: https://manavmate53-jpg.github.io/portfolio/#hero"
            )

        email_body = sanitize_builder_text(email_body)

        return {
            "contact": contact,
            "recipient_type": recipient_type.upper(),
            "linkedin_note": linkedin_note,
            "linkedin_note_chars": len(linkedin_note),
            "email_subject": email_subject,
            "email_body": email_body,
            "attachment_pdf": pdf_path,
        }

    def process_outreach(
        self,
        job: ScrapedJob,
        pdf_path: Optional[str] = None,
        dry_run: bool = True,
        recipient_type: str = "TA"
    ) -> Dict[str, Any]:
        """Failsafe outreach dispatcher. If dry_run is True (default), writes draft to file. If False, sends via SMTP."""
        draft = self.draft_outreach(job, pdf_path, recipient_type=recipient_type)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_comp = re.sub(r"[^\w-]", "_", job.company)
        recip_slug = recipient_type.upper()

        # Save draft inspection payload
        draft_txt_path = self.drafts_dir / f"draft_{safe_comp}_{recip_slug}_{timestamp}.txt"
        draft_json_path = self.drafts_dir / f"draft_{safe_comp}_{recip_slug}_{timestamp}.json"

        with open(draft_txt_path, "w", encoding="utf-8") as f:
            f.write(f"=== RECIPIENT DETAILS ({recip_slug}) ===\n")
            f.write(f"Target: {draft['contact']['name']} <{draft['contact']['primary_email']}>\n")
            f.write(f"Company: {job.company} | Role: {job.role}\n")
            f.write(f"Domain: {draft['contact']['domain']} (MX Valid: {draft['contact']['mx_valid']})\n")
            f.write(f"Permutations Tested: {', '.join(draft['contact']['permutations'])}\n\n")
            f.write(f"=== LINKEDIN CONNECTION NOTE ({draft['linkedin_note_chars']} chars) ===\n")
            f.write(f"{draft['linkedin_note']}\n\n")
            f.write(f"=== COLD EMAIL DRAFT ===\n")
            f.write(f"Subject: {draft['email_subject']}\n")
            f.write(f"Attachment: {draft['attachment_pdf'] or 'None'}\n\n")
            f.write(f"{draft['email_body']}\n")

        with open(draft_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "job": job.model_dump(),
                "recipient_type": recip_slug,
                "draft": draft,
                "timestamp": timestamp,
                "status": "DRAFTED" if dry_run else "DISPATCHED"
            }, f, indent=2)

        if dry_run:
            logger.info(f"[DRY-RUN] {recip_slug} outreach drafted and logged safely to {draft_txt_path}")
            return {
                "dispatched": False,
                "mode": "DRY_RUN",
                "recipient_type": recip_slug,
                "draft_txt_path": str(draft_txt_path),
                "draft_json_path": str(draft_json_path),
                "draft": draft,
                "message": f"Deterministic dry-run complete. Draft logged safely for inspection at {draft_txt_path}."
            }
        else:
            # Live dispatch requested
            send_result = self._dispatch_smtp(draft)
            return {
                "dispatched": send_result["success"],
                "mode": "LIVE_SEND",
                "recipient_type": recip_slug,
                "draft_txt_path": str(draft_txt_path),
                "draft_json_path": str(draft_json_path),
                "draft": draft,
                "smtp_details": send_result
            }

    def process_dual_outreach(
        self,
        job: ScrapedJob,
        pdf_path: Optional[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Formulates outreach for BOTH the company Founder and the TA/HR lead."""
        founder_res = self.process_outreach(job, pdf_path=pdf_path, dry_run=dry_run, recipient_type="FOUNDER")
        ta_res = self.process_outreach(job, pdf_path=pdf_path, dry_run=dry_run, recipient_type="TA")
        return {
            "company": job.company,
            "role": job.role,
            "founder": founder_res,
            "ta": ta_res
        }

    def _dispatch_smtp(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches email via standard SMTP."""
        smtp_user = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
        raw_pw = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
        smtp_password = raw_pw.replace(" ", "") if raw_pw else None
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")

        smtp_port = int(os.getenv("SMTP_PORT", "587"))

        recipient = draft["contact"]["primary_email"]
        is_verified = draft["contact"].get("is_verified", False)

        if not recipient or "@" not in recipient:
            return {
                "success": False,
                "error": "No recipient email address available for this posting."
            }

        if not is_verified:
            return {
                "success": False,
                "error": (
                    f"Failsafe Deliverability Shield: Recipient '{recipient}' is an unverified estimate. "
                    "Outbound SMTP is blocked to prevent bounces and protect your sender reputation. "
                    "Please apply via the direct portal link or send the custom LinkedIn connection note instead."
                )
            }

        if not smtp_user or not smtp_password:
            return {
                "success": False,
                "error": "SMTP credentials not configured. Please set SMTP_USER and SMTP_PASSWORD in .env."
            }


        try:
            msg = MIMEMultipart()
            msg["From"] = f"Manav Mate <{smtp_user}>"
            msg["To"] = recipient
            msg["Subject"] = draft["email_subject"]

            msg.attach(MIMEText(draft["email_body"], "plain"))

            # Attach PDF if exists
            pdf_path = draft.get("attachment_pdf")
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
                part["Content-Disposition"] = f'attachment; filename="{os.path.basename(pdf_path)}"'
                msg.attach(part)

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())

            logger.info(f"Email successfully dispatched to {recipient}")
            return {"success": True, "recipient": recipient}
        except Exception as e:
            logger.error(f"Failed to dispatch email via SMTP: {e}")
            return {"success": False, "error": str(e)}
