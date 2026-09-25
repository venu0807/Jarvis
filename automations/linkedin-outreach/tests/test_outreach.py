import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import composer
import mailer

def test_composer_strips_cloud_when_not_allowed():
    """QA/Security Test: Ensure composer defaults to local unless cloud is explicitly enabled."""
    os.environ["JARVIS_ALLOW_CLOUD"] = "0"
    chain = ["qwen2.5-coder:7b", "gemma4:31b-cloud"]
    safe_chain = composer._strip_cloud_entries(chain)
    assert "gemma4:31b-cloud" not in safe_chain
    assert "qwen2.5-coder:7b" in safe_chain

def test_composer_allows_cloud_when_explicitly_set():
    """QA/Security Test: Cloud allowed if JARVIS_ALLOW_CLOUD=1."""
    os.environ["JARVIS_ALLOW_CLOUD"] = "1"
    chain = ["qwen2.5-coder:7b", "gemma4:31b-cloud"]
    safe_chain = composer._strip_cloud_entries(chain)
    assert "gemma4:31b-cloud" in safe_chain

def test_mailer_fails_gracefully_without_credentials():
    """QA Test: Mailer should return False immediately if SMTP credentials aren't set."""
    # Ensure they are cleared
    if "SMTP_USER" in os.environ:
        del os.environ["SMTP_USER"]
    if "SMTP_APP_PASSWORD" in os.environ:
        del os.environ["SMTP_APP_PASSWORD"]
    
    assert mailer.send_email("test@example.com", "Subject", "Body") == False

def test_generate_cold_email_with_subject():
    """QA Test: generate_cold_email parses the Subject correctly."""
    with patch("composer._try_model_via_policy") as mock_policy, \
         patch("composer._strip_cloud_entries") as mock_chain:
        mock_chain.return_value = ["mock_model"]
        mock_policy.return_value = "Subject: My Cool Subject\nHello there,\nThis is the body."

        subject, body = composer.generate_cold_email(
            post_text="Hiring a SWE",
            recruiter_name="John Doe"
        )
        assert subject == "My Cool Subject"
        assert body == "Hello there,\nThis is the body."

def test_generate_cold_email_without_subject():
    """QA Test: generate_cold_email uses default subject when none is provided."""
    with patch("composer._try_model_via_policy") as mock_policy, \
         patch("composer._strip_cloud_entries") as mock_chain:
        mock_chain.return_value = ["mock_model"]
        mock_policy.return_value = "Hello there,\nThis is the body."

        subject, body = composer.generate_cold_email(
            post_text="Hiring a SWE",
            recruiter_name="Jane Doe"
        )
        assert subject == "Application - Jane Doe"
        assert body == "Hello there,\nThis is the body."

def test_generate_cold_email_unrelated_role():
    """QA Test: generate_cold_email aborts when role is unrelated."""
    with patch("composer._try_model_via_policy") as mock_policy, \
         patch("composer._strip_cloud_entries") as mock_chain:
        mock_chain.return_value = ["mock_model"]
        mock_policy.return_value = "UNRELATED_ROLE"

        subject, body = composer.generate_cold_email(
            post_text="Hiring for Sales",
            recruiter_name="John Doe"
        )
        assert subject is None
        assert body is None

def test_generate_cold_email_all_models_fail():
    """QA Test: generate_cold_email returns None if all models return None."""
    with patch("composer._try_model_via_policy") as mock_policy, \
         patch("composer._strip_cloud_entries") as mock_chain:
        mock_chain.return_value = ["mock1", "mock2"]
        mock_policy.return_value = None

        subject, body = composer.generate_cold_email(
            post_text="Hiring a SWE",
            recruiter_name="John Doe"
        )
        assert subject is None
        assert body is None
        assert mock_policy.call_count == 2

def test_generate_cold_email_empty_chain():
    """QA Test: generate_cold_email handles empty chain properly."""
    with patch("composer._strip_cloud_entries") as mock_chain, \
         patch("composer._try_model_via_policy") as mock_policy:
        mock_chain.return_value = []

        subject, body = composer.generate_cold_email(
            post_text="Hiring a SWE",
            recruiter_name="John Doe"
        )
        assert subject is None
        assert body is None
        mock_policy.assert_not_called()
