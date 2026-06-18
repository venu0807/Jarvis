import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("PINTEREST_ACCESS_TOKEN")

# Check if token is empty or still the placeholder
if not token or "your_pinterest_access_token" in token:
    print("=" * 55)
    print("  TOKEN NOT SET UP YET!")
    print("=" * 55)
    print()
    print("  Your .env file still has the placeholder text.")
    print("  You need a real Pinterest API token to use this bot.")
    print()
    print("  Follow these steps:")
    print("  1. Go to https://developers.pinterest.com/")
    print("  2. Log in with your Pinterest account")
    print("  3. Click 'Create App' → name it 'My Auto Poster'")
    print("  4. Under 'Authentication', click 'Generate token'")
    print("  5. Select these scopes: boards:read, pins:read, pins:write")
    print("  6. Copy the token")
    print("  7. Paste it into your .env file:")
    print(f"     PINTEREST_ACCESS_TOKEN=paste_your_token_here")
    print()
    print("  Then run this script again!")
    print()
    exit()

url = "https://api.pinterest.com/v5/boards"
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

print("Fetching your boards...")
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    boards = data.get("items", [])
    if not boards:
        print("You don't have any boards yet! Please create one on Pinterest.")
    else:
        print("\n--- YOUR PINTEREST BOARDS ---")
        for b in boards:
            print(f"Board Name: {b['name']}  |  Board ID: {b['id']}")
        print("-----------------------------\n")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
