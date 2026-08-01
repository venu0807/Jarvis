#!/usr/bin/env python3
"""
Classify career URLs by ATS type and update companies.json
"""

import json
import re
from urllib.parse import urlparse

# ATS detection patterns
ATS_PATTERNS = {
    "greenhouse": [
        r"boards\.greenhouse\.io/([^/?#]+)",
        r"greenhouse\.io/([^/?#]+)",
    ],
    "lever": [
        r"jobs\.lever\.co/([^/?#]+)",
        r"lever\.co/([^/?#]+)",
    ],
    "ashby": [
        r"jobs\.ashbyhq\.com/([^/?#]+)",
        r"ashbyhq\.com/([^/?#]+)",
    ],
    "recruitee": [
        r"([^.]+)\.recruitee\.co",
        r"recruitee\.com/([^/?#]+)",
    ],
    "workday": [
        r"([^.]+)\.wd\d+\.myworkdayjobs\.com",
        r"myworkdayjobs\.com/([^/?#]+)",
        r"workdayjobs\.com/([^/?#]+)",
    ],
    "workable": [
        r"apply\.workable\.com/([^/?#]+)",
        r"([^.]+)\.workable\.com",
    ],
    "breezy": [
        r"([^.]+)\.breezy\.hr",
        r"breezy\.hr/([^/?#]+)",
    ],
    "smartrecruiters": [
        r"careers\.smartrecruiters\.com/([^/?#]+)",
        r"smartrecruiters\.com/([^/?#]+)",
    ],
    "personio": [
        r"jobs\.personio\.de/([^/?#]+)",
        r"personio\.de/([^/?#]+)",
    ],
    "rippling": [
        r"([^.]+)\.rippling-ats\.com",
        r"rippling-ats\.com/([^/?#]+)",
    ],
    "eightfold": [
        r"([^.]+)\.eightfold\.ai",
        r"eightfold\.ai/([^/?#]+)",
    ],
    "teamTailor": [
        r"([^.]+)\.teamtailor\.com",
        r"teamtailor\.com/([^/?#]+)",
    ],
    "cometogether": [
        r"([^.]+)\.cometogether\.co",
        r"cometogether\.co/([^/?#]+)",
    ],
    "jobvite": [
        r"jobs\.jobvite\.com/([^/?#]+)",
        r"jobvite\.com/([^/?#]+)",
    ],
    "icims": [
        r"careers\.icims\.com/([^/?#]+)",
        r"icims\.com/([^/?#]+)",
    ],
    "bamboohr": [
        r"([^.]+)\.bamboohr\.com",
        r"bamboohr\.com/([^/?#]+)",
    ],
    "hirehive": [
        r"([^.]+)\.hirehive\.io",
        r"hirehive\.io/([^/?#]+)",
    ],
    "gupy": [
        r"([^.]+)\.gupy\.io",
        r"gupy\.io/([^/?#]+)",
    ],
    "welcometothejungle": [
        r"welcometothejungle\.co/([^/?#]+)",
    ],
    "zohorecruit": [
        r"([^.]+)\.zohorecruit\.com",
        r"zohorecruit\.com/([^/?#]+)",
    ],
    "join": [
        r"([^.]+)\.join\.com",
        r"join\.com/([^/?#]+)",
    ],
    "angel": [
        r"angel\.co/company/([^/?#]+)",
        r"wellfound\.com/company/([^/?#]+)/jobs",
    ],
    "github": [
        r"github\.com/([^/]+)/jobs",
    ],
    "custom": []  # fallback
}


def detect_ats(url: str):
    """Detect ATS type from career URL and extract token/company identifier."""
    url_lower = url.lower()

    for ats_type, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, url_lower)
            if match:
                token = match.group(1) if match.lastindex else None
                return ats_type, token

    # Special handling for known patterns
    if "greenhouse" in url_lower:
        return "greenhouse", None
    if "lever.co" in url_lower or "jobs.lever" in url_lower:
        return "lever", None
    if "ashby" in url_lower:
        return "ashby", None
    if "recruitee" in url_lower:
        return "recruitee", None
    if "workday" in url_lower or "myworkdayjobs" in url_lower:
        return "workday", None
    if "workable" in url_lower:
        return "workable", None
    if "breezy" in url_lower:
        return "breezy", None
    if "smartrecruiters" in url_lower:
        return "smartrecruiters", None
    if "personio" in url_lower:
        return "personio", None
    if "rippling" in url_lower:
        return "rippling", None
    if "eightfold" in url_lower:
        return "eightfold", None
    if "teamtailor" in url_lower:
        return "teamTailor", None
    if "jobvite" in url_lower:
        return "jobvite", None
    if "icims" in url_lower:
        return "icims", None
    if "bamboohr" in url_lower:
        return "bamboohr", None
    if "hirehive" in url_lower:
        return "hirehive", None
    if "gupy" in url_lower:
        return "gupy", None
    if "welcometothejungle" in url_lower:
        return "welcometothejungle", None
    if "zohorecruit" in url_lower:
        return "zohorecruit", None
    if "join.com" in url_lower:
        return "join", None
    if "angel.co" in url_lower or "wellfound.com" in url_lower:
        return "angel", None

    return "custom", None


def make_key(name: str) -> str:
    """Convert company name to a valid key for companies.json."""
    key = name.lower()
    key = re.sub(r'[^a-z0-9]+', '-', key)
    key = key.strip('-')
    return key


def load_scraped_companies():
    """Load the scraped companies from the Playwright output file."""
    with open('/home/venu/.claude/projects/-home-venu-Proposals/5b628c3c-581d-4579-a52c-c5a816119eb0/tool-results/mcp-plugin_playwright_playwright-browser_evaluate-1784386432333.txt', 'r') as f:
        content = f.read()

    # Find the first [ and decode the first JSON value
    start = content.find('[')
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(content, start)
    return obj


def main():
    # Load existing companies.json
    with open('/home/venu/Proposals/Jarvis/automations/job-automation/companies.json', 'r') as f:
        existing = json.load(f)

    # Load scraped companies
    scraped = load_scraped_companies()
    print(f"Loaded {len(scraped)} scraped companies")
    print(f"Existing companies: {len(existing)}")

    # Track new entries
    new_entries = {}
    skipped = 0
    updated = 0

    for company in scraped:
        name = company['name'].strip()
        url = company['url'].strip()
        region = company['region'].strip()

        # Clean up URL
        if not url.startswith('http'):
            url = 'https://' + url

        # Create key
        key = make_key(name)

        # Skip if already exists (with same key)
        if key in existing:
            skipped += 1
            continue

        # Check for duplicate names (different casing)
        existing_keys = {k.lower(): k for k in existing.keys()}
        if key.lower() in existing_keys:
            skipped += 1
            continue

        # Detect ATS
        ats_type, token = detect_ats(url)

        # Build entry
        entry = {
            "name": name,
            "type": ats_type,
        }

        if ats_type == "greenhouse" and token:
            entry["token"] = token
        elif ats_type == "lever" and token:
            entry["token"] = token
        elif ats_type == "ashby" and token:
            entry["url"] = f"https://jobs.ashbyhq.com/{token}"
        elif ats_type == "recruitee" and token:
            entry["url"] = f"https://{token}.recruitee.co"
        elif ats_type == "workday":
            # Try to extract tenant info from URL
            entry["url"] = url
        elif ats_type in ["workable", "breezy", "smartrecruiters", "personio", "rippling", "eightfold", "teamTailor", "jobvite", "icims", "bamboohr", "hirehive", "gupy", "welcometothejungle", "zohorecruit", "join", "angel"]:
            entry["url"] = url
        else:
            entry["type"] = "custom"
            entry["url"] = url

        # Add note for manual review if custom or complex
        if ats_type == "custom" or ats_type in ["workday", "workable"]:
            entry["_note"] = f"Region: {region}, Source: remoteintech.company"

        new_entries[key] = entry
        updated += 1

    print(f"New entries to add: {updated}")
    print(f"Skipped (already exist): {skipped}")

    # Show distribution of ATS types
    ats_counts = {}
    for entry in new_entries.values():
        ats_counts[entry['type']] = ats_counts.get(entry['type'], 0) + 1
    print("\nATS Type Distribution:")
    for ats, count in sorted(ats_counts.items(), key=lambda x: -x[1]):
        print(f"  {ats}: {count}")

    # Merge and save
    merged = {**existing, **new_entries}

    with open('/home/venu/Proposals/Jarvis/automations/job-automation/companies.json', 'w') as f:
        json.dump(merged, f, indent=2)

    print(f"\nTotal companies after merge: {len(merged)}")
    print("Saved to companies.json")


if __name__ == "__main__":
    main()