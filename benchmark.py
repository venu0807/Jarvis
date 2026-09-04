import sys
import time
import asyncio
from unittest.mock import MagicMock

mock_requests = MagicMock()

class MockResponse:
    status_code = 200

def slow_get(*args, **kwargs):
    time.sleep(1)
    return MockResponse()

mock_requests.get = slow_get
sys.modules['requests'] = mock_requests

from automations.pinterest.platforms.pinterest import PinterestPlatform

async def run_benchmark():
    platform = PinterestPlatform({"credentials": {"access_token": "dummy_token", "board_id": "dummy_board"}})

    start_time = time.time()
    tasks = [platform.authenticate() for _ in range(5)]
    await asyncio.gather(*tasks)
    end_time = time.time()

    print(f"Time taken (requests - blocking): {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
