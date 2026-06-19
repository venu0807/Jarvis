import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from shared_vision import solve_with_vision

def main():
    print("Starting Vision Integration Test...")
    
    # Make sure NVIDIA_API_KEY is available
    if not os.environ.get("NVIDIA_API_KEY"):
        print("\n[ERROR] NVIDIA_API_KEY is not set in environment or pinterest/.env!")
        print("Please add it to D:\\Proposals\\Jarvis\\automations\\pinterest\\.env")
        return

    html_path = Path(__file__).parent / "test_captcha.html"
    url = f"file://{html_path.resolve()}"
    
    with sync_playwright() as p:
        # Launch headful browser so we can watch it happen
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        
        print(f"Navigating to {url}")
        page.goto(url)
        
        # Wait 2 seconds just so you can see the fake CAPTCHA
        time.sleep(2)
        
        # Oh no! The script couldn't find the selector, let's call the Vision Fallback!
        try:
            print("\n[Simulated Playwright Error] page.locator('#hidden-selector').click() timed out.")
            solve_with_vision(page, "Click the green 'Click to Verify' button.")
            
            # Wait a few seconds to see the result
            time.sleep(3)
            print("\nTest Complete!")
            
        except Exception as e:
            print(f"\n[Test Failed] Error during vision fallback: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
