import pytest
from unittest.mock import patch, MagicMock
from datetime import timezone
import lifecycle
from lifecycle import Stage

@pytest.fixture
def mock_load():
    with patch("lifecycle._load") as m:
        yield m

@pytest.fixture
def mock_save():
    with patch("lifecycle._save") as m:
        yield m

@pytest.fixture
def mock_now():
    with patch("lifecycle._now") as m:
        m.return_value = "2023-10-01T12:00:00Z"
        yield m

def test_tear_down_file_not_found(mock_load):
    mock_load.side_effect = FileNotFoundError("file not found")

    result = lifecycle.tear_down("non_existent")

    assert result.ok is False
    assert result.message == "file not found"
    mock_load.assert_called_once_with("non_existent")

@patch("lifecycle.datetime")
@patch("lifecycle.Path.mkdir")
@patch("lifecycle.shutil.copy2")
def test_tear_down_with_archive(mock_copy2, mock_mkdir, mock_datetime, mock_load, mock_save, mock_now):
    # Setup mock data
    mock_data = {"stage": Stage.LIVE.value, "schedule": "0 0 * * *"}
    mock_load.return_value = mock_data

    # Setup mock datetime
    mock_now_dt = MagicMock()
    mock_now_dt.strftime.return_value = "20231001-120000"
    mock_datetime.now.return_value = mock_now_dt

    # Run the function
    result = lifecycle.tear_down("test_auto", archive=True)

    # Assertions
    assert result.ok is True
    assert "torn down to draft, archived" in result.message

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_datetime.now.assert_called_once_with(timezone.utc)

    # Check shutil.copy2 call
    mock_copy2.assert_called_once()
    args, kwargs = mock_copy2.call_args
    src, dst = args
    assert src.name == "test_auto.yaml"
    assert dst.name == "test_auto.20231001-120000.yaml"

    # Check data modifications
    assert mock_data["stage"] == Stage.DRAFT.value
    assert mock_data["schedule"] is None
    assert mock_data["updated"] == "2023-10-01T12:00:00Z"
    assert mock_data["torn_down_at"] == "2023-10-01T12:00:00Z"

    # Check save call
    mock_save.assert_called_once_with("test_auto", mock_data)

@patch("lifecycle.Path.mkdir")
@patch("lifecycle.shutil.copy2")
def test_tear_down_without_archive(mock_copy2, mock_mkdir, mock_load, mock_save, mock_now):
    mock_data = {"stage": Stage.LIVE.value, "schedule": "0 0 * * *"}
    mock_load.return_value = mock_data

    result = lifecycle.tear_down("test_auto", archive=False)

    assert result.ok is True

    mock_mkdir.assert_not_called()
    mock_copy2.assert_not_called()

    assert mock_data["stage"] == Stage.DRAFT.value
    assert mock_data["schedule"] is None

    mock_save.assert_called_once_with("test_auto", mock_data)

def test_tear_down_no_schedule(mock_load, mock_save, mock_now):
    # Test without schedule key
    mock_data = {"stage": Stage.LIVE.value}
    mock_load.return_value = mock_data

    # We can use archive=False to skip archiving checks
    result = lifecycle.tear_down("test_auto", archive=False)

    assert result.ok is True
    assert "schedule" not in mock_data
    assert mock_data["stage"] == Stage.DRAFT.value

    mock_save.assert_called_once_with("test_auto", mock_data)
