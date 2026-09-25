import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path so we can import email_listener
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import email_listener

@pytest.fixture
def mock_env():
    with patch('email_listener.GMAIL_USER', 'testuser'), \
         patch('email_listener.GMAIL_PASS', 'testpass'):
        yield

def test_missing_credentials(capsys):
    with patch('email_listener.GMAIL_USER', None), \
         patch('email_listener.GMAIL_PASS', None):
        email_listener.check_and_process_emails()

    captured = capsys.readouterr()
    assert "missing in .env" in captured.out

@patch('imaplib.IMAP4_SSL')
def test_imap_connection_error(mock_imap, mock_env, capsys):
    mock_imap.side_effect = Exception("Connection Refused")

    email_listener.check_and_process_emails()

    captured = capsys.readouterr()
    assert "IMAP listener error: Connection Refused" in captured.out

@patch('email_listener.get_processed_ids')
@patch('imaplib.IMAP4_SSL')
def test_no_emails_found(mock_imap, mock_get_processed, mock_env, capsys):
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance
    # search returns status and messages
    mock_imap_instance.search.return_value = ("OK", [b""])

    email_listener.check_and_process_emails()

    captured = capsys.readouterr()
    assert "No emails found in date range." in captured.out
    mock_imap_instance.logout.assert_called_once()

@patch('email_listener.get_processed_ids')
@patch('imaplib.IMAP4_SSL')
def test_already_processed_emails(mock_imap, mock_get_processed, mock_env, capsys):
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance
    mock_imap_instance.search.return_value = ("OK", [b"1 2"])

    # Both IDs are already processed
    mock_get_processed.return_value = {"1", "2"}

    email_listener.check_and_process_emails()

    # fetch should not be called
    mock_imap_instance.fetch.assert_not_called()
    mock_imap_instance.logout.assert_called_once()

@patch('email_listener.save_processed_id')
@patch('email_listener.extract_email_text')
@patch('email_listener.get_processed_ids')
@patch('imaplib.IMAP4_SSL')
def test_email_without_keywords(mock_imap, mock_get_processed, mock_extract, mock_save, mock_env, capsys):
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance
    mock_imap_instance.search.return_value = ("OK", [b"1"])
    mock_imap_instance.fetch.return_value = ("OK", [(b"1 (RFC822)", b"fake email data")])

    mock_get_processed.return_value = set()
    # Return subject, sender, date, body without any keywords
    mock_extract.return_value = ("Hello", "test@test.com", "Date", "Just a regular email body.")

    email_listener.check_and_process_emails()

    mock_extract.assert_called_once()
    mock_save.assert_called_once_with("1")
    captured = capsys.readouterr()
    assert "Evaluating" not in captured.out

@patch('email_listener.parse_interview_with_llm')
@patch('email_listener.save_processed_id')
@patch('email_listener.extract_email_text')
@patch('email_listener.get_processed_ids')
@patch('imaplib.IMAP4_SSL')
def test_email_with_keywords_not_interview(mock_imap, mock_get_processed, mock_extract, mock_save, mock_parse, mock_env, capsys):
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance
    mock_imap_instance.search.return_value = ("OK", [b"1"])
    mock_imap_instance.fetch.return_value = ("OK", [(b"1 (RFC822)", b"fake email data")])

    mock_get_processed.return_value = set()
    mock_extract.return_value = ("Interview Process", "test@test.com", "Date", "This is an interview preparation newsletter.")
    mock_parse.return_value = {"is_interview": False}

    email_listener.check_and_process_emails()

    mock_parse.assert_called_once()
    mock_save.assert_called_once_with("1")
    captured = capsys.readouterr()
    assert "INTERVIEW/TEST DETECTED" not in captured.out

@patch('email_listener.generate_prep_sheet')
@patch('email_listener.add_interview_to_calendar')
@patch('email_listener.parse_interview_with_llm')
@patch('email_listener.save_processed_id')
@patch('email_listener.extract_email_text')
@patch('email_listener.get_processed_ids')
@patch('imaplib.IMAP4_SSL')
def test_email_with_keywords_is_interview(mock_imap, mock_get_processed, mock_extract, mock_save, mock_parse, mock_add_cal, mock_gen_prep, mock_env, capsys):
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance
    mock_imap_instance.search.return_value = ("OK", [b"1"])
    mock_imap_instance.fetch.return_value = ("OK", [(b"1 (RFC822)", b"fake email data")])

    mock_get_processed.return_value = set()
    mock_extract.return_value = ("Invitation for Interview", "hr@testco.com", "Date", "We would like to invite you for a coding test.")
    mock_parse.return_value = {
        "is_interview": True,
        "company_name": "TestCo",
        "job_role": "Tester",
        "date_time": "2026-08-27 15:00"
    }
    mock_gen_prep.return_value = "/path/to/prep.md"

    email_listener.check_and_process_emails()

    mock_parse.assert_called_once()
    mock_add_cal.assert_called_once_with("TestCo", "2026-08-27 15:00")
    mock_gen_prep.assert_called_once_with("TestCo", "2026-08-27 15:00")
    mock_save.assert_called_once_with("1")

    captured = capsys.readouterr()
    assert "INTERVIEW/TEST DETECTED: TestCo (Tester) at 2026-08-27 15:00" in captured.out
    assert "AI Prep Sheet generated: /path/to/prep.md" in captured.out

@patch('email_listener.generate_prep_sheet')
@patch('email_listener.add_interview_to_calendar')
@patch('email_listener.parse_interview_with_llm')
@patch('email_listener.save_processed_id')
@patch('email_listener.extract_email_text')
@patch('email_listener.get_processed_ids')
@patch('imaplib.IMAP4_SSL')
def test_email_interview_exceptions(mock_imap, mock_get_processed, mock_extract, mock_save, mock_parse, mock_add_cal, mock_gen_prep, mock_env, capsys):
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance
    mock_imap_instance.search.return_value = ("OK", [b"1"])
    mock_imap_instance.fetch.return_value = ("OK", [(b"1 (RFC822)", b"fake email data")])

    mock_get_processed.return_value = set()
    mock_extract.return_value = ("Invitation for Interview", "hr@testco.com", "Date", "We would like to invite you for a coding test.")
    mock_parse.return_value = {
        "is_interview": True,
        "company_name": "TestCo",
        "job_role": "Tester",
        "date_time": "2026-08-27 15:00"
    }

    # Induce exceptions
    mock_add_cal.side_effect = Exception("Calendar API fail")
    mock_gen_prep.side_effect = Exception("Prep generation fail")

    email_listener.check_and_process_emails()

    mock_save.assert_called_once_with("1")

    captured = capsys.readouterr()
    assert "Calendar error: Calendar API fail" in captured.out
    assert "Prep generation error: Prep generation fail" in captured.out
