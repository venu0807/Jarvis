import os
import sys
from pathlib import Path

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
