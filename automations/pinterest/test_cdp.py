from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("ws://127.0.0.1:9222")
        print("Connected! Contexts:", len(browser.contexts))
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        page.goto("https://bot.sannysoft.com")
        print("Page title:", page.title())
        page.screenshot(path="test_obscura.png")
        print("Screenshot saved to test_obscura.png")
        
if __name__ == "__main__":
    test()
