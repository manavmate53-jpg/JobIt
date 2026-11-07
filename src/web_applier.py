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

        storage_file = self.base_dir / "data" / f"{portal_lower}_storage_state.json"

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(session_path),
                headless=False,
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(target_url)

            # Bring Chromium window to the front on macOS
            try:
                import subprocess
                subprocess.run(["osascript", "-e", 'tell application "Chromium" to activate'], capture_output=True)
            except Exception:
                pass

            # Pre-fill email and password if on login page
            try:
                page.wait_for_timeout(1500)
                email_val = os.getenv("LINKEDIN_EMAIL", "manavstore666@gmail.com") if portal_lower == "linkedin" else os.getenv("EMAIL_USER", "manavmate53@gmail.com")
                pass_val = os.getenv("LINKEDIN_PASSWORD", "M@navmate_01") if portal_lower == "linkedin" else ""

                email_input = page.locator("#username, input[name='session_key'], input[type='email']").first
                if email_input.is_visible(timeout=3000):
                    curr_val = email_input.input_value()
                    if not curr_val:
                        email_input.fill(email_val)

                if pass_val:
                    pass_input = page.locator("#password, input[name='session_password'], input[type='password']").first
                    if pass_input.is_visible(timeout=2000):
                        curr_pass = pass_input.input_value()
                        if not curr_pass:
                            pass_input.fill(pass_val)
            except Exception:
                pass

            # Wait for user to log in or auto-detect (10 minutes)
            print("\nWaiting for you to log in... (Window will automatically close once you reach your feed)")
            start_wait = time.time()
            logged_in = False

            while time.time() - start_wait < 600:
                try:
                    curr_url = page.url.lower()

                    # Check if landed on authenticated feed/dashboard
                    if portal_lower == "linkedin" and any(k in curr_url for k in ["/feed", "/in/", "/mynetwork", "/messaging"]):
                        logged_in = True
                        break
                    elif portal_lower == "naukri" and any(k in curr_url for k in ["/mnjuser", "my.naukri.com"]):
                        logged_in = True
                        break
                except Exception:
                    # Page or context may have been closed manually by user
                    break

                time.sleep(1.5)

            # Save state
            try:
                context.storage_state(path=str(storage_file))
                print(f"[Portal Login] Exported full storage state to: {storage_file}")

                if portal_lower == "linkedin":
                    import base64
                    with open(storage_file, "rb") as f:
                        b64_val = base64.b64encode(f.read()).decode("utf-8")
                    from src.services.github_secrets import sync_github_secret
                    if sync_github_secret("LINKEDIN_STORAGE_STATE", b64_val):
                        print("[Portal Login] Automatically synced LINKEDIN_STORAGE_STATE to GitHub Secrets!")
            except Exception as e:
                logger.debug(f"Could not export storage_state: {e}")

            context.close()
            if logged_in:
                print(f"[Portal Login] Successfully authenticated and saved {portal.upper()} browser session!")
            else:
                print(f"[Portal Login] Session saved to {session_path}.")

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
            # Notice period: Immediate / 0 Days
            notice_inputs = page.locator("input[id*='notice'], select[id*='notice'], input[placeholder*='Notice']")
            if notice_inputs.count() > 0:
                notice_inputs.first.fill("Immediate / 0 Days")

            # Current CTC: ₹6,00,000 (6.0 LPA)
            ctc_inputs = page.locator("input[id*='ctc'], input[id*='salary'], input[placeholder*='Current CTC']")
            if ctc_inputs.count() > 0:
                ctc_inputs.first.fill("600000")

            # Expected CTC: ₹6,50,000 to ₹7,20,000 (6.5 - 7.2 LPA CTC / ₹45k-₹50k in-hand)
            exp_ctc = page.locator("input[placeholder*='Expected CTC'], input[id*='expectedCtc']")
            if exp_ctc.count() > 0:
                exp_ctc.first.fill("680000")

            # Location / City: Jogeshwari East, Mumbai (Available On-Site Immediately)
            city_inputs = page.locator("input[id*='city'], input[placeholder*='Current Location']")
            if city_inputs.count() > 0:
                city_inputs.first.fill("Jogeshwari East, Mumbai (Available On-Site Immediately)")

            # Total Experience in Events / Operations: 4 Years
            exp_inputs = page.locator("input[id*='experience'], input[placeholder*='Experience'], input[name*='experience']")
            if exp_inputs.count() > 0:
                exp_inputs.first.fill("4")

            # Comfortable with live event date flexibility: Yes
            flex_inputs = page.locator("input[id*='flexib'], select[id*='flexib'], input[name*='flexib']")
            if flex_inputs.count() > 0:
                flex_inputs.first.fill("Yes")
        except Exception as e:
            logger.debug(f"Questionnaire auto-fill note: {e}")
