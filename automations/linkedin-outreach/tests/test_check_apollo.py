import os
import sys
import importlib.util
from unittest.mock import patch, MagicMock
import pytest
import requests

@pytest.fixture
def check_apollo_mod():
    # We must patch os.environ for APOLLO_API_KEY so the script doesn't sys.exit(1) on import
    with patch.dict(os.environ, {"APOLLO_API_KEY": "fake_key"}), \
         patch("requests.post") as mock_post, \
         patch("sys.exit") as mock_exit:

        spec = importlib.util.spec_from_file_location(
            "check_apollo",
            "automations/linkedin-outreach/scripts/check_apollo.py"
        )
        check_apollo = importlib.util.module_from_spec(spec)
        sys.modules["check_apollo"] = check_apollo
        spec.loader.exec_module(check_apollo)

        # Reset the mock because it might get called during import if the script runs anything
        mock_post.reset_mock()
        yield check_apollo, mock_post

def test_check_apollo_success(check_apollo_mod, capsys):
    check_apollo, mock_post = check_apollo_mod

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Success response"
    mock_post.return_value = mock_response

    result = check_apollo.test("Test Success", "http://fake.url", {"data": "test"})

    assert result == mock_response
    mock_post.assert_called_with(
        "http://fake.url",
        headers={"Content-Type": "application/json", "X-Api-Key": "fake_key"},
        json={"data": "test"},
        timeout=15
    )
    captured = capsys.readouterr()
    assert "=== Test Success ===" in captured.out
    assert "✅ 200: Success response" in captured.out

def test_check_apollo_ok_not_200(check_apollo_mod, capsys):
    check_apollo, mock_post = check_apollo_mod

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not found response"
    mock_post.return_value = mock_response

    result = check_apollo.test("Test Not Found", "http://fake.url", {"data": "test"}, ok_codes=(200, 404, 422))

    assert result == mock_response
    captured = capsys.readouterr()
    assert "=== Test Not Found ===" in captured.out
    assert "✅ 404: Not found response" in captured.out

def test_check_apollo_failure_status(check_apollo_mod, capsys):
    check_apollo, mock_post = check_apollo_mod

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    result = check_apollo.test("Test Failure", "http://fake.url", {"data": "test"})

    assert result == mock_response
    captured = capsys.readouterr()
    assert "=== Test Failure ===" in captured.out
    assert "❌ 500: Internal Server Error" in captured.out

def test_check_apollo_exception(check_apollo_mod, capsys):
    check_apollo, mock_post = check_apollo_mod

    mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

    result = check_apollo.test("Test Exception", "http://fake.url", {"data": "test"})

    assert result is None
    captured = capsys.readouterr()
    assert "=== Test Exception ===" in captured.out
    assert "❌ request failed: Connection timed out" in captured.out
