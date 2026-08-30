import json
import pytest
from unittest.mock import patch, MagicMock
from event_bus import EventBus

@patch('event_bus.psycopg2.connect')
def test_publish_success(mock_connect):
    # Setup mock
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_connect.return_value = mock_conn

    # Execute
    bus = EventBus()
    payload = {"company": "Google", "title": "Software Engineer"}
    result = bus.publish("jobs.test", "jobs.applied", payload)

    # Verify
    assert result is True
    mock_connect.assert_called_once_with(**bus.db_params)
    mock_conn.cursor.assert_called_once()

    # Check channel splitting (jobs.test -> jobs)
    expected_source = "jobs"
    mock_cur.execute.assert_called_once_with(
        "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
        (expected_source, "jobs.applied", json.dumps(payload))
    )

    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('event_bus.psycopg2.connect')
def test_publish_success_no_split(mock_connect):
    # Setup mock
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_connect.return_value = mock_conn

    # Execute
    bus = EventBus()
    payload = {"product": "Neon Lamp"}
    result = bus.publish("pinterest", "pinterest.pin_posted", payload)

    # Verify
    assert result is True

    # Check channel with no split
    expected_source = "pinterest"
    mock_cur.execute.assert_called_once_with(
        "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
        (expected_source, "pinterest.pin_posted", json.dumps(payload))
    )

@patch('event_bus.psycopg2.connect')
def test_publish_failure(mock_connect):
    # Setup mock to raise exception
    mock_connect.side_effect = Exception("Database connection failed")

    # Execute
    bus = EventBus()
    payload = {"test": "data"}
    result = bus.publish("test.channel", "test.event", payload)

    # Verify
    assert result is False
    mock_connect.assert_called_once()
