import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from automations.interview_scheduler_prep_bot.prep_generator import generate_prep_sheet

@patch('automations.interview_scheduler_prep_bot.prep_generator.get_company_news')
@patch('automations.interview_scheduler_prep_bot.prep_generator.fetch_job_description')
@patch('automations.interview_scheduler_prep_bot.prep_generator.call_llm')
@patch('automations.interview_scheduler_prep_bot.prep_generator.PREP_DIR')
def test_generate_prep_sheet_success(mock_prep_dir, mock_call_llm, mock_fetch_job_description, mock_get_company_news, tmp_path):
    # Setup mocks
    mock_get_company_news.return_value = "Mock News"
    mock_fetch_job_description.return_value = ("Mock Title", "Mock JD")

    mock_llm_result = MagicMock()
    mock_llm_result.text = "Mock Markdown Content"
    mock_call_llm.return_value = mock_llm_result

    # Configure PREP_DIR mock to point to a temporary path
    mock_prep_dir.mkdir.return_value = None
    mock_prep_dir.__truediv__.side_effect = lambda x: tmp_path / x

    # Execute
    result = generate_prep_sheet("Test Company", "2026-01-01")

    # Assert
    assert result != ""
    assert "test_company_prep_sheet.md" in result

    # Verify file was written
    output_file = Path(result)
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "Mock Markdown Content"

    # Verify mock calls
    mock_get_company_news.assert_called_once_with("Test Company")
    mock_fetch_job_description.assert_called_once_with("Test Company")
    mock_call_llm.assert_called_once()

@patch('automations.interview_scheduler_prep_bot.prep_generator.get_company_news')
@patch('automations.interview_scheduler_prep_bot.prep_generator.fetch_job_description')
@patch('automations.interview_scheduler_prep_bot.prep_generator.call_llm')
@patch('automations.interview_scheduler_prep_bot.prep_generator.PREP_DIR')
def test_generate_prep_sheet_empty_llm_response(mock_prep_dir, mock_call_llm, mock_fetch_job_description, mock_get_company_news, tmp_path):
    # Setup mocks
    mock_get_company_news.return_value = "Mock News"
    mock_fetch_job_description.return_value = ("Mock Title", "Mock JD")

    mock_llm_result = MagicMock()
    mock_llm_result.text = "" # Empty text
    mock_call_llm.return_value = mock_llm_result

    # Configure PREP_DIR mock
    mock_prep_dir.mkdir.return_value = None
    mock_prep_dir.__truediv__.side_effect = lambda x: tmp_path / x

    # Execute
    result = generate_prep_sheet("Test Company", "2026-01-01")

    # Assert
    assert result == ""

    # Verify file was NOT written
    output_file = tmp_path / "test_company_prep_sheet.md"
    assert not output_file.exists()

@patch('automations.interview_scheduler_prep_bot.prep_generator.get_company_news')
@patch('automations.interview_scheduler_prep_bot.prep_generator.fetch_job_description')
@patch('automations.interview_scheduler_prep_bot.prep_generator.call_llm')
@patch('automations.interview_scheduler_prep_bot.prep_generator.PREP_DIR')
def test_generate_prep_sheet_llm_exception(mock_prep_dir, mock_call_llm, mock_fetch_job_description, mock_get_company_news, tmp_path):
    # Setup mocks
    mock_get_company_news.return_value = "Mock News"
    mock_fetch_job_description.return_value = ("Mock Title", "Mock JD")

    # LLM raises an exception
    mock_call_llm.side_effect = Exception("Ollama disconnected")

    # Configure PREP_DIR mock
    mock_prep_dir.mkdir.return_value = None
    mock_prep_dir.__truediv__.side_effect = lambda x: tmp_path / x

    # Execute
    result = generate_prep_sheet("Test Company", "2026-01-01")

    # Assert - should gracefully handle exception and return empty string
    assert result == ""

    # Verify file was NOT written
    output_file = tmp_path / "test_company_prep_sheet.md"
    assert not output_file.exists()
