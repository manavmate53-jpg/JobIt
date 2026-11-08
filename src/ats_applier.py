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
    "location": "Jogeshwari East, Mumbai, Maharashtra, India",
    "address": "Jogeshwari East, Mumbai, Maharashtra, India",
    "city": "Mumbai",
    "state": "Maharashtra",
    "country": "India",
    "linkedin": "https://www.linkedin.com/in/manav-mate-9448b1341/",
    "portfolio": "https://manavmate53-jpg.github.io/portfolio/#hero",
    "product_lab": "https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering",
    "current_company": "NeoManpower / HireFlo",
    "current_title": "Product & Operations Lead",
    "experience_years": "4",
    "notice_period": "Immediate / 0 Days",
    "notice_period_days": "0",
    "current_ctc": "6.0 LPA",
    "current_ctc_numeric": "600000",
    "expected_ctc": "6.5 - 7.2 LPA (₹45,000 - ₹50,000 in-hand)",
    "expected_ctc_numeric": "700000"
}

TRACK_RESUMES = {
    "event_mice": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
    "founders_office": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Founders_Office_CV.pdf",
    "prod_ops": BASE_DIR / "exports" / "resumes" / "Manav_Mate_ProdOps_CV.pdf",
    "apm": BASE_DIR / "exports" / "resumes" / "Manav_Mate_APM_CV.pdf",
}

class SubmissionIncompleteError(Exception):
    """Raised when an application is claimed to be submitted but pre-apply or unsubmitted elements remain visible."""
    pass


UNSUBMITTED_BLACKLIST_MARKERS = [
    "apply now",
    "apply on company site",
    "apply with your resume",
    "job details",
    "full job description",
    "review your application",
    "submit your application",
]

SUBMIT_BUTTON_SELECTORS = [
    "button:has-text('Apply now')",
    "button:has-text('Apply on company site')",
    "button:has-text('Apply')",
    "button:has-text('Submit your application')",
    "button:has-text('Submit application')",
    "button:has-text('Submit Application')",
    "button:has-text('Submit')",
    "button#submit_app",
    "input[type='submit']",
    "a:has-text('Apply now')",
    "a:has-text('Apply on company site')",
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


def verify_confirmation_screen(page: Any, ats_type: str = "generic", raise_on_failure: bool = False) -> Tuple[bool, str]:
    """Strictly validates that the page is genuinely a post-submission confirmation screen.
    Returns (is_verified: bool, reason: str).
    Rules:
    1. Blacklist check: If any pre-apply or in-progress marker is visible, strictly forbid verification.
    2. Button check: If an apply or submit button is still visible and clickable, reject.
    3. Mandatory Positive Confirmation: Requires explicit post-submission tokens per portal.
    """
    url = getattr(page, "url", "")
    if callable(url):
        url = url()
    url_lower = str(url).lower()

    content = ""
    if hasattr(page, "content"):
        content = page.content() if callable(page.content) else page.content
    content_lower = str(content).lower()

    # Rule 1: Blacklist False Confirmation Markers
    for marker in UNSUBMITTED_BLACKLIST_MARKERS:
        marker_found = False
        if hasattr(page, "locator") and callable(page.locator):
            try:
                loc = page.locator(f"text='{marker}'").first
                if loc.is_visible(timeout=300):
                    marker_found = True
            except Exception:
                pass
        if not marker_found and marker in content_lower:
            if not hasattr(page, "locator") or not callable(page.locator):
                marker_found = True

        if marker_found:
            reason = f"Pre-apply blacklist marker visible: '{marker}' (application not submitted)"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason

    # Rule 2: Two-Step Check for Visible Submit/Apply Buttons
    for sel in SUBMIT_BUTTON_SELECTORS:
        btn_txt = None
        if hasattr(page, "locator") and callable(page.locator):
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=300) and btn.is_enabled(timeout=300):
                    txt = btn.inner_text().strip().lower()
                    if any(w in txt for w in ["apply", "submit"]):
                        btn_txt = txt
            except Exception:
                pass

        if btn_txt:
            reason = f"Submit/Apply button still visible and clickable: '{btn_txt}'"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason

    # Rule 3: Mandatory Platform-Specific Positive Confirmation Markers
    if "indeed.com" in url_lower:
        indeed_tokens = [
            "your application has been submitted",
            "your application was sent to",
            "your application has been sent",
            "application submitted",
        ]
        has_positive = any(t in content_lower for t in indeed_tokens) or "/post-apply" in url_lower
        if not has_positive:
            reason = "Indeed submission incomplete: Missing 'Your application has been submitted / sent' or '/post-apply' URL"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Indeed post-submission confirmation verified"

    elif "lever.co" in url_lower:
        has_positive = "/thanks" in url_lower or "thank you for applying" in content_lower
        if not has_positive:
            reason = "Lever submission incomplete: Missing '/thanks' URL or 'Thank you for applying' confirmation text"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Lever post-submission confirmation verified"

    elif "greenhouse.io" in url_lower:
        has_positive = "/confirmation" in url_lower or "application submitted!" in content_lower or "thank you for applying" in content_lower
        if not has_positive:
            reason = "Greenhouse submission incomplete: Missing '/confirmation' URL or 'Application submitted!' text"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Greenhouse post-submission confirmation verified"

    elif "jobvite.com" in url_lower:
        has_positive = "thank you for your interest" in content_lower or "your application has been successfully submitted" in content_lower or "application submitted" in content_lower
        if not has_positive:
            reason = "Jobvite submission incomplete: Missing 'successfully submitted' or 'Thank you for your interest' confirmation text"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Jobvite post-submission confirmation verified"

    elif "linkedin.com" in url_lower:
        has_positive = "application sent" in content_lower or "your application was sent" in content_lower
        if not has_positive:
            reason = "LinkedIn submission incomplete: Missing 'Application sent' confirmation modal"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "LinkedIn post-submission confirmation verified"

    elif "naukri.com" in url_lower:
        has_positive = "successfully applied" in content_lower or "you have successfully applied" in content_lower
        if not has_positive:
            reason = "Naukri submission incomplete: Missing 'Successfully applied' confirmation banner"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Naukri post-submission confirmation verified"

    elif "wellfound.com" in url_lower or "angel.co" in url_lower:
        has_positive = "application sent" in content_lower or "applied" in url_lower
        if not has_positive:
            reason = "Wellfound submission incomplete: Missing application confirmation"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Wellfound post-submission confirmation verified"

    else:
        # Generic ATS: Check for URL confirmation or explicit success header
        generic_confirm_tokens = [
            "your application has been submitted",
            "thank you for applying",
            "application submitted successfully",
            "we have received your application",
            "application complete",
        ]
        has_positive = any(t in content_lower for t in generic_confirm_tokens) or any(
            u in url_lower for u in ["/thanks", "/thank-you", "/thankyou", "/confirmation", "/submitted"]
        )
        if not has_positive:
            reason = "Generic ATS submission incomplete: No explicit confirmation header or success URL detected"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Generic ATS post-submission confirmation verified"


def assert_confirmation_screen(page: Any, ats_type: str = "generic") -> Tuple[bool, str]:
    """Strictly asserts confirmation screen. Raises SubmissionIncompleteError on any failure."""
    return verify_confirmation_screen(page, ats_type=ats_type, raise_on_failure=True)


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
                is_verified, reason = verify_confirmation_screen(page, ats_type=ats_type)

                if is_verified:
                    proof_path = PROOFS_DIR / f"{track}_{safe_comp}_{job_id}_SUCCESS.png"
                    page.screenshot(path=str(proof_path))
                    submission_url = page.url
                    browser.close()

                    self.tracker_db.mark_applied_verified(
                        job_id=job_id,
                        proof_screenshot_path=str(proof_path),
                        submission_url=submission_url,
                        notes=f"Submitted via Direct ATS Applier ({ats_type}): {reason}"
                    )
                    return {
                        "status": "APPLIED_VERIFIED",
                        "proof_screenshot_path": str(proof_path),
                        "submission_url": submission_url,
                        "company": company,
                        "role": role,
                        "reason": reason
                    }
                else:
                    unverified_path = PROOFS_DIR / f"unverified_{track}_{safe_comp}_{job_id}.png"
                    page.screenshot(path=str(unverified_path))
                    browser.close()
                    self.tracker_db.mark_needs_human_click(
                        job_id,
                        f"Post-submission confirmation failed: {reason}",
                        str(unverified_path)
                    )
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": f"Post-submission confirmation unconfirmed: {reason}",
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

        # 4. Location / Address / City
        self._safe_fill(page, "input[name*='address'], input[id*='address']", CANDIDATE_DATA["location"])
        self._safe_fill(page, "input[name*='location'], input[id*='location']", CANDIDATE_DATA["location"])
        self._safe_fill(page, "input[name*='city'], input[id*='city']", CANDIDATE_DATA["city"])

        # 5. Organization / Current Company
        self._safe_fill(page, "input[name='org'], input[name*='company'], input[id*='company']", CANDIDATE_DATA["current_company"])

        # 6. Experience, CTC & Notice Period
        self._safe_fill(page, "input[name*='experience'], input[id*='experience']", CANDIDATE_DATA["experience_years"])
        self._safe_fill(page, "input[name*='notice'], input[id*='notice']", CANDIDATE_DATA["notice_period"])
        self._safe_fill(page, "input[name*='current_ctc'], input[id*='current_ctc'], input[name*='current_salary']", CANDIDATE_DATA["current_ctc"])
        self._safe_fill(page, "input[name*='expected_ctc'], input[id*='expected_ctc'], input[name*='expected_salary']", CANDIDATE_DATA["expected_ctc"])

        # 7. URLs (LinkedIn, Portfolio, GitHub/Other)
        self._safe_fill(page, "input[name*='urls[LinkedIn]'], input[name*='linkedin'], input[id*='linkedin']", CANDIDATE_DATA["linkedin"])
        self._safe_fill(page, "input[name*='urls[Portfolio]'], input[name*='portfolio'], input[id*='portfolio'], input[name*='website'], input[id*='website']", CANDIDATE_DATA["portfolio"])
        self._safe_fill(page, "input[name*='urls[Other]'], input[name*='other_url'], input[id*='other_url']", CANDIDATE_DATA["product_lab"])

        # 8. Resume file upload
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

    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        tracker_db: Optional[TrackerDB] = None,
        telemetry_db: Optional[TelemetryDB] = None
    ):
        self.profile_dir = profile_dir or (BASE_DIR / "data" / "browser_profile")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.tracker_db = tracker_db or TrackerDB()
        self.telemetry_db = telemetry_db or TelemetryDB()

    def launch_copilot(
        self,
        job_id: int,
        job_url: str,
        company: str,
        role: str,
        track: str = "event_mice"
    ) -> Dict[str, Any]:
        """Launches a visible persistent Chrome session with auto-filled fields and terminal prompt."""
        import select
        import sys

        safe_comp = re.sub(r"[^\w-]", "_", company)
        resume_pdf = DirectATSApplier().get_resume_path(track)

        print("\n" + "=" * 80)
        print(f"[CO-PILOT MODE] Launching interactive browser for: {company} - {role}")
        print(f"Target URL: {job_url}")
        print(f"Tailored CV: {resume_pdf.name}")
        print("=" * 80)

        headless_mode = os.getenv("COPILOT_HEADLESS", "false").lower() in ("true", "1")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=headless_mode,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(job_url, timeout=30000)
                time.sleep(2)

                # Auto-open application modal/form if on job posting page
                try:
                    if "indeed.com" in page.url.lower():
                        indeed_apply = page.locator("#indeedApplyButton, button:has-text('Apply now'), a:has-text('Apply now')").first
                        if indeed_apply.is_visible(timeout=3000):
                            indeed_apply.click()
                            time.sleep(2)
                    elif "jobvite.com" in page.url.lower() and "/apply" not in page.url.lower():
                        jv_apply = page.locator("a:has-text('Apply')").first
                        if jv_apply.is_visible(timeout=3000):
                            jv_apply.click()
                            time.sleep(2)
                    elif "linkedin.com" in page.url.lower():
                        li_apply = page.locator("button.jobs-apply-button, button:has-text('Easy Apply')").first
                        if li_apply.is_visible(timeout=3000):
                            li_apply.click()
                            time.sleep(2)
                    elif "naukri.com" in page.url.lower():
                        naukri_apply = page.locator("button:has-text('Apply'), a:has-text('Apply')").first
                        if naukri_apply.is_visible(timeout=3000):
                            naukri_apply.click()
                            time.sleep(2)
                except Exception:
                    pass

                # Attempt auto-fill on standard questions
                applier = DirectATSApplier()
                applier._fill_ats_form(page, "generic_ats", resume_pdf)

                # Activate window on macOS if interactive
                try:
                    import subprocess
                    subprocess.run(["osascript", "-e", 'tell application "Chromium" to activate'], capture_output=True)
                except Exception:
                    pass

                box_msg = (
                    f"\n" + "=" * 70 + "\n"
                    f"CO-PILOT READY: {company} - {role}\n"
                    f"1. Check the opened browser window.\n"
                    f"2. Answer any company-specific questions or complete CAPTCHA if prompted.\n"
                    f"3. Click the final 'Submit Application' button on the website.\n"
                    f"4. Once the confirmation screen ('Thank you / Application Sent') loads, press ENTER here.\n"
                    + "=" * 70 + "\n"
                )
                print(box_msg)

                # Wait for user submission or confirmation screen detection
                max_wait = int(os.getenv("COPILOT_WAIT_TIMEOUT", "45"))
                start_time = time.time()
                is_verified = False
                reason = "Timed out waiting for submission confirmation"

                while time.time() - start_time < max_wait:
                    ver, r = verify_confirmation_screen(page)
                    if ver:
                        is_verified = True
                        reason = r
                        break

                    try:
                        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                            sys.stdin.readline()
                            time.sleep(1.5)
                            is_verified, reason = verify_confirmation_screen(page)
                            break
                    except Exception:
                        pass

                    time.sleep(1.5)

                if not is_verified and time.time() - start_time >= max_wait:
                    is_verified, reason = verify_confirmation_screen(page)

                if is_verified:
                    proof_path = PROOFS_DIR / f"{track}_{safe_comp}_{job_id}_SUCCESS.png"
                    page.screenshot(path=str(proof_path))
                    submission_url = page.url
                    context.close()

                    self.tracker_db.mark_applied_verified(
                        job_id=job_id,
                        proof_screenshot_path=str(proof_path),
                        submission_url=submission_url,
                        notes=f"Submitted via Co-Pilot interactive browser: {reason}"
                    )

                    # Also update telemetry_db if opportunity exists
                    try:
                        with self.telemetry_db._get_connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT id FROM opportunities WHERE company_name LIKE ?", (f"%{company}%",))
                            row = cur.fetchone()
                            if row:
                                self.telemetry_db.mark_applied_verified(
                                    opportunity_id=row["id"],
                                    proof_screenshot_path=str(proof_path),
                                    submission_url=submission_url,
                                    notes=f"Submitted via Co-Pilot interactive browser: {reason}"
                                )
                    except Exception as e:
                        logger.warning(f"Failed to update telemetry_db for {company}: {e}")

                    print(f"\n[SUCCESS] Verified submission captured for {company}.")
                    print(f"Proof screenshot captured: {proof_path}")
                    return {
                        "status": "APPLIED_VERIFIED",
                        "proof_screenshot_path": str(proof_path),
                        "submission_url": submission_url,
                        "reason": reason
                    }
                else:
                    rejected_path = PROOFS_DIR / f"copilot_rejected_{job_id}.png"
                    try:
                        page.screenshot(path=str(rejected_path))
                    except Exception:
                        pass
                    context.close()

                    self.tracker_db.mark_needs_human_click(
                        job_id,
                        f"Co-Pilot confirmation check failed: {reason}",
                        str(rejected_path)
                    )
                    print(f"\n\033[91m[REJECTED] Confirmation check failed. Screen still shows unsubmitted state.\033[0m")
                    print(f"Details: {reason}")
                    print(f"State screenshot captured: {rejected_path}")
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": f"Confirmation check failed: {reason}",
                        "screenshot": str(rejected_path)
                    }

            except Exception as e:
                context.close()
                self.tracker_db.mark_needs_human_click(job_id, f"Co-Pilot browser error: {e}")
                return {
                    "status": "NEEDS_HUMAN_CLICK",
                    "reason": str(e)
                }

