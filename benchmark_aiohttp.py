import sys
import time
import asyncio
from unittest.mock import MagicMock

# Create a mock aiohttp ClientSession
mock_aiohttp = MagicMock()

class MockClientResponse:
    status = 200

class MockClientSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def get(self, *args, **kwargs):
        class ContextManager:
            async def __aenter__(self):
                await asyncio.sleep(1)
                return MockClientResponse()
            async def __aexit__(self, *args):
                pass
        return ContextManager()

mock_aiohttp.ClientSession = MockClientSession
sys.modules['aiohttp'] = mock_aiohttp

class MockPinterestPlatform:
    def __init__(self):
        self.use_api = True
        self.access_token = "dummy"

    async def authenticate(self) -> bool:
        if self.use_api:
            try:
                import aiohttp
                headers = {"Authorization": f"Bearer {self.access_token}"}
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.pinterest.com/v5/user_account",
                        headers=headers,
                        timeout=10
                    ) as resp:
                        return resp.status == 200
            except Exception as e:
                print(e)
                return False
        return True

async def run_benchmark():
    platform = MockPinterestPlatform()

    start_time = time.time()
    tasks = [platform.authenticate() for _ in range(5)]
    await asyncio.gather(*tasks)
    end_time = time.time()

    print(f"Time taken (aiohttp - non-blocking): {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
