"""Stealth Playwright Browser Wrapper with Human Emulation & Cookie Auth.

Provides undetectable browser interactions for LinkedIn automation:
- Cookie-based authentication using LI_AT
- Dynamic jitter and randomized delay distributions
- Human typing simulation with micro-delays between keystrokes
- Human scrolling simulation
- Challenge and CAPTCHA detection with graceful non-zero aborts
- Masking of navigator.webdriver and browser fingerprints
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Dict, List, Optional
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

try:
    from playwright_stealth import stealth_sync
    HAS_PLAYWRIGHT_STEALTH = True
except ImportError:
    HAS_PLAYWRIGHT_STEALTH = False

logger = logging.getLogger("ying_yang.browser")


class ChallengeDetectedException(Exception):
    """Raised when LinkedIn presents a verification or CAPTCHA challenge."""
    pass


class StealthBrowser:
    """Stealth Playwright browser manager with human behavioral simulation."""

    def __init__(
        self,
        headless: bool = True,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        min_delay: float = 4.5,
        max_delay: float = 14.2,
        cookie_value: Optional[str] = None,
    ):
        self.headless = headless
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        self.viewport = viewport or {"width": 1440, "height": 900}
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.cookie_value = cookie_value or os.getenv("LINKEDIN_COOKIE") or os.getenv("LI_AT")

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def start(self) -> Page:
        """Launches the stealth browser instance and injects session cookies."""
        logger.info("Initializing Playwright Stealth Browser...")
        self._playwright = sync_playwright().start()

        # Launch Chromium with anti-detection flags
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
                "--hide-scrollbars",
                "--mute-audio",
            ],
        )

        self._context = self._browser.new_context(
            user_agent=self.user_agent,
            viewport=self.viewport,
            locale="en-US",
            timezone_id="Asia/Kolkata",
            permissions=["geolocation"],
            geolocation={"latitude": 19.0760, "longitude": 72.8777}, # Mumbai coordinates
            device_scale_factor=1.0,
            has_touch=False,
            is_mobile=False,
        )

        # Inject LinkedIn Authentication Cookie if available
        if self.cookie_value:
            clean_cookie = self.cookie_value.strip().strip('"').strip("'")
            self._context.add_cookies([
                {
                    "name": "li_at",
                    "value": clean_cookie,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None",
                }
            ])
            logger.info("Injected LI_AT authentication cookie for domain .linkedin.com")

        self._page = self._context.new_page()

        # Apply stealth evasions
        self._apply_stealth(self._page)
        return self._page

    def _apply_stealth(self, page: Page) -> None:
        """Applies playwright-stealth and manual JavaScript navigator evasions."""
        if HAS_PLAYWRIGHT_STEALTH:
            try:
                stealth_sync(page)
                logger.debug("Applied playwright-stealth to page.")
            except Exception as e:
                logger.warning(f"Error applying playwright-stealth: {e}")

        # Additional robust manual evasions
        page.add_init_script("""
            // Overwrite webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock languages and plugins
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock Chrome runtime
            window.chrome = {
                runtime: {}
            };
        """)

    def random_jitter(self, multiplier: float = 1.0) -> None:
        """Sleeps for a randomized human-like delay duration."""
        low = self.min_delay * multiplier
        high = self.max_delay * multiplier
        delay = random.uniform(low, high)
        logger.debug(f"Jitter pause: {delay:.2f}s")
        time.sleep(delay)

    def check_for_challenge(self, page: Optional[Page] = None) -> bool:
        """Inspects page URL and DOM for verification checkpoints and CAPTCHAs."""
        target_page = page or self._page
        if not target_page:
            return False

        current_url = target_page.url.lower()
        content = ""
        try:
            content = target_page.content().lower()
        except Exception:
            pass

        # Checkpoint URL patterns
        challenge_markers = [
            "/checkpoint/challenge",
            "/checkpoint/lg/login-submit",
            "security-check",
            "captcha",
            "recaptcha",
            "hcaptcha",
            "verification code",
            "quick verification",
        ]

        if any(marker in current_url for marker in challenge_markers) or (
            "please solve this challenge" in content or "unusual activity" in content
        ):
            logger.warning("=" * 65)
            logger.warning("[WARNING] CHALLENGE_DETECTED: LinkedIn verification prompt encountered!")
            logger.warning(f"URL: {target_page.url}")
            logger.warning("Aborting interaction gracefully without non-zero exit code.")
            logger.warning("=" * 65)
            return True

        return False

    def human_type(self, selector: str, text: str, page: Optional[Page] = None) -> None:
        """Types text into an element with variable human keystroke delays."""
        target_page = page or self._page
        if not target_page:
            return

        target_page.click(selector)
        for char in text:
            target_page.keyboard.type(char)
            # Randomized keystroke delay between 40ms and 160ms
            time.sleep(random.uniform(0.04, 0.16))
            if random.random() < 0.05:
                # Occasional brief pause mimicking thinking
                time.sleep(random.uniform(0.3, 0.8))

    def human_scroll(self, page: Optional[Page] = None, scrolls: int = 3) -> None:
        """Performs smooth, randomized human scrolling on the page."""
        target_page = page or self._page
        if not target_page:
            return

        for _ in range(scrolls):
            delta_y = random.randint(250, 650)
            target_page.mouse.wheel(0, delta_y)
            time.sleep(random.uniform(1.2, 2.8))

    def close(self) -> None:
        """Closes browser and cleans up Playwright processes."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.debug(f"Error during browser cleanup: {e}")
        logger.info("Stealth Browser session closed.")

    def __enter__(self) -> StealthBrowser:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

