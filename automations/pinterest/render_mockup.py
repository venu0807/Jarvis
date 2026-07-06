import asyncio
from playwright.async_api import async_playwright

async def render():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1000, "height": 1500})
        await page.goto("file:///mnt/c/Users/Venu/.gemini/antigravity-ide/brain/4b852682-1a1a-435a-b1ed-d025b90d2ffe/mockup.html")
        await page.wait_for_timeout(2000) # Wait for web fonts and images to load
        await page.screenshot(path="/mnt/c/Users/Venu/.gemini/antigravity-ide/brain/4b852682-1a1a-435a-b1ed-d025b90d2ffe/test_html_aesthetic.jpg", type="jpeg", quality=95)
        await browser.close()

asyncio.run(render())
