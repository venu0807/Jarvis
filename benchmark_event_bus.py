import time
import sys
from unittest.mock import MagicMock

# Mock psycopg2
mock_psycopg2 = MagicMock()
class MockConn:
    def __init__(self):
        self.closed = False
        self.autocommit = False
        time.sleep(0.01) # Simulate connection delay
    def cursor(self):
        return MockCursor()
    def close(self):
        self.closed = True

class MockCursor:
    def execute(self, *args, **kwargs):
        time.sleep(0.001) # Simulate query delay
    def fetchall(self):
        return []

mock_psycopg2.connect = lambda **kwargs: MockConn()
sys.modules['psycopg2'] = mock_psycopg2

from automations.event_bus import EventBus

def benchmark_listen_loop_logic(is_optimized=False):
    bus = EventBus()
    count = 0
    start_time = time.time()

    # Simulate the loop logic
    if not is_optimized:
        for _ in range(100):
            conn = mock_psycopg2.connect(**bus.db_params)
            cur = conn.cursor()
            cur.execute(
                "SELECT id, payload FROM events WHERE event_type = %s AND id > %s ORDER BY id ASC",
                ("test_event", 0)
            )
            rows = cur.fetchall()
            conn.close()
    else:
        conn = None
        for _ in range(100):
            if conn is None or conn.closed:
                conn = mock_psycopg2.connect(**bus.db_params)
                conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                "SELECT id, payload FROM events WHERE event_type = %s AND id > %s ORDER BY id ASC",
                ("test_event", 0)
            )
            rows = cur.fetchall()
        if conn and not conn.closed:
            conn.close()

    end_time = time.time()
    return end_time - start_time

if __name__ == '__main__':
    unoptimized = benchmark_listen_loop_logic(is_optimized=False)
    print(f"Unoptimized loop (100 iterations): {unoptimized:.4f} seconds")

    optimized = benchmark_listen_loop_logic(is_optimized=True)
    print(f"Optimized loop (100 iterations): {optimized:.4f} seconds")

    print(f"Improvement: {unoptimized / optimized:.2f}x faster")
