import requests
import re
url = "https://trends.pinterest.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
try:
    r = requests.get(url, headers=headers)
    print("Got HTML length:", len(r.text))
    matches = re.findall(r'"term":"([^"]+)"', r.text)
    if not matches:
        matches = re.findall(r'"keyword":"([^"]+)"', r.text)
    print("Keywords found:", set(matches))
except Exception as e:
    print(e)
