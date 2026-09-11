import pytest
from unittest.mock import patch, MagicMock
import json
from event_bus import EventBus

@pytest.fixture
def event_bus():
    return EventBus()

@patch('event_bus.psycopg2.connect')
def test_publish_success(mock_connect, event_bus):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    payload = {"key": "value"}
    result = event_bus.publish("pinterest.test", "pin_posted", payload)

    assert result is True
    mock_connect.assert_called_once_with(**event_bus.db_params)
    mock_conn.cursor.assert_called_once()
    mock_cur.execute.assert_called_once_with(
        "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
        ("pinterest", "pin_posted", json.dumps(payload))
    )
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('event_bus.psycopg2.connect')
def test_publish_no_dot_in_channel(mock_connect, event_bus):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    payload = {"key": "value"}
    result = event_bus.publish("system_channel", "sys_event", payload)

    assert result is True
    mock_cur.execute.assert_called_once_with(
        "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
        ("system_channel", "sys_event", json.dumps(payload))
    )

@patch('event_bus.psycopg2.connect')
def test_publish_connection_error(mock_connect, event_bus):
    mock_connect.side_effect = Exception("DB Connection Failed")

    payload = {"key": "value"}
    result = event_bus.publish("test", "test_event", payload)

    assert result is False
    mock_connect.assert_called_once()

@patch('event_bus.psycopg2.connect')
def test_publish_execute_error(mock_connect, event_bus):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    mock_cur.execute.side_effect = Exception("Execution Failed")

    payload = {"key": "value"}
    result = event_bus.publish("test", "test_event", payload)

    assert result is False
    mock_cur.execute.assert_called_once()
    mock_conn.commit.assert_not_called()
