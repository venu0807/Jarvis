import pytest
from unittest.mock import patch, mock_open
import sys
import os
from pathlib import Path

# Setup path so we can import email_listener
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import email_listener

@patch('email_listener.get_processed_ids')
@patch('builtins.open')
def test_save_processed_id_error_path(mock_open, mock_get_processed_ids, capsys):
    """Test that save_processed_id handles file write errors gracefully without crashing."""
    # Setup mock to return a test set
    mock_get_processed_ids.return_value = set(["old_id"])

    # Setup mock_open to raise PermissionError
    mock_open.side_effect = PermissionError("Permission denied")

    # Call the function
    email_listener.save_processed_id("new_id")

    # Verify no exception was raised

    # Capture standard output and verify the print statement
    captured = capsys.readouterr()
    assert "⚠️ Error saving processed ID: Permission denied" in captured.out

    # Verify the mock was called with the correct file path
    mock_open.assert_called_once_with(email_listener.PROCESSED_FILE, "w", encoding="utf-8")
