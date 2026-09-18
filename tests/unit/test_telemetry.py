import pytest
from unittest.mock import patch, MagicMock
from telemetry import log_telemetry

def test_log_telemetry_success(capsys):
    with patch('telemetry.psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        log_telemetry("job-123", "SUCCESS", "42")

        # Verify connect was called with right arguments
        mock_connect.assert_called_once_with(dbname="jarvis", user="postgres", host="127.0.0.1")

        # Verify execute was called correctly
        assert mock_cursor.execute.call_count == 1
        args, kwargs = mock_cursor.execute.call_args
        # The query is the first arg, parameters are the second arg
        query = args[0]
        params = args[1]
        assert "INSERT INTO automation_telemetry (job_id, status, duration_seconds)" in query
        assert params == ("job-123", "SUCCESS", 42)

        # Verify commit and close were called
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

        # Check stdout output
        captured = capsys.readouterr()
        assert "Logged SUCCESS for job-123 (42s) to PostgreSQL." in captured.out

def test_log_telemetry_db_failure(capsys):
    with patch('telemetry.psycopg2.connect') as mock_connect:
        mock_connect.side_effect = Exception("DB Connection Error")

        log_telemetry("job-123", "SUCCESS", "42")

        # Check stdout output
        captured = capsys.readouterr()
        assert "Failed to log telemetry to PostgreSQL: DB Connection Error" in captured.out

def test_log_telemetry_invalid_duration(capsys):
    with patch('telemetry.psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        log_telemetry("job-123", "SUCCESS", "invalid")

        # The error will be ValueError when casting int("invalid")
        # Ensure it doesn't crash but logs the failure
        captured = capsys.readouterr()
        assert "Failed to log telemetry to PostgreSQL:" in captured.out

        # execute should not have been called because it fails at int(duration)
        mock_cursor.execute.assert_not_called()
