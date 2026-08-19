import json
import os
import psycopg2
import logging
import threading
import time
from typing import Callable, Any, Dict, Optional

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
        self._subscribers: Dict[str, list[Callable[[Dict[str, Any]], None]]] = {}
        self._listen_thread: Optional[threading.Thread] = None
        self._stop_listen = threading.Event()

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
            
            # Also trigger local subscribers synchronously
            if event_type in self._subscribers:
                for callback in self._subscribers[event_type]:
                    try:
                        callback(payload)
                    except Exception as e:
                        logger.error(f"Subscriber error for {event_type}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save event to database: {e}")
            return False

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to an event type with a callback function."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"📡 Subscribed to {event_type}")

    def listen(self, event_type: str, callback: Callable[[Dict[str, Any]], None], poll_interval: float = 5.0) -> None:
        """Start a background thread that polls the database for new events."""
        self.subscribe(event_type, callback)
        
        def poll_loop():
            last_id = 0
            while not self._stop_listen.is_set():
                try:
                    conn = psycopg2.connect(**self.db_params)
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT id, payload FROM events WHERE event_type = %s AND id > %s ORDER BY id ASC",
                        (event_type, last_id)
                    )
                    rows = cur.fetchall()
                    conn.close()
                    
                    for row_id, payload in rows:
                        if isinstance(payload, str):
                            payload = json.loads(payload)
                        try:
                            callback(payload)
                        except Exception as e:
                            logger.error(f"Callback error for {event_type}: {e}")
                        last_id = max(last_id, row_id)
                except Exception as e:
                    logger.error(f"Poll error for {event_type}: {e}")
                time.sleep(poll_interval)
        
        self._listen_thread = threading.Thread(target=poll_loop, daemon=True)
        self._listen_thread.start()
        logger.info(f"👂 Listening for {event_type} events (poll every {poll_interval}s)")

    def stop_listen(self) -> None:
        """Stop the background listener thread."""
        self._stop_listen.set()
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)

# Global instance for easy import
_bus_instance = None

def get_bus() -> EventBus:
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance