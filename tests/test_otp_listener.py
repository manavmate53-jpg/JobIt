"""Tests for EmailOTPListener."""

import pytest
from unittest.mock import MagicMock, patch
from src.otp_listener import EmailOTPListener


def test_otp_regex_extraction():
    listener = EmailOTPListener()
    
    # Test clean header
    assert listener._clean_header("Hello World") == "Hello World"
    
    # Test regex patterns on sample texts
    import re
    samples = {
        "Your LinkedIn verification code is 492018.": "492018",
        "6-digit Code for your application to IDfy - 876922": "876922",
        "Please enter OTP: 1234 to verify": "1234",
        "Your security PIN is 998811": "998811",
    }
    for text, expected in samples.items():
        m = re.search(r"(?:code|pin|otp|verification)[\s\:\-\w]*?\b(\d{4,6})\b", text, re.IGNORECASE)
        assert m is not None
        assert m.group(1) == expected

