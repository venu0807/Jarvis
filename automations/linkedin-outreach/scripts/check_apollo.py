"""scripts/check_apollo.py — diagnose what Apollo endpoints your key can hit.

Quick health check + diagnostic:
- /v1/auth/health
- /v1/organizations/enrich (free, should always work)
- /v1/people/match (paid only — most useful for our bot)

Usage:
  python scripts/check_apollo.py
"""
import os, requests, sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))

# Load .env
from dotenv import load_dotenv
load_dotenv(PROJ / ".env")

api_key = os.getenv("APOLLO_API_KEY")
if not api_key:
    print("❌ APOLLO_API_KEY not in .env")
    sys.exit(1)

headers = {"Content-Type": "application/json", "X-Api-Key": api_key}


def test(name, url, payload, ok_codes=(200, 404, 422)):
    print(f"=== {name} ===")
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        ok = r.status_code in ok_codes
        mark = "✅" if ok else "❌"
        print(f"  {mark} {r.status_code}: {r.text[:200]}")
        return r
    except Exception as e:
        print(f"  ❌ request failed: {e}")
        return None


print(f"Apollo key: {api_key[:8]}...{api_key[-4:]}\n")

# 1. Free — should work
test(
    "1. Organization enrich (free)",
    "https://api.apollo.io/v1/organizations/enrich",
    {"domain": "google.com"},
)

# 2. People match — probe
print()
test(
    "2. People match (paid only)",
    "https://api.apollo.io/v1/people/match",
    {"first_name": "Sarah", "last_name": "Chen", "organization_name": "Google"},
)

print()
print("=" * 60)
print("Diagnosis:")
print("- If #1 succeeded and #2 returned 403:")
print("  → Your Apollo account is on FREE plan, can't do people-search.")
print("  → Workaround: rely on email-in-text extraction (already works).")
print("  → See skill: apollo-free-plan-403")
print()
print("- If #2 returned 200 with a person block:")
print("  → Apollo works! bots should be sending emails.")
print()
print("- If #2 returned 404 'no match':")
print("  → Apollo works, just this person isn't in their DB.")
