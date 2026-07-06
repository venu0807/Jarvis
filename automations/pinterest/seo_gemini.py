import os
import re
from google import genai
from google.genai import types

def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def generate_seo_title(name: str, category: str, is_trending: bool = False, price: str = None) -> str:
    """Generates an SEO optimized Pinterest title using Gemini."""
    client = get_client()
    if not client:
        return name[:80]
        
    prompt = f"""
    Write a highly engaging, viral, and SEO-optimized Pinterest title for this Amazon product.
    Product Name: {name}
    Category: {category}
    Trending: {is_trending}
    Price: {price}
    
    Rules:
    1. Must be under 80 characters.
    2. Do NOT use hashtags in the title.
    3. Make it catchy (e.g., "Must-Have", "Genius", "Viral").
    4. Only output the title text, nothing else.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        title = response.text.strip().replace('"', '').replace("'", "")
        return title[:100]
    except Exception as e:
        print(f"  ⚠️  Gemini API error (title): {e}")
        return name[:80]

def generate_seo_description(name: str, category: str, price: str, is_trending: bool = False) -> str:
    """Generates an SEO optimized Pinterest description using Gemini."""
    client = get_client()
    if not client:
        return f"Check out this amazing {category} find! {name} is only {price}."
        
    prompt = f"""
    Write a highly engaging, viral, and SEO-optimized Pinterest description for this Amazon product.
    Product Name: {name}
    Category: {category}
    Trending: {is_trending}
    Price: {price}
    
    Rules:
    1. Make it sound organic, like a recommendation from a friend.
    2. Include 3-4 relevant SEO keywords naturally.
    3. End with a strong call-to-action to click the link in bio or shop now.
    4. Include 3-5 relevant hashtags at the end.
    5. Only output the description text, nothing else.
    6. Length should be around 2-3 short sentences.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"  ⚠️  Gemini API error (desc): {e}")
        return f"Check out this amazing {category} find! {name} is only {price}."
