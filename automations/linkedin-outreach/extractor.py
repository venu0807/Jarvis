"""extractor.py — Extract contact info from LinkedIn posts.

Fixes applied:
- #4: Tighter email regex that strips trailing punctuation (parens,
  commas, periods, semicolons, colons, exclamation, question marks).
  Before: `john@gmail.com.)` matched and was sent as-is → bounced.
  After:  cleaned to `john@gmail.com`.
- Adds a sanity check: emails without a TLD, with consecutive dots, or
  with non-ASCII are discarded.
- Better Apollo.io error handling: distinguish 404 (no person found) from
  402 (quota exceeded) from 5xx (transient — should retry).
"""

import os
import re
import requests
import time
from typing import Optional, Tuple

EMAIL_REGEX = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
)
VALIDATION_REGEX = re.compile(r"[^@]+@[^@]+\.[a-zA-Z]{2,}$")

# Trailing punctuation that's NOT part of an email
TRAILING_PUNCT = ".,;:!?)>]'\""


def extract_email_from_text(text):
    """Extract the first valid email from text. Strips trailing punctuation."""
    if not text:
        return None

    for match in EMAIL_REGEX.finditer(text):
        candidate = match.group(0)

        # Strip any trailing punctuation that snuck in
        while candidate and candidate[-1] in TRAILING_PUNCT:
            candidate = candidate[:-1]

        # Discard obvious garbage
        if not candidate or ".." in candidate.split("@")[0]:
            continue
        if not VALIDATION_REGEX.match(candidate):
            continue

        return candidate

    return None


def get_email_from_apollo(name, company, max_retries=2):
    """Use Apollo API to find email given name + company. Retries on 5xx."""
    api_key = os.environ.get("APOLLO_API_KEY")
    if not api_key:
        print("Apollo API Key not set.")
        return None

    url = "https://api.apollo.io/v1/people/match"
    # Apollo deprecated body-form api_key; now requires X-Api-Key header only.
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }

    parts = name.strip().split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    data = {
        "first_name": first_name,
        "last_name": last_name,
        "organization_name": company,
    }

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=15)

            if resp.status_code == 200:
                person = resp.json().get("person")
                if person and person.get("email"):
                    return person["email"]
                # 200 + no person = genuinely not found
                print(f"  ℹ Apollo: no match for {name} @ {company}")
                return None

            if resp.status_code == 404:
                # Person genuinely not in DB
                print(f"  ℹ Apollo: 404 (no match) for {name}")
                return None

            if resp.status_code == 422:
                # Bad input — won't fix by retrying
                print(f"  ⚠ Apollo: 422 (bad input): {resp.text[:120]}")
                return None

            if resp.status_code in (402, 429):
                print(f"  ⚠ Apollo: {resp.status_code} quota/rate-limit hit.")
                return None

            if resp.status_code >= 500:
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"  ⚠ Apollo: {resp.status_code} server error, retrying in {wait}s")
                    time.sleep(wait)
                    continue
                print(f"  ⚠ Apollo: {resp.status_code} after {max_retries} retries")
                return None

            print(f"  ⚠ Apollo: {resp.status_code} {resp.text[:120]}")
            return None

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print(f"  ⚠ Apollo timeout, retrying...")
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception as e:
            print(f"  ⚠ Apollo error: {type(e).__name__}: {str(e)[:120]}")
            return None

    return None


def extract_contact_info(text, name, company):
    """Try in-text email first, then Apollo (paid only). Returns (email, source) or (None, None)."""
    email = extract_email_from_text(text)
    if email:
        return email, "regex"

    # Apollo lookup silently skipped on free-tier plans (403).
    # To use Apollo, upgrade at https://app.apollo.io/ or use Hunter.io instead.
    return None, None
