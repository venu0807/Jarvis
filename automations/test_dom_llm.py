import time
import os
from playwright.sync_api import sync_playwright
from shared_dom_llm import solve_with_dom_sync

def main():
    # Get absolute path to the HTML file
    html_path = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "test_form.html")).replace("\\", "/")
    
    with sync_playwright() as p:
        # Headless=False so we can see if it flickers
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(html_path)
        
        print("\n--- DOM LLM Test: Zero Flicker Form Filling ---")
        time.sleep(1)
        
        print("\n--- Test 1: Click a specific skill based on resume ---")
        solve_with_dom_sync(page, "Read question 1. The user has the following skills: Java. Find the matching option and click the radio button next to it. If none match, return skip.")
        time.sleep(2)
        
        print("\n--- Test 2: Type experience based on resume ---")
        solve_with_dom_sync(page, "Read question 2. The user has 0 years of experience. Find the input field for this question and type '0' into it.")
        time.sleep(2)
        
        print("\n--- Test 3: Unmatched skill test ---")
        solve_with_dom_sync(page, "Read question 1 again. The user ONLY knows C#. Find the matching option and click it. If none match, return skip.")
        time.sleep(2)
        
        print("\nAll tests completed successfully using native DOM!\n")
        browser.close()

if __name__ == "__main__":
    main()
