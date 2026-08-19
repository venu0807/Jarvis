import os
import time
import random
from jarvis_browser import SyncBrowser

USER_DATA_DIR = os.path.join(os.getcwd(), "playwright_data")

# These are high-traffic keywords perfect for a student demographic
TRENDY_KEYWORDS = [
    "aesthetic dorm decor",
    "student study hacks",
    "college tech essentials",
    "study motivation",
    "aesthetic desk setup",
    "ipad notes aesthetic"
]

def repin_trending(num_pins=5):
    keyword = random.choice(TRENDY_KEYWORDS)
    print("\n=====================================")
    print("   TRENDING REPINNER BOT STARTING    ")
    print("=====================================")
    print(f"Selected trendy keyword for this run: '{keyword}'")
    
    try:
        with SyncBrowser(headless=True) as browser_mgr:
            context = browser_mgr.new_context_with_session(
                USER_DATA_DIR,
                viewport={"width": 1280, "height": 800},
                is_mobile=False,
                has_touch=False,
            )
            
            page = context.new_page()
            
            # 1. Navigate to Pinterest Search
            search_url = f"https://www.pinterest.com/search/pins/?q={keyword.replace(' ', '%20')}"
            print(f"Navigating to {search_url}...")
            page.goto(search_url)
            page.wait_for_load_state("domcontentloaded")
            
            # Check login
            if "login" in page.url:
                print("Error: You are not logged in! Please run main.py first to do your initial login.")
                return
                
            print("Searching for the most popular pins...")
            time.sleep(6) # Give the images time to fully load on screen
            
            # 2. Find Pin elements on the screen
            pins = page.locator('div[data-test-id="pin"]').all()
            
            if not pins:
                print("Could not find any pins on the page. Pinterest might be loading slowly.")
                return
                
            saved_count = 0
            
            # 3. Hover and Save Pins
            for i in range(min(num_pins, len(pins))):
                pin = pins[i]
                try:
                    # Hover over the image to make the Save button appear
                    pin.hover()
                    time.sleep(1.5)
                    
                    # Look for the red Save button that pops up
                    save_btn = pin.get_by_role("button", name="Save").first
                       
                    if save_btn.is_visible():
                        save_btn.click()
                        print(f"[{saved_count+1}/{num_pins}] Successfully saved a trending image!")
                        saved_count += 1
                        time.sleep(random.uniform(3, 6)) # Random delay looks like a real human
                    else:
                        print(f"[{saved_count+1}/{num_pins}] Save button not visible, skipping...")
                except Exception as e:
                    print(f"Failed to save a pin: {e}")
                   
            print(f"\nDone! Automatically grabbed {saved_count} highly trendy images to boost your profile.")
            
            # Save session
            browser_mgr.save_session(context, USER_DATA_DIR)

    except Exception as e:
        print(f"Error in Repinner: {e}")

if __name__ == "__main__":
    repin_trending(num_pins=3)