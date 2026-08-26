from playwright.async_api import async_playwright
import asyncio

async def test():
    p = await async_playwright().__aenter__()
    b = await p.chromium.launch(headless=True)
    await b.close()
    print('Chromium works!')
    await p.__aexit__(None, None, None)

asyncio.run(test())
