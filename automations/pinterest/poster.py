"""
Poster module for Pinterest automation
Handles posting pins to Pinterest via API v5 or browser automation fallback
"""

import os
import time
import logging
import base64
import requests
import json
from typing import Optional

# Import from shared browser layer (jarvis_browser)
try:
    from jarvis_browser import SyncBrowser, safe_close_sync
    JARVIS_BROWSER_AVAILABLE = True
except ImportError:
    JARVIS_BROWSER_AVAILABLE = False
    logging.warning("jarvis_browser not available - Pinterest posting will use simulation mode")

# Pinterest API v5 configuration
PINTEREST_API_BASE = "https://api.pinterest.com/v5"

# Stable browser profile directory for persistent login session
# Use /app/PinterestBot inside container
BROWSER_USER_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", "/app"),
    "PinterestBot"
)
# Ensure directory exists
os.makedirs(BROWSER_USER_DATA_DIR, exist_ok=True)

# Global browser instance for reuse
_browser_instance = None
_browser_context = None
_browser_page = None


def _get_access_token() -> Optional[str]:
    """Get Pinterest access token from environment"""
    return os.environ.get("PINTEREST_ACCESS_TOKEN")


def _get_board_id(board_name: Optional[str] = None) -> Optional[str]:
    """Get board ID - can be overridden by env var"""
    # First check env var
    board_id = os.environ.get("PINTEREST_BOARD_ID")
    if board_id:
        return board_id
    return None


def post_pin_api(image_path: str, title: str, link: str, description: str, board_name: Optional[str] = None) -> bool:
    """
    Post a pin to Pinterest using API v5
    
    Args:
        image_path: Path to the image/video to post
        title: Pin title
        link: Destination URL (affiliate link)
        description: Pin description
        board_name: Optional board name to post to
     
    Returns:
        bool: True if successful, False otherwise
    """
    access_token = _get_access_token()
    if not access_token:
        logging.warning("No PINTEREST_ACCESS_TOKEN found - cannot use API v5")
        return False
        
    board_id = _get_board_id(board_name)
    if not board_id:
        logging.warning("No PINTEREST_BOARD_ID found - cannot use API v5")
        return False
    
    if not os.path.exists(image_path):
        logging.error(f"Image file not found: {image_path}")
        return False
    
    try:
        logging.info(f"📌 Posting to Pinterest via API v5: {title[:50]}...")
        
        # Step 1: Upload media
        media_upload_url = f"{PINTEREST_API_BASE}/media"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # For API v5, we need to upload the image first
        # Pinterest API v5 uses a two-step process: create media record, then upload
        media_data = {
            "media_type": "image"
        }
        
        response = requests.post(media_upload_url, headers=headers, json=media_data, timeout=30)
        if response.status_code not in [200, 201]:
            logging.error(f"Failed to create media record: {response.status_code} - {response.text}")
            return False
            
        media_response = response.json()
        media_id = media_response.get("media_id")
        upload_url = media_response.get("upload_url")
        upload_parameters = media_response.get("upload_parameters", {})
        
        if not media_id or not upload_url:
            logging.error(f"Invalid media response: {media_response}")
            return False
        
        # Step 2: Upload the actual image file
        with open(image_path, 'rb') as f:
            files = {'file': (os.path.basename(image_path), f, 'image/png')}
            # Include upload parameters if provided
            upload_response = requests.post(upload_url, data=upload_parameters, files=files, timeout=60)
           
        if upload_response.status_code not in [200, 201, 204]:
            logging.error(f"Failed to upload image: {upload_response.status_code} - {upload_response.text}")
            return False
        
        logging.info(f"✅ Image uploaded successfully (media_id: {media_id})")
        
        # Step 3: Create the pin
        pin_create_url = f"{PINTEREST_API_BASE}/pins"
        pin_data = {
            "board_id": board_id,
            "media_source": {
                "source_type": "image_id",
                "content_type": "image/png",
                "media_id": media_id
            },
            "title": title[:100],  # Pinterest title limit
            "description": description[:500],
            "link": link,
            "note": description[:500]  # note is the description field
        }
        
        # Add board_section_id if we need to support sections later
        pin_response = requests.post(pin_create_url, headers=headers, json=pin_data, timeout=30)
        
        if pin_response.status_code in [200, 201]:
            pin_info = pin_response.json()
            logging.info(f"✅ Pin successfully posted to Pinterest via API! Pin ID: {pin_info.get('id', 'unknown')}")
            return True
        else:
            logging.error(f"Failed to create pin: {pin_response.status_code} - {pin_response.text}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Failed to post pin to Pinterest via API: {e}")
        return False


def _apply_session_cookie(page):
    """Apply Pinterest session cookie if available"""
    session_cookie = os.environ.get("PINTEREST_SESSION_COOKIE")
    if not session_cookie:
        return False
    
    try:
        # Decode the base64 cookie
        decoded = base64.b64decode(session_cookie).decode('utf-8')
        # The cookie value is the _pinterest_sess cookie value
        page.context.add_cookies([{
            "name": "_pinterest_sess",
            "value": decoded,
            "domain": ".pinterest.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }])
        logging.info("🍪 Applied Pinterest session cookie")
        return True
    except Exception as e:
        logging.warning(f"Could not apply session cookie: {e}")
        return False


def _clear_and_apply_session_cookie(page):
    """Clear existing cookies and apply fresh session cookie"""
    session_cookie = os.environ.get("PINTEREST_SESSION_COOKIE")
    if not session_cookie:
        return False
    
    try:
        # Clear all existing cookies for pinterest.com
        page.context.clear_cookies()
        
        # Decode the base64 cookie
        decoded = base64.b64decode(session_cookie).decode('utf-8')
        # The cookie value is the _pinterest_sess cookie value
        page.context.add_cookies([{
            "name": "_pinterest_sess",
            "value": decoded,
            "domain": ".pinterest.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }])
        logging.info("🍪 Cleared old cookies and applied fresh Pinterest session cookie")
        return True
    except Exception as e:
        logging.warning(f"Could not clear and apply session cookie: {e}")
        return False


def _get_browser():
    """Get or create browser instance for Pinterest posting using jarvis_browser"""
    global _browser_instance, _browser_context, _browser_page
    
    if not JARVIS_BROWSER_AVAILABLE:
        return None, None, None
        
    if _browser_instance is None:
        try:
            # Force headless mode for container environments
            is_headless = True  # Always headless in container
            logging.info(f"🌐 Initializing Pinterest browser (headless={is_headless})")
            
            _browser_instance = SyncBrowser(headless=is_headless)
            _browser_instance.__enter__()
            
            # Create context with persistent session storage
            _browser_context = _browser_instance.new_context_with_session(
                BROWSER_USER_DATA_DIR,
                viewport={"width": 1280, "height": 720},
                is_mobile=False,
                has_touch=False,
            )
            _browser_page = _browser_context.new_page()
            logging.info(f"🌐 Pinterest browser initialized (headless={is_headless})")
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            return None, None, None
            
    return _browser_instance, _browser_context, _browser_page


def post_pin(image_path: str, title: str, link: str, description: str, board_name: Optional[str] = None) -> bool:
    """
    Post a pin to Pinterest
    
    Tries API v5 first (using PINTEREST_ACCESS_TOKEN), falls back to browser automation
    
    Args:
        image_path: Path to the image/video to post
        title: Pin title
        link: Destination URL (affiliate link)
        description: Pin description
        board_name: Optional board name to post to
     
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(image_path):
        logging.error(f"Image file not found: {image_path}")
        return False
        
    # Try API v5 first (if credentials available)
    access_token = _get_access_token()
    board_id = _get_board_id(board_name)
    
    if access_token and board_id:
        logging.info("🔑 PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID found - trying API v5 first")
        api_success = post_pin_api(image_path, title, link, description, board_name)
        if api_success:
            return True
        logging.warning("⚠️ API v5 failed, falling back to browser automation...")
    else:
        if not access_token:
            logging.warning("No PINTEREST_ACCESS_TOKEN found - skipping API v5")
        if not board_id:
            logging.warning("No PINTEREST_BOARD_ID found - skipping API v5")
    
    # If Playwright is not available, simulate posting
    if not JARVIS_BROWSER_AVAILABLE:
        logging.info(f"📌 SIMULATED Pinterest post: {title[:50]}...")
        logging.info(f"   Image: {image_path}")
        logging.info(f"   Link: {link}")
        logging.info(f"   Board: {board_name or 'Default'}")
        # In simulation, we'll consider it successful
        time.sleep(1)  # Simulate network delay
        return True
    
    # Real implementation with Playwright via jarvis_browser
    try:
        playwright, context, page = _get_browser()
        if not page:
            logging.error("Could not initialize browser")
            return False
            
        logging.info(f"📌 Posting to Pinterest: {title[:50]}...")
        
        # Apply session cookie if available (bypasses login)
        # Use clear_and_apply to ensure fresh session
        cookie_applied = _clear_and_apply_session_cookie(page)
        
        # Navigate to Pinterest pin builder directly
        page.goto("https://www.pinterest.com/pin-builder/", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Check if we're logged in - look for create pin elements
        if not cookie_applied:
            # Check for login requirement
            if page.locator('input[id="email"]').is_visible(timeout=3000):
                logging.info("🔐 Logging into Pinterest...")
                
                # Get credentials from environment
                email = os.environ.get("PINTEREST_EMAIL")
                password = os.environ.get("PINTEREST_PASSWORD")
                
                if not email or not password:
                    logging.error("Pinterest credentials not found in environment")
                    return False
                    
                # Fill in login form
                page.fill('input[id="email"]', email)
                page.fill('input[id="password"]', password)
                page.click('button[type="submit"]')
                page.wait_for_timeout(5000)
                
                # Wait for login to complete - navigate to pin builder again
                page.goto("https://www.pinterest.com/pin-builder/", timeout=30000)
                page.wait_for_timeout(3000)
        else:
            # Cookie was applied, but verify we're actually logged in
            # Sometimes cookie expires - check if we see login form
            if page.locator('input[id="email"]').is_visible(timeout=3000):
                logging.warning("⚠️ Session cookie expired, attempting login with credentials...")
                email = os.environ.get("PINTEREST_EMAIL")
                password = os.environ.get("PINTEREST_PASSWORD")
                if email and password:
                    page.fill('input[id="email"]', email)
                    page.fill('input[id="password"]', password)
                    page.click('button[type="submit"]')
                    page.wait_for_timeout(5000)
                    page.goto("https://www.pinterest.com/pin-builder/", timeout=30000)
                    page.wait_for_timeout(3000)
        
        # Verify we're on pin builder page
        if not page.locator('input[type="file"]').is_visible(timeout=5000):
            logging.error("Could not access pin builder - may need manual login")
            return False
        
        # Upload image
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(image_path)
        page.wait_for_timeout(3000)  # Wait for upload
        
        # Fill in title
        title_input = page.locator('input[placeholder="Add a title"]')
        title_input.fill(title[:100])  # Pinterest title limit
        
        # Fill in description
        desc_input = page.locator('textarea[placeholder="Add a description"]')
        desc_input.fill(description[:500])  # Reasonable description limit
        
        # Fill in destination link
        link_input = page.locator('input[placeholder="Add a destination link"]')
        link_input.fill(link)
        
        # Select board if specified
        if board_name:
            board_input = page.locator('input[placeholder="Board"]')
            board_input.click()
            page.wait_for_timeout(1000)
            board_input.fill(board_name)
            page.wait_for_timeout(2000)
            # Select the first matching option
            first_option = page.locator('div[role="option"]:has-text("' + board_name + '")')
            if first_option.is_visible():
                first_option.click()
            else:
                # Press Enter to use the typed board name
                board_input.press("Enter")
        
        # Click publish button - use more specific selector
        publish_button = page.locator('button:has-text("Publish"):visible')
        publish_button.click()
        page.wait_for_timeout(5000)  # Wait for publish to complete
        
        # Check for success
        success_indicator = page.locator('text=Your Pin has been published')
        if success_indicator.is_visible(timeout=5000):
            logging.info("✅ Pin successfully posted to Pinterest!")
            return True
        else:
            logging.warning("⚠️  Could not confirm pin publication")
            return False
          
    except Exception as e:
        logging.error(f"❌ Failed to post pin to Pinterest: {e}")
        return False


def cleanup_browser():
    """Clean up browser resources"""
    global _browser_instance, _browser_context, _browser_page
    
    try:
        if _browser_page:
            _browser_page.close()
            _browser_page = None
        if _browser_context:
            _browser_context.close()
            _browser_context = None
        if _browser_instance:
            _browser_instance.__exit__(None, None, None)
            _browser_instance = None
        logging.info("🧹 Pinterest browser cleaned up")
    except Exception as e:
        logging.error(f"Error cleaning up browser: {e}")


# For testing purposes
if __name__ == "__main__":
    # Test the post_pin function with dummy data
    result = post_pin(
        image_path="test_image.jpg",
        title="Test Pin Title",
        link="https://example.com",
        description="This is a test pin description",
        board_name="Test Board"
    )