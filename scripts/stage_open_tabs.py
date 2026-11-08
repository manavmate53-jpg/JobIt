#!/usr/bin/env python3
"""Stage Open Tabs for Interactive Co-Pilot Applications.

Launches a persistent, detached Chrome session with --remote-debugging-port=9222.
Opens 5 priority target jobs in separate tabs, clicks initial Apply buttons,
pre-fills standard candidate information, and attaches tailored PDF resumes.
Leaves the browser completely detached and running on the user's desktop so the
user can review and submit manually.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stage_open_tabs")

CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
PROFILE_DIR = BASE_DIR / "data" / "browser_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_DATA = {
    "full_name": "Manav Mate",
    "first_name": "Manav",
    "last_name": "Mate",
    "email": "manavmate53@gmail.com",
    "phone": "+91 85915 95889",
    "phone_clean": "8591595889",
    "location": "Mumbai, Maharashtra, India",
    "address": "Jogeshwari East, Mumbai, Maharashtra, India",
    "city": "Mumbai",
    "state": "Maharashtra",
    "country": "India",
    "linkedin": "https://www.linkedin.com/in/manav-mate-9448b1341/",
    "portfolio": "https://manavmate53-jpg.github.io/portfolio/#hero",
    "product_lab": "https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering",
    "experience_years": "4",
    "notice_period": "Immediate / 0 Days",
    "current_ctc": "6.0 LPA",
    "current_ctc_numeric": "600000",
    "expected_ctc": "6.5 - 7.2 LPA (₹45,000 - ₹50,000 in-hand)",
    "expected_ctc_numeric": "700000",
}

TARGET_JOBS = [
    {
        "id": 647,
        "company": "Euro Panel Products Ltd",
        "role": "Events Executive (Display & Events)",
        "track": "event_mice",
        "url": "https://in.indeed.com/viewjob?jk=2051dab3e8356d40",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Indeed",
    },
    {
        "id": 616,
        "company": "WebMD",
        "role": "Associate Product Marketing Manager",
        "track": "apm",
        "url": "https://jobs.jobvite.com/webmd/job/oH8YAfw7?isComingFromApp=true",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_APM_CV.pdf",
        "portal": "Jobvite",
    },
    {
        "id": 643,
        "company": "Red Bull",
        "role": "On Premise Festival & Events Manager",
        "track": "event_mice",
        "url": "https://www.linkedin.com/jobs/view/4479837751/",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "LinkedIn",
    },
    {
        "id": 638,
        "company": "Torqwars",
        "role": "Events Lead",
        "track": "event_mice",
        "url": "https://www.naukri.com/job-listings-events-lead-torqwars-mumbai-3-to-7-years-071026029016?src=jobsearchDesk&sid=17940788904325118&xp=19&px=1&nignbevent_src=jobsearchDeskGNB",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Naukri",
    },
    {
        "id": 179,
        "company": "Dukaan",
        "role": "Associate Product Manager - B2B Commerce & Catalog AI",
        "track": "apm",
        "url": "https://wellfound.com/jobs/dukaan-apm-b2b-commerce-catalog-849306",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_APM_CV.pdf",
        "portal": "Wellfound",
    },
]


def is_cdp_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_chrome_running() -> str:
    """Finds Chrome and launches it detached on port 9222 if not already running."""
    if is_cdp_ready():
        logger.info(f"Connected to existing Chrome session on {CDP_URL}")
        return "existing"

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Users/manav/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    ]

    chrome_bin = None
    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            chrome_bin = cand
            break

    if not chrome_bin:
        raise RuntimeError("No compatible Chrome or Chromium binary found on this system.")

    logger.info(f"Spawning detached Chrome browser: {chrome_bin}")
    cmd = [
        chrome_bin,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Wait for CDP endpoint to respond
    for _ in range(15):
        time.sleep(1)
        if is_cdp_ready():
            logger.info("Chrome remote debugging port is ready.")
            break
    else:
        raise TimeoutError("Timed out waiting for Chrome remote debugging port 9222.")

    # Bring Chrome window to front on macOS
    try:
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'], capture_output=True)
    except Exception:
        pass

    return "spawned"


def prefill_tab(page, target: Dict[str, Any]):
    """Attempts initial apply clicks and fills standard candidate fields."""
    job_id = target["id"]
    company = target["company"]
    url = target["url"]
    resume_path = target["resume"]

    logger.info(f"Loading Job #{job_id}: {company} | URL: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        logger.warning(f"Page goto timeout/warning for {company}: {e}")

    time.sleep(2)

    # 1. Click initial apply button if visible
    url_lower = page.url.lower()
    try:
        if "indeed.com" in url_lower:
            btn = page.locator("#indeedApplyButton, button:has-text('Apply now'), a:has-text('Apply now')").first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(2)
        elif "jobvite.com" in url_lower and "/apply" not in url_lower:
            btn = page.locator("a:has-text('Apply')").first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(2)
        elif "linkedin.com" in url_lower:
            btn = page.locator("button.jobs-apply-button, button:has-text('Easy Apply'), button:has-text('Apply')").first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(2)
        elif "naukri.com" in url_lower:
            btn = page.locator("button:has-text('Apply'), a:has-text('Apply')").first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(2)
        elif "wellfound.com" in url_lower or "angel.co" in url_lower:
            btn = page.locator("button:has-text('Apply'), a:has-text('Apply')").first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(2)
    except Exception as e:
        logger.debug(f"Initial apply button click passed: {e}")

    # Helper for safe filling
    def safe_fill(container, selector: str, value: str):
        try:
            loc = container.locator(selector).first
            if loc.is_visible(timeout=1000):
                curr = loc.input_value()
                if not curr:
                    loc.fill(str(value))
        except Exception:
            pass

    containers = [page]
    try:
        containers.extend(page.frames)
    except Exception:
        pass

    for c in containers:
        # Full Name & First/Last
        safe_fill(c, "input[name='name'], input[id*='name']:not([id*='first']):not([id*='last'])", CANDIDATE_DATA["full_name"])
        safe_fill(c, "input[name*='first_name'], input[id*='first_name'], input[name*='firstName'], input[name*='firstname']", CANDIDATE_DATA["first_name"])
        safe_fill(c, "input[name*='last_name'], input[id*='last_name'], input[name*='lastName'], input[name*='lastname']", CANDIDATE_DATA["last_name"])

        # Email
        safe_fill(c, "input[name='email'], input[type='email'], input[id*='email'], input[name*='email']", CANDIDATE_DATA["email"])

        # Phone
        safe_fill(c, "input[name='phone'], input[type='tel'], input[id*='phone'], input[name*='phone'], input[name*='mobile']", CANDIDATE_DATA["phone"])

        # Location / Address / City
        safe_fill(c, "input[name*='address'], input[id*='address'], input[name*='location'], input[id*='location']", CANDIDATE_DATA["location"])
        safe_fill(c, "input[name*='city'], input[id*='city']", CANDIDATE_DATA["city"])

        # Experience & Notice Period
        safe_fill(c, "input[name*='experience'], input[id*='experience'], input[name*='years_of_experience']", CANDIDATE_DATA["experience_years"])
        safe_fill(c, "input[name*='notice'], input[id*='notice']", CANDIDATE_DATA["notice_period"])

        # CTC
        safe_fill(c, "input[name*='current_ctc'], input[id*='current_ctc'], input[name*='current_salary']", CANDIDATE_DATA["current_ctc"])
        safe_fill(c, "input[name*='expected_ctc'], input[id*='expected_ctc'], input[name*='expected_salary']", CANDIDATE_DATA["expected_ctc"])

        # URLs
        safe_fill(c, "input[name*='linkedin'], input[id*='linkedin'], input[name*='urls[LinkedIn]']", CANDIDATE_DATA["linkedin"])
        safe_fill(c, "input[name*='portfolio'], input[id*='portfolio'], input[name*='website'], input[id*='website'], input[name*='urls[Portfolio]']", CANDIDATE_DATA["portfolio"])
        safe_fill(c, "input[name*='other_url'], input[id*='other_url'], input[name*='urls[Other]']", CANDIDATE_DATA["product_lab"])

        # Resume file upload
        try:
            file_input = c.locator("input[type='file']").first
            if file_input.is_visible(timeout=1000) and resume_path.exists():
                file_input.set_input_files(str(resume_path))
                time.sleep(1)
        except Exception:
            pass

    logger.info(f"Tab staged for Job #{job_id}: {company}")


def stage_all_tabs():
    ensure_chrome_running()

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else browser.new_context()

        # Close any existing blank or test tabs
        for existing_page in list(context.pages):
            u = existing_page.url.lower()
            if "example.com" in u or "httpbin.org" in u or "new-tab-page" in u:
                try:
                    existing_page.close()
                except Exception:
                    pass

        # Open each target in its own tab
        for idx, target in enumerate(TARGET_JOBS, 1):
            logger.info(f"[{idx}/5] Staging tab for: {target['company']} - {target['role']}")
            # Create a new tab
            page = context.new_page()
            prefill_tab(page, target)

        # Disconnect CDP client without closing the browser!
        browser.close()

    # Bring Chrome to front on macOS
    try:
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'], capture_output=True)
    except Exception:
        pass

    print("\n" + "=" * 76)
    print("CO-PILOT TABS STAGED SUCCESSFULLY IN DETACHED CHROME!")
    print("=" * 76)
    print("All 5 pre-filled tabs are open on your desktop in Google Chrome:")
    for idx, t in enumerate(TARGET_JOBS, 1):
        print(f"  [Tab {idx}] Job #{t['id']}: {t['company']} ({t['role']}) - {t['portal']}")
    print("-" * 76)
    print("INSTRUCTIONS FOR SUBMISSION:")
    print("1. Switch to Google Chrome on your screen.")
    print("2. Review each pre-filled tab, answer any company-specific questions or CAPTCHAs.")
    print("3. Click the final 'Submit' button on each website.")
    print("4. When you have submitted, run:")
    print("     python3 cli.py verify-open-tabs")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    stage_all_tabs()
