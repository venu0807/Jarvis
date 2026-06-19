import os
import base64
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
import asyncio
import aiohttp

# Load nearest .env file
load_dotenv(Path(__file__).parent / "pinterest" / ".env")

class VisionFallbackError(Exception):
    pass

def get_nvidia_key():
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        raise VisionFallbackError("NVIDIA_API_KEY not found in environment variables.")
    return key

def _build_payload(base64_image, width, height, instruction):
    system_prompt = (
        "You are an expert robotic automation agent. You are looking at a screenshot of a web browser.\n"
        f"The viewport size is {width}x{height} pixels.\n"
        "Your goal is to answer the user's instruction based on what you see on the screen.\n"
        "You must output ONLY valid JSON.\n"
        "Schema options:\n"
        "1. If you need to click a specific location or large button: {\"action\": \"click\", \"x\": int, \"y\": int}\n"
        "2. If you need to click a text label, radio button, or checkbox option: {\"action\": \"click_text\", \"text\": \"exact text of option\"}\n"
        "3. If you need to type text into an input field: {\"action\": \"type\", \"x\": int, \"y\": int, \"text\": \"value to type\"}\n"
        "4. If you should skip or do nothing: {\"action\": \"skip\"}\n"
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

def _parse_response(content):
    # Extract JSON string
    start_idx = content.find('{')
    end_idx = content.rfind('}')
    if start_idx != -1 and end_idx != -1:
        json_str = content[start_idx:end_idx+1]
    else:
        json_str = content
        
    try:
        action_data = json.loads(json_str)
    except json.JSONDecodeError:
        raise VisionFallbackError(f"Failed to parse model response as JSON: {json_str}")
    
    return action_data

def solve_with_vision(page, instruction: str):
    """Sync version for Pinterest"""
    print(f"\n[Vision Fallback] Falling back to VLM for instruction: '{instruction}'")
    screenshot_bytes = page.screenshot(animations="disabled", caret="hide")
    base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
    viewport = page.viewport_size
    width = viewport['width'] if viewport else 1366
    height = viewport['height'] if viewport else 768
    
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {get_nvidia_key()}", "Content-Type": "application/json", "Accept": "application/json"}
    payload = _build_payload(base64_image, width, height, instruction)
    
    print("  -> Sending screenshot to Nvidia NIM API (Llama 3.2 90B Vision)...")
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise VisionFallbackError(f"API Error {response.status_code}: {response.text}")
        
    content = response.json()['choices'][0]['message']['content'].strip()
    action_data = _parse_response(content)
    action = action_data.get('action')
    
    if action == 'click':
        print(f"  -> Vision System clicking at ({action_data['x']}, {action_data['y']})")
        page.mouse.click(action_data['x'], action_data['y'])
        print("  -> Click complete!")
    elif action == 'click_text':
        print(f"  -> Vision System finding text: '{action_data['text']}'")
        el = page.get_by_text(action_data['text']).first
        if el:
            box = el.bounding_box()
            if box:
                # Physical mouse click directly on the coordinates to avoid bot detection and scroll jerking
                target_x = box['x'] + (box['width'] / 2)
                target_y = box['y'] + (box['height'] / 2)
                page.mouse.click(target_x, target_y)
                print(f"  -> Physical click executed at ({target_x}, {target_y}) for '{action_data['text']}'")
            else:
                print(f"  -> Element '{action_data['text']}' not visible for bounding box click.")
        else:
            print(f"  -> Element '{action_data['text']}' not found.")
    elif action == 'type':
        print(f"  -> Vision System typing '{action_data['text']}' at ({action_data['x']}, {action_data['y']})")
        page.mouse.click(action_data['x'], action_data['y'])
        page.keyboard.type(action_data['text'])
        print("  -> Type complete!")
    elif action == 'skip':
        print("  -> Vision System skipped action (no match/irrelevant).")
    else:
        raise VisionFallbackError(f"Unsupported action received: {action_data}")

async def solve_with_vision_async(page, instruction: str):
    """Async version for Job Automation"""
    print(f"\n[Vision Fallback] Falling back to VLM for instruction: '{instruction}'")
    screenshot_bytes = await page.screenshot(animations="disabled", caret="hide")
    base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
    viewport = page.viewport_size
    width = viewport['width'] if viewport else 1366
    height = viewport['height'] if viewport else 768
    
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {get_nvidia_key()}", "Content-Type": "application/json", "Accept": "application/json"}
    payload = _build_payload(base64_image, width, height, instruction)
    
    print("  -> Sending screenshot to Nvidia NIM API (Llama 3.2 90B Vision)...")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise VisionFallbackError(f"API Error {response.status}: {text}")
            data = await response.json()
            
    content = data['choices'][0]['message']['content'].strip()
    action_data = _parse_response(content)
    action = action_data.get('action')
    
    if action == 'click':
        print(f"  -> Vision System clicking at ({action_data['x']}, {action_data['y']})")
        await page.mouse.click(action_data['x'], action_data['y'])
        print("  -> Click complete!")
    elif action == 'click_text':
        print(f"  -> Vision System finding text: '{action_data['text']}'")
        el = await page.get_by_text(action_data['text']).first
        if el:
            box = await el.bounding_box()
            if box:
                target_x = box['x'] + (box['width'] / 2)
                target_y = box['y'] + (box['height'] / 2)
                await page.mouse.click(target_x, target_y)
                print(f"  -> Physical click executed at ({target_x}, {target_y}) for '{action_data['text']}'")
            else:
                print(f"  -> Element '{action_data['text']}' not visible for bounding box click.")
        else:
            print(f"  -> Element '{action_data['text']}' not found.")
    elif action == 'type':
        print(f"  -> Vision System typing '{action_data['text']}' at ({action_data['x']}, {action_data['y']})")
        await page.mouse.click(action_data['x'], action_data['y'])
        await page.keyboard.type(action_data['text'])
        print("  -> Type complete!")
    elif action == 'skip':
        print("  -> Vision System skipped action (no match/irrelevant).")
    else:
        raise VisionFallbackError(f"Unsupported action received: {action_data}")
