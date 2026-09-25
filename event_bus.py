import json
import os
import psycopg2
import logging
from typing import Any, Dict

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        # We now connect directly to PostgreSQL instead of Redis!
        self.db_params = {
            'dbname': os.getenv('JARVIS_DB_NAME', 'pinterest_db'),
            'user': os.getenv('JARVIS_DB_USER', 'venu'),
            'password': os.getenv('JARVIS_DB_PASS', 'venu'),
            'host': os.getenv('JARVIS_DB_HOST', '127.0.0.1')
        }

    def publish(self, channel: str, event_type: str, payload: Dict[str, Any]) -> bool:
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            
            # The channel (e.g. 'pinterest.*') isn't really needed for DB, we use event_type
            source = channel.split('.')[0] if '.' in channel else channel
            
            # Insert the event directly into Jarvis's brain!
            cur.execute(
                "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
                (source, event_type, json.dumps(payload))
            )
            conn.commit()
            conn.close()
            logger.info(f"✅ Successfully saved {event_type} to PostgreSQL Jarvis Memory!")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save event to database: {e}")
            return False

# Global instance for easy import
_bus_instance = None

def get_bus() -> EventBus:
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance
