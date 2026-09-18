import os
import json
import pytest
from unittest.mock import patch, mock_open

# We need to import the module to patch its variables
import alert_manager

@pytest.fixture
def mock_alert_file(tmp_path):
    # Create a temporary file path
    temp_file = tmp_path / "alerts.json"

    # Patch the global ALERT_FILE in alert_manager
    with patch('alert_manager.ALERT_FILE', str(temp_file)):
        yield str(temp_file)

@patch('urllib.request.urlopen')
def test_add_alert_file_does_not_exist(mock_urlopen, mock_alert_file):
    # Ensure file doesn't exist initially
    assert not os.path.exists(mock_alert_file)

    alert_manager.add_alert("TestJob", "Test error message")

    # Check that file was created
    assert os.path.exists(mock_alert_file)

    # Check file contents
    with open(mock_alert_file, 'r') as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["job"] == "TestJob"
        assert data[0]["message"] == "Test error message"
        assert "time" in data[0]

@patch('urllib.request.urlopen')
def test_add_alert_file_exists_valid_json(mock_urlopen, mock_alert_file):
    # Create existing file with valid json
    initial_data = [{"job": "OldJob", "time": "2023-01-01 00:00:00", "message": "Old error"}]
    with open(mock_alert_file, 'w') as f:
        json.dump(initial_data, f)

    alert_manager.add_alert("TestJob", "Test error message")

    # Check file contents
    with open(mock_alert_file, 'r') as f:
        data = json.load(f)
        assert len(data) == 2
        assert data[0]["job"] == "OldJob"
        assert data[1]["job"] == "TestJob"
        assert data[1]["message"] == "Test error message"

@patch('urllib.request.urlopen')
def test_add_alert_file_exists_invalid_json(mock_urlopen, mock_alert_file):
    # Create existing file with invalid json
    with open(mock_alert_file, 'w') as f:
        f.write("invalid json data")

    alert_manager.add_alert("TestJob", "Test error message")

    # Check file contents - it should ignore the invalid json and start fresh
    with open(mock_alert_file, 'r') as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["job"] == "TestJob"
        assert data[0]["message"] == "Test error message"

@patch('urllib.request.urlopen')
def test_add_alert_webhook_success(mock_urlopen, mock_alert_file):
    # It should not raise an exception
    alert_manager.add_alert("TestJob", "Test error message")

    # Verify urlopen was called once
    assert mock_urlopen.called
    assert mock_urlopen.call_count == 1

@patch('urllib.request.urlopen')
def test_add_alert_webhook_failure(mock_urlopen, mock_alert_file, capsys):
    # Configure mock to raise an exception
    mock_urlopen.side_effect = Exception("Webhook failed!")

    # It should catch the exception and print a message
    alert_manager.add_alert("TestJob", "Test error message")

    # Verify urlopen was called
    assert mock_urlopen.called

    # Verify error message was printed
    captured = capsys.readouterr()
    assert "Failed to send webhook: Webhook failed!" in captured.out
