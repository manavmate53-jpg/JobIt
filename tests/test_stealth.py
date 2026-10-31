"""Unit Tests for Stealth Browser, Anti-Detection & Jitter Protocols."""

import time
from unittest.mock import MagicMock
import pytest
from core.browser import StealthBrowser


def test_stealth_browser_config_and_cookie():
    browser = StealthBrowser(
        headless=True,
        cookie_value="test_li_at_cookie_value_xyz",
        min_delay=1.0,
        max_delay=3.0,
    )

    assert browser.cookie_value == "test_li_at_cookie_value_xyz"
    assert "Macintosh" in browser.user_agent
    assert browser.viewport["width"] == 1440
    assert browser.viewport["height"] == 900


def test_challenge_detection_graceful_abort():
    browser = StealthBrowser()

    # Mock page with challenge URL
    mock_challenge_page = MagicMock()
    mock_challenge_page.url = "https://www.linkedin.com/checkpoint/challenge/AgF..."
    mock_challenge_page.content.return_value = "<html>Please solve this challenge to continue</html>"

    is_challenge = browser.check_for_challenge(mock_challenge_page)
    assert is_challenge is True

    # Mock clean standard page
    mock_clean_page = MagicMock()
    mock_clean_page.url = "https://www.linkedin.com/feed/"
    mock_clean_page.content.return_value = "<html><div>LinkedIn Feed</div></html>"

    is_clean = browser.check_for_challenge(mock_clean_page)
    assert is_clean is False


def test_random_jitter_bounds():
    browser = StealthBrowser(min_delay=0.1, max_delay=0.3)
    start_time = time.time()
    browser.random_jitter(multiplier=1.0)
    elapsed = time.time() - start_time

    assert 0.08 <= elapsed <= 0.6

