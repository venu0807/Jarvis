"""Discover actual Workday URLs by visiting each company's careers landing
page and following redirects/scripts to find the real myworkdayjobs.com host
+ path.
"""
import requests, re

# Real public career URLs (NOT guesses — these are what cisco/ibm/walmart
# actually redirect to)
companies = [
    ("cisco",    "https://jobs.cisco.com",                       "post jobs"),
    ("ibm",      "https://www.ibm.com/careers",                  "open roles"),
    ("walmart",  "https://careers.walmart.com",                  "open roles"),
    ("oracle",   "https://www.oracle.com/careers",               "OracleExternalCareerSite"),
    ("intel",    "https://jobs.intel.com",                       "Intel"),
    ("accenture","https://www.accenture.com/us-en/careers",      "Accenture"),
    ("target",   "https://corporate.target.com/careers",         "TargetCareers"),
]

print("DISCOVERING WORKDAY HOST + SITE FROM CAREERS PAGE REDIRECT/JS")
print("=" * 70)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0"}

for name, careers_url, hint in companies:
    try:
        r = requests.get(careers_url, timeout=15, allow_redirects=True, headers=headers)
        final = r.url
        text = r.text

        # Scan for any myworkdayjobs.com host + the adjacent site path
        hosts = set(re.findall(r'([a-z0-9_-]+)\.myworkdayjobs\.com', text, re.I))
        hosts.update(re.findall(r'([a-z0-9_-]+)\.myworkdayjobs\.com', final, re.I))

        # Look for /[site-name]/ pattern near Workday refs
        site_patterns = re.findall(r'/en-US/([A-Za-z0-9_-]+)', text)

        print(f"\n[{name}]")
        print(f"  Final URL: {final}")
        print(f"  Hosts:     {sorted(hosts) if hosts else '(none in HTML)'}")
        print(f"  Sites:     {set(site_patterns) if site_patterns else '(none)'}")
    except Exception as e:
        print(f"  {name}: {type(e).__name__}: {e}")
