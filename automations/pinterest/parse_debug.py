from bs4 import BeautifulSoup

with open("debug_page.html", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("INPUTS:")
for i in soup.find_all("input"):
    print(i)

print("\n---\nBUTTONS (text only):")
for b in soup.find_all("button"):
    text = b.text.strip()
    if text:
        print(text)
