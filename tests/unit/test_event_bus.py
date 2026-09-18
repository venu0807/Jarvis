import json
import logging
from unittest.mock import patch, MagicMock

from event_bus import EventBus

def test_publish_success(caplog):
    caplog.set_level(logging.INFO)
    bus = EventBus()

    with patch('event_bus.psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        payload = {"foo": "bar"}
        result = bus.publish("test.channel", "test.event", payload)

        assert result is True
        mock_connect.assert_called_once_with(**bus.db_params)
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
            ("test", "test.event", json.dumps(payload))
        )
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

        assert "Successfully saved test.event to PostgreSQL Jarvis Memory!" in caplog.text

def test_publish_connection_failure(caplog):
    caplog.set_level(logging.ERROR)
    bus = EventBus()

    with patch('event_bus.psycopg2.connect') as mock_connect:
        mock_connect.side_effect = Exception("DB Connection Error")

        payload = {"foo": "bar"}
        result = bus.publish("test.channel", "test.event", payload)

        assert result is False
        assert "Failed to save event to database: DB Connection Error" in caplog.text

def test_publish_execute_failure(caplog):
    caplog.set_level(logging.ERROR)
    bus = EventBus()

    with patch('event_bus.psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Execute Error")

        payload = {"foo": "bar"}
        result = bus.publish("test.channel", "test.event", payload)

        assert result is False
        assert "Failed to save event to database: DB Execute Error" in caplog.text
        mock_conn.commit.assert_not_called()
