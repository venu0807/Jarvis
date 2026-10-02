import pytest
import os
import requests
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add parent directory to sys.path so we can import extractor
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractor import get_email_from_apollo

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {"APOLLO_API_KEY": "test_key"}):
        yield

def test_apollo_missing_api_key():
    with patch.dict(os.environ, clear=True):
        assert get_email_from_apollo("John Doe", "Example Inc") is None

def test_apollo_200_with_email(mock_env):
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"person": {"email": "john@example.com"}}
        mock_post.return_value = mock_resp

        assert get_email_from_apollo("John Doe", "Example Inc") == "john@example.com"
        mock_post.assert_called_once()

def test_apollo_200_no_person(mock_env):
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_post.return_value = mock_resp

        assert get_email_from_apollo("John Doe", "Example Inc") is None
        mock_post.assert_called_once()

def test_apollo_404(mock_env):
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_post.return_value = mock_resp

        assert get_email_from_apollo("John Doe", "Example Inc") is None
        mock_post.assert_called_once()

def test_apollo_422(mock_env):
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.text = "Bad input"
        mock_post.return_value = mock_resp

        assert get_email_from_apollo("John Doe", "Example Inc") is None
        mock_post.assert_called_once()

def test_apollo_402_429(mock_env):
    for status in (402, 429):
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = status
            mock_post.return_value = mock_resp

            assert get_email_from_apollo("John Doe", "Example Inc") is None
            mock_post.assert_called_once()

def test_apollo_5xx_retries(mock_env):
    with patch("requests.post") as mock_post, patch("time.sleep") as mock_sleep:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        assert get_email_from_apollo("John Doe", "Example Inc", max_retries=2) is None
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

def test_apollo_timeout_retries(mock_env):
    with patch("requests.post", side_effect=requests.exceptions.Timeout) as mock_post, patch("time.sleep") as mock_sleep:
        assert get_email_from_apollo("John Doe", "Example Inc", max_retries=2) is None
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

def test_apollo_generic_exception(mock_env):
    with patch("requests.post", side_effect=Exception("Generic Error")) as mock_post:
        assert get_email_from_apollo("John Doe", "Example Inc") is None
        mock_post.assert_called_once()

def test_apollo_unhandled_status_code(mock_env):
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 418
        mock_resp.text = "I'm a teapot"
        mock_post.return_value = mock_resp

        assert get_email_from_apollo("John Doe", "Example Inc") is None
        mock_post.assert_called_once()
