"""portal_performance.py — analyse auto-apply success rate per portal"""
import json, glob, os
from pathlib import Path
from collections import defaultdict

logs_dir = Path("output/logs")
apps_files = sorted(logs_dir.glob("applications_*.json"))

per_portal = defaultdict(lambda: {"applied": 0, "manual": 0, "skipped": 0, "error": 0})

for jf in apps_files:
    try:
        d = json.loads(jf.read_text(encoding="utf-8"))
    except Exception:
        continue
    # Applied: portal_counts (only applied counts)
    for portal, n in d.get("portal_counts", {}).items():
        per_portal[portal]["applied"] += n
    # Manual: extract portal from each manual entry
    for entry in d.get("manual", []):
        p = entry.get("portal", "Unknown") or "Unknown"
        per_portal[p]["manual"] += 1
    # Skipped: portal is embedded in the job object inside _skipped_jobs
    for entry in d.get("_skipped_jobs", []):
        p = entry.get("job", {}).get("portal", "Unknown") or "Unknown"
        per_portal[p]["skipped"] += 1

# Normalise portal keys (case mismatch)
normalised = defaultdict(lambda: {"applied": 0, "manual": 0, "skipped": 0, "error": 0})
key_map = {
    "foundit": "Foundit", "FOUNDIT": "Foundit",
    # Cut 2026-06-15 (kept in map so historical log rows still parse):
    # Glassdoor (0%), LinkedIn (3.9%), Unstop (11.1%) — see portals/__init__.py
    "Glassdoor": "Glassdoor (cut)", "glassdoor": "Glassdoor (cut)",
    "Indeed": "Indeed", "indeed": "Indeed",
    "LinkedIn": "LinkedIn (cut)", "linkedin": "LinkedIn (cut)",
    "Naukri": "Naukri", "naukri": "Naukri",
    "Internshala": "Internshala", "internshala": "Internshala",
    "Unstop": "Unstop (cut)", "unstop": "Unstop (cut)",
    "Cutshort": "Cutshort", "cutshort": "Cutshort",
    "Freshersworld": "Freshersworld", "freshersworld": "Freshersworld",
    "Wellfound": "Wellfound", "wellfound": "Wellfound",
    "CareerPage": "CareerPages", "career_pages": "CareerPages",
    "CareerPages": "CareerPages",
}
for raw, counts in per_portal.items():
    canon = key_map.get(raw, raw)
    for k, v in counts.items():
        normalised[canon][k] += v

# Also check applied_jobs.json for long-term applied counts by portal prefix
ad_path = logs_dir / "applied_jobs.json"
prefix_counts = defaultdict(int)
if ad_path.exists():
    ad = json.loads(ad_path.read_text(encoding="utf-8"))
    for jid in ad:
        # IDs are like "indeed_12345", "fi_67890", "internshala_xxx"
        prefix = jid.split("_", 1)[0].lower() if "_" in jid else "?"
        prefix_counts[prefix] += 1

# Print
print(f"{'Portal':<16} {'Applied':>8} {'Manual':>8} {'Skipped':>8} {'Total':>8} {'Apply%':>8}")
print("=" * 64)
sorted_portals = sorted(normalised.items(), key=lambda x: -x[1]["applied"])
for portal, c in sorted_portals:
    total = c["applied"] + c["manual"] + c["skipped"]
    pct = (c["applied"] / total * 100) if total > 0 else 0
    bar = "█" * int(pct / 5)
    print(f"{portal:<16} {c['applied']:>8} {c['manual']:>8} {c['skipped']:>8} {total:>8} {pct:>6.1f}% {bar}")

print()
print("=== Long-term applied_jobs.json prefix counts (lifetime) ===")
for prefix in sorted(prefix_counts, key=prefix_counts.get, reverse=True):
    print(f"  {prefix:<16} {prefix_counts[prefix]:>5} jobs")
print()
print(f"=== Sample top manual reasons (today's run) ===")
today = logs_dir / "applications_2026-06-12.json"
if today.exists():
    d = json.loads(today.read_text(encoding="utf-8"))
    by_p = defaultdict(lambda: defaultdict(int))
    for m in d.get("manual", []):
        p = m.get("portal", "?")
        r = (m.get("reason","") or "n/a")[:50]
        by_p[p][r] += 1
    for p in sorted(by_p.keys()):
        if not by_p[p]:
            continue
        print(f"\n  {p}:")
        for r, n in sorted(by_p[p].items(), key=lambda x:-x[1])[:4]:
            print(f"    {n}x  {r}")
