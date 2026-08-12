import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
import asyncio

load_dotenv(Path(__file__).parent / "pinterest" / ".env")

def get_nvidia_key():
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        raise Exception("NVIDIA_API_KEY not found")
    return key

js_extractor = r"""
() => {
    let elements = [];
    document.querySelectorAll('input, textarea, select, label, button, [role="radio"], [role="checkbox"]').forEach(el => {
        let rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        
        let text = el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || "";
        text = text.trim().substring(0, 100).replace(/\n/g, ' ');
        
        let info = `<${el.tagName.toLowerCase()}`;
        if (el.id) info += ` id="${el.id}"`;
        if (el.type) info += ` type="${el.type}"`;
        if (el.name) info += ` name="${el.name}"`;
        info += `>${text}</${el.tagName.toLowerCase()}>`;
        
        if (!elements.includes(info) && text.length > 0) {
            elements.push(info);
        }
    });
    return elements.join('\n');
}
"""

def _build_text_payload(dom_text, instruction):
    system_prompt = (
        "You are an expert robotic automation agent. You are looking at a simplified HTML representation of a web form.\n"
        "Your goal is to answer the user's instruction based on the provided HTML elements.\n"
        "You must output ONLY valid JSON matching one of these actions:\n"
        "1. To click a specific element: {\"action\": \"click\", \"target_text\": \"exact inner text or placeholder of the element to click\"}\n"
        "2. To type into an input: {\"action\": \"type\", \"target_text\": \"exact placeholder or label text of the input\", \"value\": \"exact text to type without summarizing\"}\n"
        "3. If none of the options are safe or relevant: {\"action\": \"skip\"}\n"
        "Do not output markdown block ticks, just raw JSON. DO NOT summarize or truncate the text to type."
    )
    return {
        "model": "meta/llama-3.1-8b-instruct", # text-only DOM Q — 8b fast, 90b-vision hung
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"Instruction: {instruction}\n\nForm HTML:\n{dom_text}"
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.1
    }

def _parse_response(content):
    start_idx = content.find('{')
    end_idx = content.rfind('}')
    if start_idx != -1 and end_idx != -1:
        json_str = content[start_idx:end_idx+1]
    else:
        json_str = content
    return json.loads(json_str)

async def solve_with_dom_async(page, instruction: str):
    print(f"\n[DOM LLM] Analyzing form for instruction: '{instruction}'")
    
    # Extract simplified DOM
    dom_text = await page.evaluate(js_extractor)
    
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {get_nvidia_key()}", "Content-Type": "application/json"}
    payload = _build_text_payload(dom_text, instruction)
    
    # Run sync request in a background thread to not block async loop
    # timeout: NVIDIA 90b-vision hung indefinitely with no timeout — cap it
    # so a slow/rate-limited completion skips the question instead of stalling
    # the whole pipeline.
    try:
        response = await asyncio.to_thread(
            requests.post, url, headers=headers, json=payload, timeout=30
        )
        data = response.json()
    except Exception as e:
        print(f"  -> DOM LLM call failed ({e}); skipping question")
        return
    if 'choices' not in data:
        print(f"  -> DOM LLM no choices ({data}); skipping question")
        return

    content = data['choices'][0]['message']['content'].strip()
    action_data = _parse_response(content)
    action = action_data.get('action')
    
    if action == 'click':
        target = action_data['target_text']
        print(f"  -> DOM System clicking: '{target}'")
        el = page.get_by_text(target).first
        if await el.count() == 0:
             el = page.get_by_placeholder(target).first
        await el.evaluate("node => node.click()")
        print("  -> Click complete!")
        
    elif action == 'type':
        target = action_data['target_text']
        val = action_data['value']
        print(f"  -> DOM System typing '{val}' into '{target}'")
        el = page.get_by_placeholder(target).first
        if await el.count() == 0:
            el = page.get_by_text(target).first
        # Use native Playwright fill
        await el.fill(val)
        print("  -> Type complete!")
        
    elif action == 'skip':
        print("  -> DOM System skipped action (no match/irrelevant).")
    else:
        print(f"  -> Unknown action: {action_data}")

# Sync version for testing
def solve_with_dom_sync(page, instruction: str):
    print(f"\n[DOM LLM] Analyzing form for instruction: '{instruction}'")
    dom_text = page.evaluate(js_extractor)
    
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {get_nvidia_key()}", "Content-Type": "application/json"}
    payload = _build_text_payload(dom_text, instruction)
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
    except Exception as e:
        print(f"  -> DOM LLM call failed ({e}); skipping question")
        return
    if 'choices' not in data:
        print(f"  -> DOM LLM no choices ({data}); skipping question")
        return

    content = data['choices'][0]['message']['content'].strip()
    action_data = _parse_response(content)
    action = action_data.get('action')
    
    if action == 'click':
        target = action_data['target_text']
        print(f"  -> DOM System clicking: '{target}'")
        el = page.get_by_text(target).first
        if el.count() == 0:
             el = page.get_by_placeholder(target).first
        el.evaluate("node => node.click()")
        print("  -> Click complete!")
        
    elif action == 'type':
        target = action_data['target_text']
        val = action_data['value']
        print(f"  -> DOM System typing '{val}' into '{target}'")
        el = page.get_by_placeholder(target).first
        if el.count() == 0:
            el = page.get_by_text(target).first
        el.fill(val)
        print("  -> Type complete!")
        
    elif action == 'skip':
        print("  -> DOM System skipped action.")
