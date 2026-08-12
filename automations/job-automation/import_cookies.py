"""import_cookies.py — turn exported cookies into a Playwright session file.

The auto-applier persists per-portal auth in .sessions/<portal>.json as
Playwright storage_state (cookies + localStorage). When a session expires,
login back in your own browser, export the cookies, and import them here:

    python import_cookies.py <portal> <cookiefile>

Supported formats (autodetected):
  * Netscape cookies.txt  — from "Get cookies.txt LOCALLY" / curl extensions
  * EditThisCookie JSON   — the array of {name,value,domain,...} objects

<portal> must match the session filename: naukri|internshala|indeed|
foundit|cutshort|freshersworld|wellfound
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
SESSION_DIR = BASE_DIR / ".sessions"

VALID = {"naukri", "internshala", "indeed", "foundit"}


def _parse_netscape(text: str) -> list:
    """Parse Netscape cookies.txt lines into Playwright cookie dicts.

    Accepts both tab- and whitespace-delimited lines — copy/paste from a
    browser extension can normalize tabs to spaces. `split()` handles both;
    cookie values in these exports never contain spaces.
    """
    cookies = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 7:
            continue
        domain, include_sub, path, secure, expires, name, value = (
            parts[0], parts[1] == "TRUE", parts[2], parts[3] == "TRUE",
            int(parts[4]), parts[5], parts[6],
        )
        # Playwright needs a valid domain (leading dot stripped) and sameSite/enabled
        cookies.append({
            "name": name,
            "value": value,
            "domain": domain.lstrip("."),
            "path": path,
            "expires": expires if expires > 0 else -1,
            "httpOnly": include_sub,  # reuse; best-effort
            "secure": secure,
            "sameSite": "Lax",
        })
    return cookies


def _parse_json(blob: str) -> list:
    """EditThisCookie export: [{name,value,domain,path,expirationDate,sameSite,secure,...}]"""
    data = json.loads(blob)
    out = []
    for c in data:
        out.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", "").lstrip("."),
            "path": c.get("path", "/"),
            "expires": c.get("expirationDate", -1),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "sameSite": c.get("sameSite", "Lax"),
        })
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    portal, cookie_file = sys.argv[1], sys.argv[2]
    if portal not in VALID:
        print(f"Unknown portal '{portal}'. Valid: {', '.join(sorted(VALID))}")
        return 1
    src = Path(cookie_file)
    if not src.exists():
        print(f"Cookie file not found: {src}")
        return 1

    text = src.read_text(encoding="utf-8", errors="ignore")
    if text.lstrip().startswith("["):
        cookies = _parse_json(text)
    else:
        cookies = _parse_netscape(text)

    if not cookies:
        print("No cookies parsed — check the file format.")
        return 1

    # storage_state requires at least one origin; cookies go under cookie key.
    state = {"cookies": cookies, "origins": []}
    dest = SESSION_DIR / f"{portal}.json"
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"✅ Imported {len(cookies)} cookies → {dest}")
    print(f"   Next pipeline run will reuse them for '{portal}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
