import pytest
from src.ats_applier import (
    detect_login_wall,
    normalize_ats_url,
    ZeroFieldsFilledError,
)

class MockPage:
    def __init__(self, url="", content_html=""):
        self.url = url
        self._content = content_html

    def content(self):
        return self._content


def test_normalize_ats_url():
    # Jobvite URL normalization
    assert normalize_ats_url("https://jobs.jobvite.com/webmd/job/oH8YAfw7") == "https://jobs.jobvite.com/webmd/job/oH8YAfw7/apply"
    assert normalize_ats_url("https://jobs.jobvite.com/webmd/job/oH8YAfw7?isComingFromApp=true") == "https://jobs.jobvite.com/webmd/job/oH8YAfw7/apply?isComingFromApp=true"
    assert normalize_ats_url("https://jobs.jobvite.com/webmd/job/oH8YAfw7/apply") == "https://jobs.jobvite.com/webmd/job/oH8YAfw7/apply"

    # Lever URL normalization
    assert normalize_ats_url("https://jobs.lever.co/company/abc-123") == "https://jobs.lever.co/company/abc-123/apply"
    assert normalize_ats_url("https://jobs.lever.co/company/abc-123/apply") == "https://jobs.lever.co/company/abc-123/apply"


def test_detect_login_wall_linkedin():
    # LinkedIn login page
    p = MockPage(url="https://www.linkedin.com/login", content_html="<h1>Sign in to LinkedIn</h1>")
    is_gated, platform, reason = detect_login_wall(p, job_id=643)
    assert is_gated is True
    assert platform == "LinkedIn"

    # LinkedIn checkpoint
    p2 = MockPage(url="https://www.linkedin.com/checkpoint/challenge", content_html="<h1>Security Verification</h1>")
    is_gated2, platform2, reason2 = detect_login_wall(p2, job_id=643)
    assert is_gated2 is True
    assert platform2 == "LinkedIn"


def test_detect_login_wall_naukri():
    p = MockPage(url="https://www.naukri.com/nlogin/login", content_html="<button>Login</button>")
    is_gated, platform, reason = detect_login_wall(p, job_id=638)
    assert is_gated is True
    assert platform == "Naukri"


def test_detect_login_wall_indeed():
    p = MockPage(url="https://secure.indeed.com/account/login", content_html="<h1>Sign in to your account</h1>")
    is_gated, platform, reason = detect_login_wall(p, job_id=647)
    assert is_gated is True
    assert platform == "Indeed"


def test_detect_login_wall_wellfound():
    p = MockPage(url="https://wellfound.com/login", content_html="<h1>Log In</h1><p>Sign Up to Apply</p>")
    is_gated, platform, reason = detect_login_wall(p, job_id=179)
    assert is_gated is True
    assert platform == "Wellfound"


def test_detect_login_wall_direct_ats_passes():
    p = MockPage(url="https://jobs.jobvite.com/webmd/job/oH8YAfw7/apply", content_html="<h1>WebMD Careers</h1>")
    is_gated, platform, reason = detect_login_wall(p, job_id=616)
    assert is_gated is False

