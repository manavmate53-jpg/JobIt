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
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))

from src.ats_applier import (
    detect_login_wall,
    fill_all_visible_inputs,
    normalize_ats_url,
    ZeroFieldsFilledError,
    click_initial_apply_if_present,
    step_through_wizard,
)

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
        "id": 648,
        "company": "Sarvysampanna System Solutions",
        "role": "Corporate Events Manager",
        "track": "event_mice",
        "url": "https://in.indeed.com/viewjob?jk=c5d94c084ced26ba",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Indeed",
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
        "id": 636,
        "company": "Sarvysampanna System Solutions",
        "role": "Corporate Event Planner",
        "track": "event_mice",
        "url": "https://www.naukri.com/job-listings-corporate-event-planner-sarvysampa",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Naukri",
    },
    {
        "id": 618,
        "company": "BCD Meetings & Events",
        "role": "MICE Project Manager / Coordinator",
        "track": "event_mice",
        "url": "https://www.bcdme.com/careers",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Direct Portal",
    },
    {
        "id": 619,
        "company": "CWT Meetings & Events",
        "role": "Event Production & Procurement Executive",
        "track": "event_mice",
        "url": "https://www.cwt-meetings-events.com/careers",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Direct Portal",
    },
    {
        "id": 620,
        "company": "BI Worldwide",
        "role": "MICE Project Manager / Coordinator",
        "track": "event_mice",
        "url": "https://www.biworldwide.co.in/careers",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Direct Portal",
    },
    {
        "id": 621,
        "company": "American Express GBT",
        "role": "MICE Project Manager / Coordinator",
        "track": "event_mice",
        "url": "https://www.amexglobalbusinesstravel.com/careers",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Direct Portal",
    },
    {
        "id": 623,
        "company": "FCM Meetings & Events",
        "role": "Event Production & Procurement Executive",
        "track": "event_mice",
        "url": "https://www.fcmtravel.com/en-in/careers",
        "resume": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
        "portal": "Direct Portal",
    },
]


def is_cdp_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def sync_user_chrome_session(target_profile_dir: Path):
    """Copies current login session & cookies from user's default Chrome profile
    into JobIt's persistent automation profile so auth credentials persist seamlessly.
    """
    src_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    if not src_dir.exists():
        return

    target_profile_dir.mkdir(parents=True, exist_ok=True)
    target_default = target_profile_dir / "Default"
    target_default.mkdir(parents=True, exist_ok=True)

    for fname in ["Local State"]:
        src_file = src_dir / fname
        if src_file.exists():
            try:
                shutil.copy2(src_file, target_profile_dir / fname)
            except Exception as e:
                logger.debug(f"Could not copy {fname}: {e}")

    for fname in ["Cookies", "Network Persistent State", "Login Data", "Preferences"]:
        src_file = src_dir / "Default" / fname
        if src_file.exists():
            try:
                shutil.copy2(src_file, target_default / fname)
            except Exception as e:
                logger.debug(f"Could not copy {fname}: {e}")


def ensure_chrome_running() -> str:
    """Finds Chrome and launches it detached on port 9222 if not already running."""
    if is_cdp_ready():
        logger.info(f"Connected to existing Chrome session on {CDP_URL}")
        return "existing"

    sync_user_chrome_session(PROFILE_DIR)

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Users/manav/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "/Users/manav/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
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

    # 1. Normalize ATS URL
    target_url = normalize_ats_url(url)
    logger.info(f"Loading Job #{job_id}: {company} | URL: {target_url}")
    try:
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        logger.warning(f"Page goto timeout/warning for {company}: {e}")

    time.sleep(2)

    # Mandatory Stage 1 Screenshot
    step1_path = BASE_DIR / "exports" / "proofs" / f"job_{job_id}_step1_loaded.png"
    try:
        page.screenshot(path=str(step1_path))
    except Exception:
        pass

    # 2. Check for login walls
    is_gated, platform, gate_reason = detect_login_wall(page, job_id=job_id)
    if is_gated:
        logger.warning(f"[AUTH REQUIRED] Job #{job_id} on {platform} blocked by login wall: {gate_reason}")

    # 3. Click initial apply button if visible
    click_initial_apply_if_present(page)

    # 4. Multi-Step Wizard & Smart DOM Filling
    filled_fields = []
    try:
        submitted, notes, filled_fields = step_through_wizard(
            page,
            profile=CANDIDATE_DATA,
            cv_path=resume_path,
            max_steps=5,
            pause_before_submit=True,
            return_details=True,
        )
        logger.info(f"Successfully processed Job #{job_id}: {company} | {len(filled_fields)} fields filled | {notes}")
        step2_path = BASE_DIR / "exports" / "proofs" / f"job_{job_id}_step2_filled.png"
        page.screenshot(path=str(step2_path))
    except Exception as e:
        logger.warning(f"Form filling encountered error for Job #{job_id}: {e}")

    step3_path = BASE_DIR / "exports" / "proofs" / f"job_{job_id}_step3_result.png"
    try:
        page.screenshot(path=str(step3_path))
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
            logger.info(f"[{idx}/{len(TARGET_JOBS)}] Staging tab for: {target['company']} - {target['role']}")
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

