import time
from jarvis_browser import SyncBrowser

def test_scrape():
    with SyncBrowser(headless=False) as browser:
        context = browser.new_context()
        page = context.new_page()
        page.goto('https://trends.pinterest.com/', timeout=60000)
        print("Waiting for trends to load...")
        time.sleep(5)
        # find all spans or divs that look like trend names
        # usually they are in a list or table.
        text_content = page.content()
        import re
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text_content, 'html.parser')
        texts = soup.get_text(separator='\n').split('\n')
        keywords = []
        for t in texts:
            if len(t.strip()) > 3 and len(t.strip()) < 40:
                keywords.append(t.strip())
        print("Potential keywords:", set(keywords[:50]))
        
if __name__ == '__main__':
    test_scrape()
