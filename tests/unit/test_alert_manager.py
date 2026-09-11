import pytest
from unittest.mock import patch, mock_open
import json
import urllib.error

# Import the module to test
from alert_manager import add_alert

@patch('alert_manager.open', new_callable=mock_open)
@patch('alert_manager.os.path.exists', return_value=False)
@patch('urllib.request.urlopen')
def test_add_alert_webhook_failure(mock_urlopen, mock_exists, mock_file, capsys):
    # Simulate urllib.request.urlopen raising a URLError
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

    # Call the function
    add_alert("TestJob", "Test Error Message")

    # Check that it printed the failure message without crashing
    captured = capsys.readouterr()
    assert "Failed to send webhook:" in captured.out

    # Verify the mock was called
    mock_urlopen.assert_called_once()
