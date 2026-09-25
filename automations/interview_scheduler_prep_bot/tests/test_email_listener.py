import pytest
import json
from pathlib import Path

# Since email_listener imports from other modules in its directory and parent directory,
# it might be easier to patch its global variables after import.
from email_listener import get_processed_ids
import email_listener

def test_get_processed_ids_file_missing(tmp_path, monkeypatch):
    """Checks that an empty set is returned when the processed IDs file does not exist."""
    fake_file = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(email_listener, "PROCESSED_FILE", fake_file)

    result = get_processed_ids()
    assert result == set()

def test_get_processed_ids_valid_json(tmp_path, monkeypatch):
    """Checks that the correct set of IDs is returned when the file contains a valid JSON array."""
    fake_file = tmp_path / "processed_emails.json"
    fake_file.write_text('["id1", "id2", "id3"]', encoding="utf-8")
    monkeypatch.setattr(email_listener, "PROCESSED_FILE", fake_file)

    result = get_processed_ids()
    assert result == {"id1", "id2", "id3"}

def test_get_processed_ids_invalid_json(tmp_path, monkeypatch):
    """Checks that an empty set is returned when the file contains invalid JSON data."""
    fake_file = tmp_path / "processed_emails.json"
    fake_file.write_text('not valid json', encoding="utf-8")
    monkeypatch.setattr(email_listener, "PROCESSED_FILE", fake_file)

    result = get_processed_ids()
    assert result == set()
