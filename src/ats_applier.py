"""Direct ATS Form Applier and Browser Co-Pilot Engine.

Provides two execution modes:
MODE A: Direct ATS Form Applier (Lever, Greenhouse, Trakstar, Gem, Ashby, Workable, Zoho)
MODE B: Persistent Logged-In Browser Co-Pilot Mode (Naukri, LinkedIn, Custom Portals)
Enforces Proof-of-Submission (PoS) Firewall.
"""

from __future__ import annotations

import datetime
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from playwright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from src.tracker_db import TrackerDB
from src.analytics.telemetry_db import TelemetryDB

logger = logging.getLogger(__name__)

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
PROOFS_DIR = BASE_DIR / "exports" / "proofs"
PROOFS_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_DATA = {
    "full_name": "Manav Mate",
    "first_name": "Manav",
    "last_name": "Mate",
    "email": "manavmate53@gmail.com",
    "phone": "+91 85915 95889",
    "phone_clean": "8591595889",
    "location": "Mumbai, Maharashtra, India",
    "city": "Mumbai",
    "state": "Maharashtra",
    "country": "India",
    "linkedin": "https://www.linkedin.com/in/manav-mate-9448b1341/",
    "portfolio": "https://manavmate53-jpg.github.io/portfolio/#hero",
    "product_lab": "https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering",
    "current_company": "NeoManpower / HireFlo",
    "current_title": "Product & Operations Lead",
    "experience_years": "4",
    "current_ctc": "6.0 LPA",
    "current_ctc_numeric": "600000",
    "expected_ctc": "6.5 - 7.2 LPA",
    "expected_ctc_numeric": "700000",
    "notice_period": "Immediate",
    "notice_period_days": "0"
}

TRACK_RESUMES = {
    "event_mice": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
    "founders_office": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Founders_Office_CV.pdf",
    "prod_ops": BASE_DIR / "exports" / "resumes" / "Manav_Mate_ProdOps_CV.pdf",
    "apm": BASE_DIR / "exports" / "resumes" / "Manav_Mate_APM_CV.pdf",
}

CONFIRMATION_PHRASES = [
    "thank you for applying",
    "application submitted",
    "application received",
    "we have received your application",
    "thanks for applying",
    "application complete",
    "your application has been submitted",
    "your application was submitted",
    "successfully applied",
    "thank you for submitting",
    "thank you for your interest",
    "we will be in touch",
    "application has been sent"
]

BOT_WALL_PHRASES = [
    "attention required! | cloudflare",
    "access denied",
    "403 forbidden",
    "verify you are human",
    "captcha",
    "cloudflare ray id",
    "please enable cookies"
]


class DirectATSApplier:
    """Automates form submission directly on ATS portals without bot walls."""

    def __init__(self, tracker_db: Optional[TrackerDB] = None, telemetry_db: Optional[TelemetryDB] = None):
        self.tracker_db = tracker_db or TrackerDB()
        self.telemetry_db = telemetry_db or TelemetryDB()

    def get_resume_path(self, track: str) -> Path:
        res = TRACK_RESUMES.get(track.lower())
        if res and res.exists():
            return res
        fallback = BASE_DIR / "exports" / "resumes" / "Manav_Mate_Master_CV.pdf"
        if fallback.exists():
            return fallback
        return TRACK_RESUMES["event_mice"]

    def detect_ats_type(self, url: str) -> str:
        u = url.lower()
        if "lever.co" in u:
            return "lever"
        elif "greenhouse.io" in u:
            return "greenhouse"
        elif "trakstar.com" in u:
            return "trakstar"
        elif "gem.com" in u:
            return "gem"
        elif "ashbyhq.com" in u:
            return "ashby"
        elif "workable.com" in u:
            return "workable"
        elif "zohorecruit" in u:
            return "zoho"
        elif "darwinbox" in u:
            return "darwinbox"
        return "generic_ats"

    def apply_job(
        self,
        job_id: int,
        job_url: str,
        company: str,
        role: str,
        track: str = "event_mice",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Applies to an ATS posting with Proof-of-Submission (PoS) verification."""
        ats_type = self.detect_ats_type(job_url)
        safe_comp = re.sub(r"[^\w-]", "_", company)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        resume_pdf = self.get_resume_path(track)

        logger.info(f"Applying to {company} ({role}) via {ats_type.upper()} | URL: {job_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                page.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                time.sleep(2)

                # Check for bot walls immediately
                page_text_lower = page.content().lower()
                for bw in BOT_WALL_PHRASES:
                    if bw in page_text_lower:
                        shot_path = PROOFS_DIR / f"blocked_{track}_{safe_comp}_{job_id}.png"
                        page.screenshot(path=str(shot_path))
                        browser.close()
                        self.tracker_db.mark_needs_human_click(job_id, f"Bot wall encountered ({bw})", str(shot_path))
                        return {
                            "status": "NEEDS_HUMAN_CLICK",
                            "reason": f"Bot wall detected: {bw}",
                            "screenshot": str(shot_path)
                        }

                # Dismiss cookie banners if present
                for cookie_btn in page.locator("button:has-text('Accept'), button:has-text('Agree'), button:has-text('Allow all')").all():
                    if cookie_btn.is_visible():
                        try:
                            cookie_btn.click()
                            time.sleep(1)
                            break
                        except Exception:
                            pass

                # If on job posting page, click Apply button if needed
                if ats_type == "lever":
                    apply_btn = page.locator("a.postings-btn:has-text('Apply'), a:has-text('Apply for this job')").first
                    if apply_btn.is_visible(timeout=3000):
                        apply_btn.click()
                        time.sleep(2)
                elif ats_type == "greenhouse":
                    apply_link = page.locator("#apply_button, a:has-text('Apply')").first
                    if apply_link.is_visible(timeout=2000):
                        apply_link.click()
                        time.sleep(1)

                # Form filling
                self._fill_ats_form(page, ats_type, resume_pdf)

                preview_path = PROOFS_DIR / f"preview_{track}_{safe_comp}_{job_id}.png"
                page.screenshot(path=str(preview_path))

                if dry_run:
                    browser.close()
                    return {
                        "status": "READY_TO_SUBMIT",
                        "preview_screenshot": str(preview_path),
                        "message": f"Form filled successfully in dry-run mode for {company}."
                    }

                # Submit form
                submitted = self._submit_ats_form(page, ats_type)
                if not submitted:
                    shot_path = PROOFS_DIR / f"unsubmitted_{track}_{safe_comp}_{job_id}.png"
                    page.screenshot(path=str(shot_path))
                    browser.close()
                    self.tracker_db.mark_needs_human_click(job_id, "Submit button not found or click failed", str(shot_path))
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": "Submit button not found",
                        "screenshot": str(shot_path)
                    }

                # Wait for post-submission confirmation
                time.sleep(4)
                final_content = page.content().lower()
                final_url = page.url.lower()

                has_confirmation = any(p in final_content for p in CONFIRMATION_PHRASES) or any(
                    u in final_url for u in ["/thanks", "/thank-you", "/thankyou", "/submitted", "/confirmation", "/received"]
                )

                proof_path = PROOFS_DIR / f"{track}_{safe_comp}_{job_id}.png"
                page.screenshot(path=str(proof_path))
                browser.close()

                if has_confirmation:
                    # Enforce PoS Firewall update
                    self.tracker_db.mark_applied_verified(
                        job_id=job_id,
                        proof_screenshot_path=str(proof_path),
                        submission_url=page.url
                    )
                    return {
                        "status": "APPLIED_VERIFIED",
                        "proof_screenshot_path": str(proof_path),
                        "submission_url": page.url,
                        "company": company,
                        "role": role
                    }
                else:
                    # Confirmation not definitively verified
                    unverified_path = PROOFS_DIR / f"unverified_{track}_{safe_comp}_{job_id}.png"
                    if proof_path.exists():
                        proof_path.rename(unverified_path)
                    self.tracker_db.mark_needs_human_click(job_id, "Form submitted but confirmation text not detected", str(unverified_path))
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": "Post-submission confirmation text unconfirmed",
                        "screenshot": str(unverified_path)
                    }

            except Exception as e:
                err_path = PROOFS_DIR / f"error_{track}_{safe_comp}_{job_id}.png"
                try:
                    page.screenshot(path=str(err_path))
                except Exception:
                    pass
                browser.close()
                self.tracker_db.mark_needs_human_click(job_id, f"Automation exception: {e}", str(err_path))
                return {
                    "status": "NEEDS_HUMAN_CLICK",
                    "reason": f"Exception: {e}",
                    "screenshot": str(err_path)
                }

    def _fill_ats_form(self, page: Page, ats_type: str, resume_path: Path):
        """Fills standard fields across Lever, Greenhouse, Trakstar, Gem, Ashby, Workable."""
        # 1. Name
        self._safe_fill(page, "input[name='name'], input[id*='name']:not([id*='first']):not([id*='last'])", CANDIDATE_DATA["full_name"])
        self._safe_fill(page, "input[name*='first_name'], input[id*='first_name'], input[name*='firstname']", CANDIDATE_DATA["first_name"])
        self._safe_fill(page, "input[name*='last_name'], input[id*='last_name'], input[name*='lastname']", CANDIDATE_DATA["last_name"])

        # 2. Email
        self._safe_fill(page, "input[name='email'], input[type='email'], input[id*='email']", CANDIDATE_DATA["email"])

        # 3. Phone
        self._safe_fill(page, "input[name='phone'], input[type='tel'], input[id*='phone']", CANDIDATE_DATA["phone"])

        # 4. Location / City
        self._safe_fill(page, "input[name*='location'], input[id*='location'], input[name*='city'], input[id*='city']", CANDIDATE_DATA["city"])

        # 5. Organization / Current Company
        self._safe_fill(page, "input[name='org'], input[name*='company'], input[id*='company']", CANDIDATE_DATA["current_company"])

        # 6. URLs (LinkedIn, Portfolio, GitHub/Other)
        self._safe_fill(page, "input[name*='urls[LinkedIn]'], input[name*='linkedin'], input[id*='linkedin']", CANDIDATE_DATA["linkedin"])
        self._safe_fill(page, "input[name*='urls[Portfolio]'], input[name*='portfolio'], input[id*='portfolio'], input[name*='website'], input[id*='website']", CANDIDATE_DATA["portfolio"])
        self._safe_fill(page, "input[name*='urls[Other]'], input[name*='other_url'], input[id*='other_url']", CANDIDATE_DATA["product_lab"])

        # 7. Resume file upload
        file_input = page.locator("input[type='file']").first
        if file_input.is_visible(timeout=3000):
            try:
                file_input.set_input_files(str(resume_path))
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Resume upload error: {e}")

    def _submit_ats_form(self, page: Page, ats_type: str) -> bool:
        """Locates and clicks the primary submit button."""
        submit_selectors = [
            "#btn-submit",
            "button#submit_app",
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit application')",
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
            "button:has-text('Apply Now')",
            "button:has-text('Send Application')"
        ]
        for sel in submit_selectors:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                try:
                    btn.click()
                    return True
                except Exception:
                    pass
        return False

    def _safe_fill(self, page: Page, selector: str, value: str):
        """Fills input if present and not already populated."""
        try:
            loc = page.locator(selector).first
            if loc.is_visible(timeout=1000):
                current = loc.input_value()
                if not current:
                    loc.fill(value)
        except Exception:
            pass


class BrowserCoPilot:
    """Persistent Browser Co-Pilot Mode for Naukri, LinkedIn, and Custom Portals."""

    def __init__(self, profile_dir: Optional[Path] = None, tracker_db: Optional[TrackerDB] = None):
        self.profile_dir = profile_dir or (BASE_DIR / "data" / "browser_profile")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.tracker_db = tracker_db or TrackerDB()

    def launch_copilot(
        self,
        job_id: int,
        job_url: str,
        company: str,
        role: str,
        track: str = "event_mice"
    ) -> Dict[str, Any]:
        """Launches a visible persistent Chrome session with auto-filled fields and terminal prompt."""
        safe_comp = re.sub(r"[^\w-]", "_", company)
        resume_pdf = DirectATSApplier().get_resume_path(track)

        print("\n" + "=" * 80)
        print(f"[CO-PILOT MODE] Launching interactive browser for: {company} - {role}")
        print(f"Target URL: {job_url}")
        print(f"Tailored CV: {resume_pdf.name}")
        print("=" * 80)

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=False,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(job_url, timeout=30000)
                time.sleep(2)

                # Attempt auto-fill on standard questions
                applier = DirectATSApplier()
                applier._fill_ats_form(page, "generic_ats", resume_pdf)

                print("\n[CO-PILOT ACTION REQUIRED]")
                print("1. Review the application in the open browser window.")
                print("2. Solve any CAPTCHA or fill any custom questions if required.")
                print("3. Click 'Submit' when ready.")
                print("-" * 80)

                # Capture proof after user confirms
                user_input = input("Did you successfully submit the application? [y/N]: ").strip().lower()

                if user_input in ("y", "yes"):
                    proof_path = PROOFS_DIR / f"{track}_{safe_comp}_{job_id}.png"
                    page.screenshot(path=str(proof_path))
                    context.close()

                    self.tracker_db.mark_applied_verified(
                        job_id=job_id,
                        proof_screenshot_path=str(proof_path),
                        submission_url=page.url,
                        notes="Submitted via Co-Pilot interactive browser with candidate confirmation."
                    )
                    print(f"SUCCESS: Marked APPLIED_VERIFIED with proof at {proof_path}")
                    return {
                        "status": "APPLIED_VERIFIED",
                        "proof_screenshot_path": str(proof_path),
                        "submission_url": page.url
                    }
                else:
                    context.close()
                    shot_path = PROOFS_DIR / f"copilot_skipped_{track}_{safe_comp}_{job_id}.png"
                    self.tracker_db.mark_needs_human_click(
                        job_id,
                        "Co-Pilot session paused or skipped by user without submission",
                        str(shot_path)
                    )
                    print("SKIPPED: Job logged as NEEDS_HUMAN_CLICK without faking applied status.")
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": "User skipped or cancelled submission"
                    }

            except Exception as e:
                context.close()
                self.tracker_db.mark_needs_human_click(job_id, f"Co-Pilot browser error: {e}")
                return {
                    "status": "NEEDS_HUMAN_CLICK",
                    "reason": str(e)
                }
