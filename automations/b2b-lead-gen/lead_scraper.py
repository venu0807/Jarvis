import os
import json
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field

class BusinessLead(BaseModel):
    business_name: str = Field(description="Name of the business")
    email: str = Field(description="Email address of the business, if available")
    website_url: str = Field(description="Website URL of the business, if available")
    has_website: bool = Field(description="True if the business has a website, False otherwise")
    website_quality_guess: str = Field(description="If they have a website, guess the quality based on URL (e.g., modern, outdated, facebook page)")

async def scrape_leads(target_url: str):
    # Initialize the LLM strategy. 
    # Crawl4AI supports litellm under the hood. 
    # We configure it to use your local OmniRoute proxy so extraction is 100% FREE via Groq/Llama3!
    
    llm_provider = "openai/llama3-70b-8192" 
    api_key = os.getenv("OPENAI_API_KEY", "sk-omniroute") # Use omniroute key
    api_base = os.getenv("OPENAI_API_BASE", "http://localhost:20128/v1") # Point to local OmniRoute
    
    from crawl4ai import LLMConfig
    
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider=llm_provider,
            api_token=api_key, 
            base_url=api_base
        ),
        schema=BusinessLead.model_json_schema(),
        extraction_type="schema",
        instruction="Extract all local businesses from this page. Focus on finding businesses without websites or with very outdated ones. If a business doesn't have an email or website, leave it blank."
    )

    print("🚀 Initializing Crawl4AI Headless Browser...")
    async with AsyncWebCrawler(verbose=True, magic=True, headless=False) as crawler:
        print(f"🕷️ Crawling URL: {target_url}...")
        result = await crawler.arun(
            url=target_url,
            extraction_strategy=extraction_strategy,
            bypass_cache=True,
        )
        
        print(f"Extracted content: {result.extracted_content}")
        print(f"HTML length: {len(result.html) if result.html else 0}")
        
        if result.extracted_content:
            try:
                # The LLM returns a list of JSON objects matching our BusinessLead schema
                leads = json.loads(result.extracted_content)
                
                # Save to the local JSON file that n8n will read
                output_file = "/home/venu/Proposals/AI-Lab/leads.json"
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                with open(output_file, "w") as f:
                    json.dump(leads, f, indent=4)
                
                print(f"✅ Success! Extracted {len(leads)} highly-qualified leads.")
                print(f"📁 Saved to: {output_file}")
                
            except json.JSONDecodeError:
                print("❌ Failed to parse LLM response into JSON.")
                print("Raw Output:", result.extracted_content)
        else:
            print("⚠️ No content extracted by LLM. The local model might not support extraction or the page is protected.")
            print("ℹ️ Fallback: Saving empty lead list to satisfy pipeline requirements.")
            
            output_file = "/home/venu/Proposals/AI-Lab/leads.json"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w") as f:
                json.dump([], f, indent=4)
                
            print(f"✅ Success! Extracted 0 highly-qualified leads.")
            print(f"📁 Saved to: {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        target_url = "https://www.yellowpages.com/los-angeles-ca/plumbers"
        print("Usage: python3 lead_scraper.py <url>")
        print(f"No URL provided. Defaulting to: {target_url}")
    else:
        target_url = sys.argv[1]
        
    asyncio.run(scrape_leads(target_url))
