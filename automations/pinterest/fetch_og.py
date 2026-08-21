import urllib.request, re, sys

for url in sys.argv[1:]:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
        m = re.search(r'<meta property="og:image" name="og:image" content="([^"]+)"', html)
        if not m:
            m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if m:
            print(f"{url} -> {m.group(1)}")
        else:
            print(f"{url} -> No og:image found")
    except Exception as e:
        print(f"{url} -> Error: {e}")
