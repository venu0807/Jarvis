import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from lifecycle import health_check, Stage

def test_health_check_file_not_found():
    with patch("lifecycle._load") as mock_load:
        mock_load.side_effect = FileNotFoundError("automation not found: missing")
        result = health_check("missing")
        assert result == {"ok": False, "error": "automation not found: missing"}

def test_health_check_basic():
    with patch("lifecycle._load") as mock_load:
        mock_load.return_value = {
            "stage": Stage.DRAFT.value,
            "models": {"build": "gpt-4", "run": "gpt-3.5"},
            "schedule": "0 0 * * *"
        }
        result = health_check("test_auto")
        assert result["ok"] is True
        assert result["name"] == "test_auto"
        assert result["stage"] == Stage.DRAFT.value
        assert result["model_build"] == "gpt-4"
        assert result["model_run"] == "gpt-3.5"
        assert result["schedule"] == "0 0 * * *"
        assert result["cloud_violation"] is False
        assert result["last_dry"] is None
        assert result["draft_history_count"] == 0

def test_health_check_cloud_violation():
    with patch("lifecycle._load") as mock_load:
        mock_load.return_value = {
            "stage": Stage.LIVE.value,
            "models": {"run": "gpt-4"}
        }
        result = health_check("test_auto")
        assert result["ok"] is True
        assert result["cloud_violation"] is True

def test_health_check_no_cloud_violation():
    with patch("lifecycle._load") as mock_load:
        mock_load.return_value = {
            "stage": Stage.LIVE.value,
            "models": {"run": "ollama/llama3"}
        }
        result = health_check("test_auto")
        assert result["ok"] is True
        assert result["cloud_violation"] is False

def test_health_check_with_history():
    with patch("lifecycle._load") as mock_load:
        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        mock_load.return_value = {
            "stage": Stage.DRY.value,
            "models": {"run": "phi4"},
            "dry_runs": {
                "history": [
                    {
                        "ran_at": two_hours_ago.isoformat().replace("+00:00", "Z"),
                        "outcome": "PASS"
                    }
                ]
            }
        }
        result = health_check("test_auto")
        assert result["ok"] is True
        assert result["last_dry"] is not None
        assert result["last_dry"]["outcome"] == "PASS"
        assert 1.9 <= result["last_dry"]["age_h"] <= 2.1
        assert result["draft_history_count"] == 1

def test_health_check_invalid_history_date():
    with patch("lifecycle._load") as mock_load:
        mock_load.return_value = {
            "stage": Stage.DRAFT.value,
            "dry_runs": {
                "history": [
                    {
                        "ran_at": "invalid-date",
                        "outcome": "PASS"
                    }
                ]
            }
        }
        result = health_check("test_auto")
        assert result["ok"] is True
        assert result["last_dry"] is None
