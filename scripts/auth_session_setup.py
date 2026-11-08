#!/usr/bin/env python3
"""Interactive Authentication Session Setup Script.

Launches a persistent browser session using `data/browser_profile` to allow the user
to log in once to major job platforms (Indeed, LinkedIn, Naukri, Wellfound).
Cookies, tokens, and sessions persist in `data/browser_profile` so subsequent
automated and co-pilot runs are pre-authenticated without hitting login walls.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("auth_session_setup")

PROFILE_DIR = BASE_DIR / "data" / "browser_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
PROOFS_DIR = BASE_DIR / "exports" / "proofs"
PROOFS_DIR.mkdir(parents=True, exist_ok=True)

AUTH_URLS = {
    "LinkedIn": "https://www.linkedin.com/login",
    "Indeed": "https://secure.indeed.com/auth",
    "Naukri": "https://www.naukri.com/nlogin/login",
    "Wellfound": "https://wellfound.com/login",
}


def setup_auth_session():
    """Launches visible persistent browser tabs for each portal and verifies authentication."""
    print("=" * 80)
    print("JOBIT BROWSER AUTHENTICATION SETUP")
    print(f"Profile Directory: {PROFILE_DIR}")
    print("=" * 80)
    print("Opening persistent browser with tabs for LinkedIn, Indeed, Naukri, and Wellfound.")
    print("Please log in to each account in the opened browser window.")
    print("Once logged in across your accounts, return here and press ENTER to verify and save sessions.")
    print("=" * 80)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        pages = {}
        first = True
        for name, url in AUTH_URLS.items():
            if first and context.pages:
                page = context.pages[0]
                first = False
            else:
                page = context.new_page()
            page.goto(url)
            pages[name] = page
            time.sleep(1)

        # macOS: activate Chromium window
        try:
            subprocess.run(["osascript", "-e", 'tell application "Chromium" to activate'], capture_output=True)
        except Exception:
            pass

        input("\n>>> Press ENTER here once you have finished logging into your accounts: ")

        print("\nVerifying session states across open tabs...")
        results = {}
        for name, page in pages.items():
            current_url = page.url.lower()
            content = page.content().lower()

            is_authenticated = False
            user_identifier = "Unknown"

            if name == "LinkedIn":
                # If feed or mynetwork or jobs or not on login/checkpoint
                if any(k in current_url for k in ["/feed", "/mynetwork", "/jobs", "/in/"]):
                    is_authenticated = True
                elif "/login" not in current_url and "/checkpoint" not in current_url and "sign in" not in content[:500]:
                    is_authenticated = True

            elif name == "Indeed":
                if any(k in current_url for k in ["indeed.com/m", "indeed.com/promo", "myjobs"]) or (
                    "secure.indeed.com/auth" not in current_url and "sign in" not in content[:500]
                ):
                    is_authenticated = True

            elif name == "Naukri":
                if any(k in current_url for k in ["naukri.com/mnjuser", "naukri.com/profile"]) or (
                    "/nlogin" not in current_url and "login" not in current_url
                ):
                    is_authenticated = True

            elif name == "Wellfound":
                if any(k in current_url for k in ["wellfound.com/jobs", "wellfound.com/candidates"]) or (
                    "/login" not in current_url and "log in" not in content[:500]
                ):
                    is_authenticated = True

            results[name] = is_authenticated
            status_text = "[VERIFIED AUTHENTICATED]" if is_authenticated else "[STILL LOGGED OUT]"
            print(f"  {name:12}: {status_text} | URL: {page.url[:60]}")

            # Save proof screenshot
            shot_path = PROOFS_DIR / f"auth_status_{name.lower()}.png"
            page.screenshot(path=str(shot_path))

        print("\nAll authentication cookies, tokens, and storage state are saved to:")
        print(f"  {PROFILE_DIR}")
        print("Closing browser context. You are now ready for automated and co-pilot submissions!\n")
        context.close()
        return results


if __name__ == "__main__":
    setup_auth_session()

