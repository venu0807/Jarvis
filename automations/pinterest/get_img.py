import asyncio
from playwright.async_api import async_playwright

async def get_amazon_img():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.amazon.in/dp/B0F7Y54PJX")
        img = await page.locator("#landingImage").get_attribute("src")
        print("IMG:", img)
        hires = await page.locator("#landingImage").get_attribute("data-old-hires")
        if hires: print("HIRES:", hires)
        await browser.close()

asyncio.run(get_amazon_img())
