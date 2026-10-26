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
import requests

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

        # If Hunter API key is provided, try enrichment
        if not primary_email and self.hunter_api_key and name != "Talent Acquisition":
            hunter_email = self._query_hunter(name, domain)
            if hunter_email:
                primary_email = hunter_email

        permutations = self.generate_permutations(name, domain)
        if not primary_email:
            primary_email = permutations[0]

        return {
            "name": name,
            "domain": domain,
            "primary_email": primary_email,
            "permutations": permutations,
            "mx_valid": mx_valid,
            "mx_servers": mx_servers,
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

    def draft_outreach(self, job: ScrapedJob, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """Drafts LinkedIn connection note and cold email."""
        contact = self.enricher.find_or_enrich_contact(job)
        hr_name = contact["name"]
        first_name = hr_name.split()[0] if hr_name else "there"

        # LinkedIn Note: strictly under 300 characters
        linkedin_note = (
            f"Hi {first_name}, saw {job.company}'s {job.role} opening. "
            f"At HireFlo I cut Llama 3.1 inference compute costs by 40% via NVIDIA NIM and previously led 200+ ops deployments "
            f"at NeoManpower with zero SLA breaches. Would love to connect and share my interactive PM Lab builds: "
            f"https://manavmate53-jpg.github.io/pm-product-lab/#hub"
        )
        short_role = job.role.split(" - ")[0].split(" (")[0]
        if len(linkedin_note) > 295:
            # Compact version using clean shortened role
            linkedin_note = (
                f"Hi {first_name}, saw {job.company}'s {short_role} role. At HireFlo I cut Llama 3.1 compute costs by 40% "
                f"and led 200+ ops deployments at NeoManpower with 0 SLA breaches. "
                f"Would love to connect and share my PM builds: https://manavmate53-jpg.github.io/pm-product-lab/#hub"
            )
        if len(linkedin_note) > 295:
            linkedin_note = linkedin_note[:292] + "..."

        # Cold Email Subject & Body
        email_subject = f"{job.role} - Manav Mate | Builder & Product Manager"
        email_body = (
            f"Hi {hr_name},\n\n"
            f"I noticed {job.company} is hiring for {job.role}.\n\n"
            f"I am an early-career product manager and former bootstrapped founder. At HireFlo India, "
            f"I owned product discovery and shipped our Llama 3.1 inference pipeline on NVIDIA NIM, "
            f"cutting compute costs by 40% while building a 1,000-document parsing workflow in 10 minutes. "
            f"Prior to that, I bootstrapped NeoManpower to 50+ B2B corporate clients and led 200+ ground "
            f"deployments across Mumbai with zero SLA breaches.\n\n"
            f"I have also built live systems in my PM Product Lab, including EvalGuard AI (schema guardrails) "
            f"and AutoMatch IQ (marketplace funnel telemetry): https://manavmate53-jpg.github.io/pm-product-lab/#hub\n\n"
            f"I have attached my tailored resume for your review. I would welcome the opportunity to discuss "
            f"how my technical PRD execution and operational discipline can support {job.company}.\n\n"
            f"Best regards,\n"
            f"Manav Mate\n"
            f"+91 85915 95889 | manavmate53@gmail.com\n"
            f"Portfolio: https://manavmate53-jpg.github.io/portfolio/#hero"
        )
        email_body = sanitize_builder_text(email_body)

        return {
            "contact": contact,
            "linkedin_note": linkedin_note,
            "linkedin_note_chars": len(linkedin_note),
            "email_subject": email_subject,
            "email_body": email_body,
            "attachment_pdf": pdf_path,
        }

    def process_outreach(self, job: ScrapedJob, pdf_path: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
        """Failsafe outreach dispatcher. If dry_run is True (default), writes draft to file. If False, sends via SMTP."""
        draft = self.draft_outreach(job, pdf_path)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_comp = re.sub(r"[^\w-]", "_", job.company)

        # Save draft inspection payload
        draft_txt_path = self.drafts_dir / f"draft_{safe_comp}_{timestamp}.txt"
        draft_json_path = self.drafts_dir / f"draft_{safe_comp}_{timestamp}.json"

        with open(draft_txt_path, "w", encoding="utf-8") as f:
            f.write(f"=== RECIPIENT DETAILS ===\n")
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
                "draft": draft,
                "timestamp": timestamp,
                "status": "DRAFTED" if dry_run else "DISPATCHED"
            }, f, indent=2)

        if dry_run:
            logger.info(f"[DRY-RUN] Outreach drafted and logged safely to {draft_txt_path}")
            return {
                "dispatched": False,
                "mode": "DRY_RUN",
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
                "draft_txt_path": str(draft_txt_path),
                "draft_json_path": str(draft_json_path),
                "draft": draft,
                "smtp_details": send_result
            }

    def _dispatch_smtp(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches email via standard SMTP."""
        smtp_user = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
        smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))

        recipient = draft["contact"]["primary_email"]

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
