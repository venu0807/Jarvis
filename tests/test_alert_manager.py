import json
import os
from unittest.mock import patch
import pytest

import alert_manager

@pytest.fixture
def temp_alert_file(tmp_path, monkeypatch):
    alert_file = tmp_path / "alerts.json"
    monkeypatch.setattr(alert_manager, "ALERT_FILE", str(alert_file))
    return alert_file

@patch("urllib.request.urlopen")
def test_add_alert_new_file(mock_urlopen, temp_alert_file):
    alert_manager.add_alert("TestJob", "Test Error")

    assert temp_alert_file.exists()
    with open(temp_alert_file, "r") as f:
        alerts = json.load(f)

    assert len(alerts) == 1
    assert alerts[0]["job"] == "TestJob"
    assert alerts[0]["message"] == "Test Error"
    assert "time" in alerts[0]

    mock_urlopen.assert_called_once()

@patch("urllib.request.urlopen")
def test_add_alert_existing_file(mock_urlopen, temp_alert_file):
    initial_alerts = [{"job": "OldJob", "time": "2023-01-01 00:00:00", "message": "Old Error"}]
    with open(temp_alert_file, "w") as f:
        json.dump(initial_alerts, f)

    alert_manager.add_alert("NewJob", "New Error")

    with open(temp_alert_file, "r") as f:
        alerts = json.load(f)

    assert len(alerts) == 2
    assert alerts[0]["job"] == "OldJob"
    assert alerts[1]["job"] == "NewJob"
    assert alerts[1]["message"] == "New Error"

    mock_urlopen.assert_called_once()

@patch("urllib.request.urlopen")
def test_add_alert_invalid_json_file(mock_urlopen, temp_alert_file):
    with open(temp_alert_file, "w") as f:
        f.write("invalid json {")

    alert_manager.add_alert("FixJob", "Fix Error")

    with open(temp_alert_file, "r") as f:
        alerts = json.load(f)

    assert len(alerts) == 1
    assert alerts[0]["job"] == "FixJob"

    mock_urlopen.assert_called_once()

@patch("urllib.request.urlopen")
def test_add_alert_webhook_failure(mock_urlopen, temp_alert_file, capsys):
    mock_urlopen.side_effect = Exception("Webhook down")

    alert_manager.add_alert("FailJob", "Fail Error")

    with open(temp_alert_file, "r") as f:
        alerts = json.load(f)

    assert len(alerts) == 1
    assert alerts[0]["job"] == "FailJob"

    captured = capsys.readouterr()
    assert "Failed to send webhook: Webhook down" in captured.out

def test_clear_alerts(temp_alert_file):
    initial_alerts = [{"job": "OldJob", "time": "2023-01-01 00:00:00", "message": "Old Error"}]
    with open(temp_alert_file, "w") as f:
        json.dump(initial_alerts, f)

    alert_manager.clear_alerts()

    with open(temp_alert_file, "r") as f:
        alerts = json.load(f)

    assert alerts == []
