import pytest
from unittest.mock import MagicMock, patch
from src.inbox_monitor import InboxMonitor, clean_header_str


def test_clean_header_str():
    assert clean_header_str("Interview Invitation") == "Interview Invitation"
    assert clean_header_str("") == ""


def test_inbox_monitor_unconfigured():
    monitor = InboxMonitor(email_password="")
    assert not monitor.is_configured()
    assert monitor.check_for_replies(["Swiggy", "CRED"]) == []


def test_inbox_monitor_mocked_search():
    monitor = InboxMonitor(
        imap_server="imap.example.com",
        email_user="test@example.com",
        email_password="validpassword123"
    )
    assert monitor.is_configured()

    with patch("imaplib.IMAP4_SSL") as mock_imap:
        instance = MagicMock()
        mock_imap.return_value = instance
        instance.login.return_value = ("OK", [b"Logged in"])
        instance.select.return_value = ("OK", [b"1"])
        instance.search.return_value = ("OK", [b"1 2"])

        # Mock email 1
        raw_email = (
            b"From: recruiter@swiggy.in\r\n"
            b"Subject: Next steps regarding your PM application\r\n"
            b"Date: Mon, 27 Oct 2026 10:00:00 +0000\r\n\r\n"
            b"Hello Manav, we would like to invite you for an interview."
        )
        instance.fetch.return_value = ("OK", [(b"1 (RFC822 {100})", raw_email)])

        replies = monitor.check_for_replies(["Swiggy"], max_emails=5)
        assert len(replies) == 1
        assert replies[0]["company"] == "Swiggy"
        assert replies[0]["is_interview"] is True

