import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
import main as outreach_main

@pytest.fixture(autouse=True)
def mock_time_sleep():
    with patch('time.sleep', return_value=None) as mock_sleep:
        yield mock_sleep

def test_main_test_email():
    with patch('sys.argv', ['main.py', '--test-email', 'test@example.com']):
        with patch('main._run_test_email') as mock_run_test:
            outreach_main.main()
            mock_run_test.assert_called_once_with('test@example.com')

def test_main_export():
    with patch('sys.argv', ['main.py', '--export']):
        with patch('main._run_export') as mock_run_export:
            outreach_main.main()
            mock_run_export.assert_called_once()

def test_main_followups():
    with patch('sys.argv', ['main.py', '--followups']):
        with patch('main._run_followups') as mock_run_followups:
            outreach_main.main()
            mock_run_followups.assert_called_once()

@patch('main.scrape_linkedin_posts')
@patch('main.extract_contact_info')
@patch('main.scrape_recruiter_profile')
@patch('main.generate_cold_email')
@patch('main._send_email_wrapped')
@patch('main._already_contacted')
@patch('main._record_sent')
def test_main_outreach_loop_happy_path(
    mock_record_sent, mock_already_contacted, mock_send_email,
    mock_generate_cold_email, mock_scrape_profile, mock_extract_contact,
    mock_scrape_posts
):
    mock_scrape_posts.return_value = [{"text": "Hiring", "name": "John Doe", "company": "Tech"}]
    mock_extract_contact.return_value = ("john@tech.com", "text")
    mock_already_contacted.return_value = False
    mock_scrape_profile.return_value = "Bio text"
    mock_generate_cold_email.return_value = ("Subject", "Body")
    mock_send_email.return_value = True

    with patch('sys.argv', ['main.py', '--roles', 'Python Developer', '--limit', '1']):
        outreach_main.main()

    mock_scrape_posts.assert_called_once()
    mock_extract_contact.assert_called_once()
    mock_scrape_profile.assert_called_once()
    mock_generate_cold_email.assert_called_once()
    mock_send_email.assert_called_once()
    mock_record_sent.assert_called_once()

@patch('main.scrape_linkedin_posts')
def test_main_outreach_loop_no_posts(mock_scrape_posts):
    mock_scrape_posts.return_value = []

    with patch('sys.argv', ['main.py', '--roles', 'Python Developer']):
        outreach_main.main()

    mock_scrape_posts.assert_called_once()

@patch('main.scrape_linkedin_posts')
@patch('main.extract_contact_info')
@patch('main._send_email_wrapped')
def test_main_outreach_loop_no_email(mock_send_email, mock_extract_contact, mock_scrape_posts):
    mock_scrape_posts.return_value = [{"text": "Hiring", "name": "John Doe", "company": "Tech"}]
    mock_extract_contact.return_value = (None, None)

    with patch('sys.argv', ['main.py', '--roles', 'Python Developer']):
        outreach_main.main()

    mock_scrape_posts.assert_called_once()
    mock_extract_contact.assert_called_once()
    mock_send_email.assert_not_called()

@patch('main.scrape_linkedin_posts')
@patch('main.extract_contact_info')
@patch('main._already_contacted')
@patch('main._send_email_wrapped')
def test_main_outreach_loop_already_contacted(mock_send_email, mock_already_contacted, mock_extract_contact, mock_scrape_posts):
    mock_scrape_posts.return_value = [{"text": "Hiring", "name": "John Doe", "company": "Tech"}]
    mock_extract_contact.return_value = ("john@tech.com", "text")
    mock_already_contacted.return_value = True

    with patch('sys.argv', ['main.py', '--roles', 'Python Developer']):
        outreach_main.main()

    mock_already_contacted.assert_called_once()
    mock_send_email.assert_not_called()

@patch('main.scrape_linkedin_posts')
@patch('main.extract_contact_info')
@patch('main.scrape_recruiter_profile')
@patch('main.generate_cold_email')
@patch('main._send_email_wrapped')
@patch('main._already_contacted')
def test_main_outreach_loop_composer_fails(
    mock_already_contacted, mock_send_email, mock_generate_cold_email,
    mock_scrape_profile, mock_extract_contact, mock_scrape_posts
):
    mock_scrape_posts.return_value = [{"text": "Hiring", "name": "John Doe", "company": "Tech"}]
    mock_extract_contact.return_value = ("john@tech.com", "text")
    mock_already_contacted.return_value = False
    mock_generate_cold_email.return_value = ("Subject", None) # No body generated

    with patch('sys.argv', ['main.py', '--roles', 'Python Developer']):
        outreach_main.main()

    mock_generate_cold_email.assert_called_once()
    mock_send_email.assert_not_called()

@patch('main.scrape_linkedin_posts')
@patch('main.extract_contact_info')
@patch('main.scrape_recruiter_profile')
@patch('main.generate_cold_email')
@patch('main._send_email_wrapped')
@patch('main._already_contacted')
def test_main_outreach_loop_dry_run(
    mock_already_contacted, mock_send_email, mock_generate_cold_email,
    mock_scrape_profile, mock_extract_contact, mock_scrape_posts
):
    mock_scrape_posts.return_value = [{"text": "Hiring", "name": "John Doe", "company": "Tech"}]
    mock_extract_contact.return_value = ("john@tech.com", "text")
    mock_already_contacted.return_value = False
    mock_generate_cold_email.return_value = ("Subject", "Body")

    with patch('sys.argv', ['main.py', '--roles', 'Python Developer', '--dry-run', '--limit', '1']):
        outreach_main.main()

    mock_send_email.assert_not_called()
    mock_generate_cold_email.assert_called_once()

@patch('main.scrape_linkedin_posts')
@patch('main.extract_contact_info')
@patch('main.scrape_recruiter_profile')
@patch('main.generate_cold_email')
@patch('main._send_email_wrapped')
@patch('main._already_contacted')
@patch('main._record_sent')
def test_main_outreach_loop_daily_cap(
    mock_record_sent, mock_already_contacted, mock_send_email,
    mock_generate_cold_email, mock_scrape_profile, mock_extract_contact,
    mock_scrape_posts
):
    # Setup posts for multiple roles to ensure daily cap breaks the loop
    mock_scrape_posts.return_value = [{"text": "Hiring", "name": "John Doe", "company": "Tech"}]
    mock_extract_contact.return_value = ("john@tech.com", "text")
    mock_already_contacted.return_value = False
    mock_generate_cold_email.return_value = ("Subject", "Body")
    mock_send_email.return_value = True

    with patch('sys.argv', ['main.py', '--roles', 'Python Developer, Django Developer', '--limit', '1']):
        outreach_main.main()

    # We set a limit of 1, so we should only scrape posts once for the first role, then hit cap and break
    mock_scrape_posts.assert_called_once_with('Python Developer')
    mock_send_email.assert_called_once()
