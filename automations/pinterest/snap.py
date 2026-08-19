from playwright.sync_api import sync_playwright
import sys

def snap(url, out):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(3000)
        page.screenshot(path=out)
        browser.close()

if __name__ == "__main__":
    snap(sys.argv[1], sys.argv[2])
