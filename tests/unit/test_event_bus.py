import unittest
from unittest.mock import patch
import logging

from event_bus import EventBus

class TestEventBus(unittest.TestCase):
    @patch('event_bus.psycopg2.connect')
    def test_publish_db_connection_failure(self, mock_connect):
        mock_connect.side_effect = Exception("DB Connection Failed")
        bus = EventBus()

        with self.assertLogs('event_bus', level='ERROR') as cm:
            result = bus.publish("test.channel", "test.event", {"data": "value"})

        self.assertFalse(result)
        self.assertTrue(any("Failed to save event to database: DB Connection Failed" in log for log in cm.output))

if __name__ == '__main__':
    unittest.main()
