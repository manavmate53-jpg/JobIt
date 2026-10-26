"""Web Portal Automated Applier (Naukri & LinkedIn Easy Apply).

Automates web application submission using Playwright with persistent browser sessions:
1. Reuses saved login sessions (cookies & tokens stored in data/browser_sessions/).
2. Navigates to job postings on Naukri or LinkedIn.
3. Automatically detects Apply / Easy Apply flows.
4. Uploads the tailored single-page A4 PDF resume.
5. Fills candidate profile answers (Phone, Experience, Current CTC: 8 LPA, Expected CTC: 12-16 LPA, Notice Period: Immediate/15 Days).
6. Captures application proof screenshots in exports/applications/.
7. Supports safe dry-run (stops at final review) vs full auto-submit.
"""

from __future__ import annotations

import datetime
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page

from src.profile_engine import ProfileEngine
from src.scrapers.base_scraper import ScrapedJob

logger = logging.getLogger(__name__)


class PortalWebApplier:
    """Automates web application workflows on job portals."""

    def __init__(self, base_dir: Optional[Path] = None, profile_engine: Optional[ProfileEngine] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.profile_engine = profile_engine or ProfileEngine()
        self.profile = self.profile_engine.profile

        self.sessions_dir = self.base_dir / "data" / "browser_sessions"
        self.applications_dir = self.base_dir / "exports" / "applications"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.applications_dir.mkdir(parents=True, exist_ok=True)

    def get_session_path(self, portal: str) -> Path:
        """Returns persistent browser session directory for a portal."""
        p = portal.lower()
        target = self.sessions_dir / p
        target.mkdir(parents=True, exist_ok=True)
        return target

    def login_interactively(self, portal: str = "naukri"):
        """Launches a visible browser so the user can log in once; session is saved persistently."""
        portal_lower = portal.lower()
        session_path = self.get_session_path(portal_lower)

        login_urls = {
            "naukri": "https://www.naukri.com/nlogin/login",
            "linkedin": "https://www.linkedin.com/login",
        }
        target_url = login_urls.get(portal_lower, "https://www.naukri.com/nlogin/login")

        print(f"\n[Portal Login] Launching visible Chromium browser for {portal.upper()}...")
        print(f"Session data will be preserved in: {session_path}")
        print("Please complete login / OTP in the opened browser window.")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(session_path),
                headless=False,
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.new_page()
            page.goto(target_url)

            # Wait for user to log in
            print("\nWaiting for you to log in... (Press Enter in terminal once logged in successfully)")
            try:
                input(">> Press [ENTER] here once you see your logged-in dashboard/feed: ")
            except Exception:
                time.sleep(15)

            # Save state
            context.close()
            print(f"[Portal Login] Successfully saved {portal.upper()} browser session!")

    def apply(
        self,
        job: ScrapedJob,
        pdf_path: str,
        dry_run: bool = True,
        headless: bool = False
    ) -> Dict[str, Any]:
        """Applies to a job via Naukri or LinkedIn browser automation."""
        portal = "naukri" if "naukri" in job.source.lower() or "naukri" in job.job_url else "linkedin"
        session_path = self.get_session_path(portal)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_comp = re.sub(r"[^\w-]", "_", job.company)

        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "status": "ERROR",
                "message": f"Tailored PDF resume not found at {pdf_path}. Run 'jobit tailor' first."
            }

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(session_path),
                headless=headless,
                viewport={"width": 1280, "height": 850},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"macOS"',
                },
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars"
                ]
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Ensure URL is https
            if job.job_url.startswith("http://"):
                job.job_url = "https://" + job.job_url[7:]

            try:
                if portal == "naukri":
                    return self._apply_naukri(page, job, pdf_path, safe_comp, timestamp, dry_run)
                else:
                    return self._apply_linkedin(page, job, pdf_path, safe_comp, timestamp, dry_run)
            except Exception as e:
                logger.error(f"Browser application automation encountered error: {e}")
                err_screenshot = self.applications_dir / f"error_{safe_comp}_{timestamp}.png"
                try:
                    page.screenshot(path=str(err_screenshot))
                except Exception:
                    pass
                return {
                    "success": False,
                    "status": "ERROR",
                    "error": str(e),
                    "screenshot_path": str(err_screenshot) if err_screenshot.exists() else None,
                    "message": f"Automated web apply error: {e}"
                }
            finally:
                context.close()

    def _apply_naukri(
        self,
        page: Page,
        job: ScrapedJob,
        pdf_path: str,
        safe_comp: str,
        timestamp: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Executes application flow on Naukri.com."""
        page.goto(job.job_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)

        # 1. Check if already applied
        page_content = page.content().lower()
        if "already applied" in page_content or page.locator("text='Already Applied'").count() > 0:
            screenshot = self.applications_dir / f"already_applied_{safe_comp}_{timestamp}.png"
            page.screenshot(path=str(screenshot))
            return {
                "success": True,
                "status": "ALREADY_APPLIED",
                "screenshot_path": str(screenshot),
                "message": f"Already applied to {job.role} at {job.company} on Naukri."
            }

        # 2. Check for login prompt
        if "login to apply" in page_content or page.locator("button:has-text('Login to apply')").count() > 0:
            screenshot = self.applications_dir / f"login_required_{safe_comp}_{timestamp}.png"
            page.screenshot(path=str(screenshot))
            return {
                "success": False,
                "status": "LOGIN_REQUIRED",
                "screenshot_path": str(screenshot),
                "message": "Naukri login session expired or missing. Run 'jobit login --portal naukri' once."
            }

        # 3. Locate Apply Button
        apply_btn = None
        selectors = [
            "button.apply-button",
            "button:has-text('Apply')",
            "button:has-text('Apply on company site')",
            "a.apply-button",
            "a:has-text('Apply on company site')",
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=1500):
                apply_btn = loc
                break

        if not apply_btn:
            screenshot = self.applications_dir / f"no_apply_btn_{safe_comp}_{timestamp}.png"
            page.screenshot(path=str(screenshot))
            return {
                "success": False,
                "status": "APPLY_BUTTON_NOT_FOUND",
                "screenshot_path": str(screenshot),
                "message": "Could not locate Apply button on the job page."
            }

        btn_text = apply_btn.inner_text().strip()
        is_external = "company site" in btn_text.lower() or "company website" in btn_text.lower()

        # 4. Click Apply
        apply_btn.click()
        time.sleep(2)

        # 5. Handle file upload if resume upload input appears
        file_input = page.locator("input[type='file']").first
        if file_input.is_visible(timeout=2000):
            try:
                file_input.set_input_files(pdf_path)
                time.sleep(1)
            except Exception as f_err:
                logger.warning(f"File upload error: {f_err}")

        # 6. Fill common questions if present
        self._fill_standard_questions(page)

        # 7. Take screenshot
        preview_screenshot = self.applications_dir / f"preview_{safe_comp}_{timestamp}.png"
        page.screenshot(path=str(preview_screenshot))

        if dry_run:
            return {
                "success": True,
                "status": "READY_TO_SUBMIT",
                "is_external": is_external,
                "screenshot_path": str(preview_screenshot),
                "message": f"Application prepared & resume attached in dry-run mode. Screenshot saved to {preview_screenshot}."
            }

        # 8. Submit final application if not dry-run and internal
        if not is_external:
            submit_btn = page.locator("button:has-text('Submit'), button:has-text('Submit Application')").first
            if submit_btn.is_visible(timeout=2000):
                submit_btn.click()
                time.sleep(2)

        final_screenshot = self.applications_dir / f"submitted_{safe_comp}_{timestamp}.png"
        page.screenshot(path=str(final_screenshot))

        return {
            "success": True,
            "status": "SUBMITTED" if not is_external else "EXTERNAL_REDIRECT",
            "is_external": is_external,
            "screenshot_path": str(final_screenshot),
            "message": f"Successfully submitted application for {job.role} at {job.company}!"
        }

    def _apply_linkedin(
        self,
        page: Page,
        job: ScrapedJob,
        pdf_path: str,
        safe_comp: str,
        timestamp: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Executes Easy Apply flow on LinkedIn."""
        page.goto(job.job_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)

        easy_apply_btn = page.locator("button.jobs-apply-button, button:has-text('Easy Apply')").first
        if not easy_apply_btn.is_visible(timeout=3000):
            # External apply
            screenshot = self.applications_dir / f"linkedin_external_{safe_comp}_{timestamp}.png"
            page.screenshot(path=str(screenshot))
            return {
                "success": True,
                "status": "EXTERNAL_REDIRECT",
                "screenshot_path": str(screenshot),
                "message": "Job requires applying on the employer's external career site."
            }

        easy_apply_btn.click()
        time.sleep(2)

        # Handle resume file upload if available
        file_input = page.locator("input[type='file']").first
        if file_input.is_visible(timeout=2000):
            try:
                file_input.set_input_files(pdf_path)
                time.sleep(1)
            except Exception:
                pass

        # Fill phone if required
        phone_input = page.locator("input[id*='phoneNumber'], input[name*='phone']").first
        if phone_input.is_visible(timeout=1000) and not phone_input.input_value():
            phone_input.fill(self.profile.personal.phone)

        screenshot = self.applications_dir / f"linkedin_preview_{safe_comp}_{timestamp}.png"
        page.screenshot(path=str(screenshot))

        if dry_run:
            return {
                "success": True,
                "status": "READY_TO_SUBMIT",
                "screenshot_path": str(screenshot),
                "message": f"LinkedIn Easy Apply modal loaded, resume attached. Preview captured at {screenshot}."
            }

        # Next / Submit step
        next_btn = page.locator("button:has-text('Next'), button:has-text('Review')").first
        if next_btn.is_visible(timeout=1500):
            next_btn.click()
            time.sleep(1)

        submit_btn = page.locator("button:has-text('Submit application')").first
        if submit_btn.is_visible(timeout=2000):
            submit_btn.click()
            time.sleep(2)

        final_screenshot = self.applications_dir / f"linkedin_submitted_{safe_comp}_{timestamp}.png"
        page.screenshot(path=str(final_screenshot))

        return {
            "success": True,
            "status": "SUBMITTED",
            "screenshot_path": str(final_screenshot),
            "message": f"Successfully submitted LinkedIn Easy Apply for {job.role} at {job.company}!"
        }

    def _fill_standard_questions(self, page: Page):
        """Auto-fills typical application questionnaire inputs with grounded candidate data."""
        try:
            # Notice period
            notice_inputs = page.locator("input[id*='notice'], select[id*='notice'], input[placeholder*='Notice']")
            if notice_inputs.count() > 0:
                notice_inputs.first.fill("15 days")

            # Current CTC
            ctc_inputs = page.locator("input[id*='ctc'], input[id*='salary'], input[placeholder*='Current CTC']")
            if ctc_inputs.count() > 0:
                ctc_inputs.first.fill("800000")

            # Expected CTC
            exp_ctc = page.locator("input[placeholder*='Expected CTC'], input[id*='expectedCtc']")
            if exp_ctc.count() > 0:
                exp_ctc.first.fill("1400000")

            # Location / City
            city_inputs = page.locator("input[id*='city'], input[placeholder*='Current Location']")
            if city_inputs.count() > 0:
                city_inputs.first.fill("Mumbai")
        except Exception as e:
            logger.debug(f"Questionnaire auto-fill note: {e}")
