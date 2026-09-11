import xml.etree.ElementTree as ET
import timeit
import urllib.request
import itertools

# Fetch sample RSS
url = "https://news.google.com/rss/search?q=google+business+OR+tech"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    xml_data = response.read()

root = ET.fromstring(xml_data)

def original_method():
    news_items = []
    for item in root.findall(".//item")[:4]:
        title = item.find("title").text
        pubDate = item.find("pubDate").text
        if " - " in title:
            title = title.rsplit(" - ", 1)[0]
        news_items.append(f"  - {title} ({pubDate})")
    return news_items

def optimized_method():
    news_items = []
    for item in itertools.islice(root.iter("item"), 4):
        title = item.findtext("title")
        pubDate = item.findtext("pubDate")
        if title and " - " in title:
            title = title.rsplit(" - ", 1)[0]
        news_items.append(f"  - {title} ({pubDate})")
    return news_items

print("Results Match:", original_method() == optimized_method())

t1 = timeit.timeit(original_method, number=10000)
t2 = timeit.timeit(optimized_method, number=10000)

print(f"Original: {t1:.4f}s")
print(f"Optimized: {t2:.4f}s")
