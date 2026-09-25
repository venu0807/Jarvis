import datetime
import os
import builtins
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from automations.interview_scheduler_prep_bot.calendar_manager import add_interview_to_calendar

@pytest.fixture
def mock_output_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("automations.interview_scheduler_prep_bot.calendar_manager.OUTPUT_DIR", tmp_path)
    return tmp_path

# The module name has a hyphen 'job-automation', which breaks typical patch string imports.
# We will mock the import instead.
@pytest.fixture
def mock_telegram():
    original_import = builtins.__import__

    def side_effect(name, *args, **kwargs):
        if name == "telegram_notifier":
            mock_module = MagicMock()
            return mock_module
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=side_effect):
        yield

def test_add_interview_to_calendar_isoformat(mock_output_dir, mock_telegram):
    # Test with ISO format datetime
    company = "Tech Corp"
    dt_str = "2023-10-25T14:30:00"

    file_path = add_interview_to_calendar(company, dt_str)

    assert file_path.endswith(".ics")
    assert "Interview_Tech Corp_20231025.ics" in file_path

    # Check file content
    with open(file_path, "r") as f:
        content = f.read()

    assert "SUMMARY:Interview: Tech Corp" in content
    assert "DTSTART:20231025T143000" in content
    # Duration 45 mins by default
    assert "DTEND:20231025T151500" in content

def test_add_interview_to_calendar_custom_format(mock_output_dir, mock_telegram):
    # Test with "%Y-%m-%d %H:%M:%S" format
    company = "Innovate LLC"
    dt_str = "2023-11-15 09:00:00"

    file_path = add_interview_to_calendar(company, dt_str, duration_minutes=60)

    assert file_path.endswith(".ics")
    assert "Interview_Innovate LLC_20231115.ics" in file_path

    # Check file content
    with open(file_path, "r") as f:
        content = f.read()

    assert "SUMMARY:Interview: Innovate LLC" in content
    assert "DTSTART:20231115T090000" in content
    # Duration 60 mins
    assert "DTEND:20231115T100000" in content

def test_add_interview_to_calendar_invalid_format(mock_output_dir, mock_telegram):
    # Test with invalid format, should fallback to tomorrow
    company = "Future_Tech"
    dt_str = "invalid-date"

    now = datetime.datetime.now()
    expected_dt = now + datetime.timedelta(days=1)

    file_path = add_interview_to_calendar(company, dt_str)

    assert file_path.endswith(".ics")
    assert f"Interview_Future_Tech_{expected_dt.strftime('%Y%m%d')}.ics" in file_path

    # Check file content
    with open(file_path, "r") as f:
        content = f.read()

    assert "SUMMARY:Interview: Future_Tech" in content
    assert f"DTSTART:{expected_dt.strftime('%Y%m%dT%H%M%S')[:8]}" in content # Just check date part to avoid minute diffs

@patch("builtins.print")
def test_telegram_import_failure(mock_print, mock_output_dir):
    company = "Acme Corp"
    dt_str = "2024-01-01T10:00:00"

    original_import = builtins.__import__

    def side_effect(name, *args, **kwargs):
        if name == "telegram_notifier":
            raise Exception("Mocked Import Error")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=side_effect):
        file_path = add_interview_to_calendar(company, dt_str)

    # Verify the file was still created
    assert os.path.exists(file_path)
    # Check that it caught the exception and printed
    mock_print.assert_any_call("Note: Telegram alert skipped: Mocked Import Error")
