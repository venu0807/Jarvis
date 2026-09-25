import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sqlite3

from automations.interview_scheduler_prep_bot.prep_generator import fetch_job_description

def test_fetch_job_description_no_db():
    """Test when the database file does not exist."""
    with patch("automations.interview_scheduler_prep_bot.prep_generator.DB_PATH") as mock_db_path:
        mock_db_path.exists.return_value = False
        title, desc = fetch_job_description("Test Company")
        assert title == "Software Developer / Tester"
        assert desc == ""

def test_fetch_job_description_found():
    """Test successfully finding a job description in the database."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("Senior Developer", "Job description here")
    mock_conn.__enter__.return_value.execute.return_value = mock_cursor

    with patch("automations.interview_scheduler_prep_bot.prep_generator.DB_PATH") as mock_db_path, \
         patch("automations.interview_scheduler_prep_bot.prep_generator.sqlite3.connect", return_value=mock_conn):
        mock_db_path.exists.return_value = True
        title, desc = fetch_job_description("Test Company")
        assert title == "Senior Developer"
        assert desc == "Job description here"

def test_fetch_job_description_not_found():
    """Test when the database query returns no matching rows."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.__enter__.return_value.execute.return_value = mock_cursor

    with patch("automations.interview_scheduler_prep_bot.prep_generator.DB_PATH") as mock_db_path, \
         patch("automations.interview_scheduler_prep_bot.prep_generator.sqlite3.connect", return_value=mock_conn):
        mock_db_path.exists.return_value = True
        title, desc = fetch_job_description("Test Company")
        assert title == "Software Tester / QA & Python Developer"
        assert desc == ""

def test_fetch_job_description_db_error():
    """Test handling of a database error during querying."""
    mock_conn = MagicMock()
    mock_conn.__enter__.side_effect = sqlite3.Error("Test DB Error")

    with patch("automations.interview_scheduler_prep_bot.prep_generator.DB_PATH") as mock_db_path, \
         patch("automations.interview_scheduler_prep_bot.prep_generator.sqlite3.connect", return_value=mock_conn):
        mock_db_path.exists.return_value = True
        title, desc = fetch_job_description("Test Company")
        assert title == "Software Tester / QA & Python Developer"
        assert desc == ""

def test_fetch_job_description_cleans_company_name():
    """Test that corporate suffixes are correctly cleaned from the company name."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("Dev", "Desc")
    mock_conn.__enter__.return_value.execute.return_value = mock_cursor

    with patch("automations.interview_scheduler_prep_bot.prep_generator.DB_PATH") as mock_db_path, \
         patch("automations.interview_scheduler_prep_bot.prep_generator.sqlite3.connect", return_value=mock_conn):
        mock_db_path.exists.return_value = True

        # Test cleaning out 'pvt', 'ltd', 'technologies' etc.
        fetch_job_description("Acme Technologies Pvt Ltd")

        # Check what arguments were passed to execute
        mock_conn.__enter__.return_value.execute.assert_called_with(
            "SELECT title, description FROM jobs WHERE company LIKE ? OR company LIKE ? ORDER BY id DESC LIMIT 1",
            ("%Acme%", "%Acme%")
        )
