import json
import pytest
from unittest.mock import patch, mock_open
from email_listener import save_processed_id, get_processed_ids

def test_save_processed_id_success(tmp_path):
    """Test successful saving of a processed ID."""
    test_file = tmp_path / "processed_emails.json"

    with patch("email_listener.PROCESSED_FILE", test_file):
        # Ensure it starts empty
        assert get_processed_ids() == set()

        # Save a new ID
        save_processed_id("test_id_1")

        # Verify it was saved
        assert get_processed_ids() == {"test_id_1"}

        # Check file content
        with open(test_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data == ["test_id_1"]

        # Save another ID
        save_processed_id("test_id_2")

        # Verify both are saved
        saved_ids = get_processed_ids()
        assert "test_id_1" in saved_ids
        assert "test_id_2" in saved_ids
        assert len(saved_ids) == 2

@patch("builtins.open", side_effect=Exception("Mocked write exception"))
def test_save_processed_id_exception(mock_file, capsys):
    """Test exception handling during file write."""
    # We don't patch PROCESSED_FILE here, just the open builtin
    with patch("email_listener.get_processed_ids", return_value={"test_id_1"}):
        save_processed_id("test_id_2")

        # Capture stdout to check if exception was printed
        captured = capsys.readouterr()
        assert "⚠️ Error saving processed ID: Mocked write exception" in captured.out
