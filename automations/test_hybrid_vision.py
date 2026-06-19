import os
import base64
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

load_dotenv(Path(__file__).parent / "pinterest" / ".env")

def get_nvidia_key():
    return os.environ.get("NVIDIA_API_KEY")

def _build_payload(base64_image, width, height, instruction):
    system_prompt = (
        "You are an expert robotic automation agent. You are looking at a screenshot of a web browser.\n"
        f"The viewport size is {width}x{height} pixels.\n"
        "Your goal is to answer the user's instruction based on what you see on the screen.\n"
        "You must output ONLY valid JSON.\n"
        "Schema options:\n"
        "1. If you need to click something (like a radio button or checkbox): {\"action\": \"click_text\", \"text\": \"exact text of the label or button\"}\n"
        "2. If you need to type text into an input field: {\"action\": \"type\", \"x\": int, \"y\": int, \"text\": \"value to type\"}\n"
        "3. If you should skip or do nothing: {\"action\": \"skip\"}\n"
        "Do not output markdown block ticks, just the raw JSON."
    )
    return {
        "model": "meta/llama-3.2-90b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{system_prompt}\n\nInstruction: {instruction}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1
    }

def solve_with_hybrid_vision(page, instruction: str):
    print(f"\n[Vision] Analyzing screen for instruction: '{instruction}'")
    screenshot_bytes = page.screenshot(animations="disabled", caret="hide")
    base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
    viewport = page.viewport_size
    width = viewport['width'] if viewport else 1366
    height = viewport['height'] if viewport else 768
    
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {get_nvidia_key()}", "Content-Type": "application/json", "Accept": "application/json"}
    payload = _build_payload(base64_image, width, height, instruction)
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"API Error {response.status_code}: {response.text}")
        return
        
    content = response.json()['choices'][0]['message']['content'].strip()
    if content.startswith("```json"):
        content = content.replace("```json", "").replace("```", "").strip()
    elif content.startswith("```"):
         content = content.replace("```", "").strip()
         
    print(f"  -> Nvidia Model Output: {content}")
    
    # Extract JSON string
    start_idx = content.find('{')
    end_idx = content.rfind('}')
    if start_idx != -1 and end_idx != -1:
        json_str = content[start_idx:end_idx+1]
    else:
        json_str = content
        
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {json_str}")
        return
        
    action = data.get('action')
    
    if action == 'click':
        print(f"  -> Executing CLICK at ({data['x']}, {data['y']})")
        page.mouse.click(data['x'], data['y'])
    elif action == 'click_text':
        print(f"  -> Executing CLICK_TEXT (BBox) for '{data['text']}'")
        el = page.get_by_text(data['text']).first
        if el:
            box = el.bounding_box()
            if box:
                target_x = box['x'] + (box['width'] / 2)
                target_y = box['y'] + (box['height'] / 2)
                page.mouse.click(target_x, target_y)
                print(f"  -> BBox click executed at ({target_x}, {target_y})")
            else:
                print("  -> Bounding box not visible.")
        else:
            print("  -> Element not found.")
    elif action == 'type':
        print(f"  -> Executing TYPE at ({data['x']}, {data['y']}) with text: '{data['text']}'")
        page.mouse.click(data['x'], data['y'])
        page.keyboard.type(data['text'])
    elif action == 'skip':
        print("  -> Executing SKIP")
    else:
        print(f"  -> Unknown action: {action}")

def run_test():
    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_form.html"))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(f"file:///{html_path}")
        time.sleep(1)
        
        print("\n--- Test 1: Click a specific skill based on resume ---")
        solve_with_hybrid_vision(page, "Read question 1. The user has the following skills: Java. Find the matching option and click the radio button next to it. If none match, return skip.")
        time.sleep(2)
        
        print("\n--- Test 2: Type experience based on resume ---")
        solve_with_hybrid_vision(page, "Read question 2. The user has 0 years of experience. Find the input field for this question and type '0' into it.")
        time.sleep(2)
        
        print("\n--- Test 3: Unmatched skill test ---")
        solve_with_hybrid_vision(page, "Read question 1 again. The user ONLY knows C#. Find the matching option and click it. If none match, return skip.")
        time.sleep(2)
        
        browser.close()

if __name__ == "__main__":
    run_test()
