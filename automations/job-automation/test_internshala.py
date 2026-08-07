import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path="/usr/bin/google-chrome")
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navigating to Internshala...")
        await page.goto("https://internshala.com/internships/", timeout=60000)
        
        # Get first job link
        job_link = await page.locator("a.job-title-href, .job-internship-name a, .heading_4_5 a").first.get_attribute("href")
        if job_link:
            full_url = "https://internshala.com" + job_link if not job_link.startswith("http") else job_link
            print(f"Job URL: {full_url}")
            await page.goto(full_url)
            
            print("Looking for apply button...")
            btns = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"]')).map(b => ({
                    text: b.innerText,
                    id: b.id,
                    className: b.className,
                    tagName: b.tagName
                })).filter(b => b.text && b.text.toLowerCase().includes("apply"));
            }''')
            print(f"Apply Buttons found: {json.dumps(btns, indent=2)}")
        else:
            print("No job link found.")
            
        await browser.close()

asyncio.run(main())
