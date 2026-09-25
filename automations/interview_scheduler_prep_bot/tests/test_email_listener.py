import pytest
from unittest.mock import patch, Mock
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from email_listener import parse_interview_with_llm

@patch("email_listener.call_llm")
def test_parse_interview_with_llm_happy_path(mock_call_llm):
    """Test happy path where call_llm returns valid JSON."""
    mock_res = Mock()
    mock_res.text = '{"is_interview": true, "company_name": "Google", "job_role": "SWE", "date_time": "2026-08-27 15:00", "meeting_link": "https://meet.google.com/abc"}'
    mock_call_llm.return_value = mock_res

    result = parse_interview_with_llm("Subject", "Sender", "Body")

    assert result["is_interview"] is True
    assert result["company_name"] == "Google"
    assert result["job_role"] == "SWE"
    assert result["date_time"] == "2026-08-27 15:00"
    assert result["meeting_link"] == "https://meet.google.com/abc"
    mock_call_llm.assert_called_once()

@patch("email_listener.call_llm")
def test_parse_interview_with_llm_markdown_json(mock_call_llm):
    """Test happy path where call_llm returns valid JSON wrapped in markdown."""
    mock_res = Mock()
    mock_res.text = '''```json
{
  "is_interview": true,
  "company_name": "Meta",
  "job_role": "Data Scientist",
  "date_time": "2026-09-01 10:00",
  "meeting_link": ""
}
```'''
    mock_call_llm.return_value = mock_res

    result = parse_interview_with_llm("Subject", "Sender", "Body")

    assert result["is_interview"] is True
    assert result["company_name"] == "Meta"
    assert result["job_role"] == "Data Scientist"

@patch("email_listener.call_llm")
def test_parse_interview_with_llm_negative_path(mock_call_llm):
    """Test path where email is not an interview."""
    mock_res = Mock()
    mock_res.text = '{"is_interview": false, "company_name": "", "job_role": "", "date_time": "", "meeting_link": ""}'
    mock_call_llm.return_value = mock_res

    result = parse_interview_with_llm("Subject", "Sender", "Body")

    assert result["is_interview"] is False
    assert result["company_name"] == ""

@patch("email_listener.call_llm")
def test_parse_interview_with_llm_parsing_failure(mock_call_llm):
    """Test path where call_llm returns invalid JSON."""
    mock_res = Mock()
    mock_res.text = 'This is just some text, not JSON'
    mock_call_llm.return_value = mock_res

    result = parse_interview_with_llm("Subject", "Sender", "Body")

    assert result["is_interview"] is False

@patch("email_listener.call_llm")
def test_parse_interview_with_llm_exception(mock_call_llm):
    """Test path where call_llm raises an exception."""
    mock_call_llm.side_effect = Exception("API error")

    result = parse_interview_with_llm("Subject", "Sender", "Body")

    assert result["is_interview"] is False
