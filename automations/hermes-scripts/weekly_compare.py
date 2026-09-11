"""
weekly_compare.py — Compare portal performance before vs after fixes
Built: 2026-06-12. Designed to run on 2026-06-19 to evaluate 1 week of data after
the LinkedIn CTA fix and headful re-auth flow.

Usage:
    python scripts/weekly_compare.py            # full lifetime comparison
    python scripts/weekly_compare.py --since 2026-06-12   # only logs from that date
    python scripts/weekly_compare.py --disable  # interactive: offers to comment out portals with <10% rate
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

PROJ_DIR = Path(__file__).resolve().parent.parent
# Allow override via env var or CLI flag — needed when this cron copy lives in ~/.hermes/scripts/
PROJ_DIR = Path(os.environ.get("JOB_AUTOMATION_DIR", str(PROJ_DIR)))
LOGS_DIR = PROJ_DIR / "output" / "logs"
APPLIED_LOG = LOGS_DIR / "applied_jobs.json"

# LinkedIn CTA fix shipped on this date
FIX_DATE = "2026-06-12"


def normalise(portal: str) -> str:
    """Map any variant to canonical name."""
    p = (portal or "").strip()
    key_map = {
        "foundit": "Foundit", "fi": "Foundit",
        "glassdoor": "Glassdoor",
        "indeed": "Indeed",
        "linkedin": "LinkedIn",
        "naukri": "Naukri",
        "internshala": "Internshala",
        "unstop": "Unstop", "us": "Unstop",
        "cutshort": "Cutshort",
        "freshersworld": "Freshersworld",
        "wellfound": "Wellfound",
    }
    return key_map.get(p.lower(), p or "Unknown")


def load_counts(since: str = None):
    """Return {portal: {applied, manual, skipped, n_runs, first_seen, last_seen}}"""
    counts = defaultdict(lambda: {
        "applied": 0, "manual": 0, "skipped": 0,
        "n_runs": 0, "first_seen": None, "last_seen": None,
    })

    for jf in sorted(LOGS_DIR.glob("applications_*.json")):
        # Extract date from filename: applications_YYYY-MM-DD.json
        m = re.search(r"applications_(\d{4}-\d{2}-\d{2})", jf.name)
        if not m:
            continue
        date_str = m.group(1)
        if since and date_str < since:
            continue
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Track which portals ran that day
        portals_seen = set()

        # Applied counts by portal (portal_counts dict only counts 'applied')
        for portal, n in d.get("portal_counts", {}).items():
            canon = normalise(portal)
            counts[canon]["applied"] += n
            portals_seen.add(canon)

        # Manual entries
        for entry in d.get("manual", []):
            p = normalise(entry.get("portal", ""))
            counts[p]["manual"] += 1
            portals_seen.add(p)

        # Skipped: we need to look inside _skipped_jobs → job.portal
        for entry in d.get("_skipped_jobs", []):
            p = normalise(entry.get("job", {}).get("portal", ""))
            counts[p]["skipped"] += 1
            portals_seen.add(p)

        for p in portals_seen:
            c = counts[p]
            c["n_runs"] += 1
            if c["first_seen"] is None or date_str < c["first_seen"]:
                c["first_seen"] = date_str
            if c["last_seen"] is None or date_str > c["last_seen"]:
                c["last_seen"] = date_str

    return dict(counts)


def fmt_row(name, c, threshold=10.0):
    total = c["applied"] + c["manual"] + c["skipped"]
    pct = (c["applied"] / total * 100) if total > 0 else 0
    bar = "█" * int(pct / 5)
    flag = "🟢" if pct >= threshold * 2 else ("🟡" if pct >= threshold else "🔴")
    return f"{flag} {name:<14} applied={c['applied']:>4}  manual={c['manual']:>4}  skipped={c['skipped']:>4}  total={total:>5}  apply%={pct:>5.1f}%  {bar:<22} (runs={c['n_runs']}, {c['first_seen']}→{c['last_seen']})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="Only count logs on/after this date (YYYY-MM-DD)")
    ap.add_argument("--threshold", type=float, default=10.0, help="Apply%% below this = disable candidate")
    ap.add_argument("--disable", action="store_true", help="Comment-out portal_map entries below threshold")
    args = ap.parse_args()

    since = args.since or FIX_DATE  # default: post-fix only
    print(f"=== Portal Performance — logs on/after {since} ===\n")

    counts = load_counts(since=since)

    if not counts:
        print(f"No application logs found after {since}.")
        print("Run the pipeline for a few days then re-run this script.")
        return

    # Sort by apply% descending
    rows = sorted(counts.items(), key=lambda x: -(x[1]["applied"] / max(1, x[1]["applied"] + x[1]["manual"] + x[1]["skipped"])))
    print(f"{'Portal':<16} {'Applied':>8} {'Manual':>7} {'Skip':>5} {'Total':>6} {'Apply%':>7}  Trend")
    print("=" * 100)
    for name, c in rows:
        print(fmt_row(name, c, threshold=args.threshold))

    # Pre vs post comparison
    print(f"\n=== Lifetime pre-fix (before {FIX_DATE}) ===")
    pre = load_counts()
    pre_filtered = {k: v for k, v in pre.items() if v["last_seen"] and v["last_seen"] < FIX_DATE}
    if not pre_filtered:
        print("(no pre-fix data)")
    else:
        for k, v in sorted(pre_filtered.items(), key=lambda x: x[0]):
            print(fmt_row(k, v, threshold=args.threshold))

    print(f"\n=== Δ vs pre-fix ===")
    print(f"{'Portal':<16} {'Pre':>6} {'Post':>6} {'Δ':>8}")
    for name, post in rows:
        pre_c = pre_filtered.get(name, {"applied": 0, "manual": 0, "skipped": 0})
        post_total = post["applied"]
        pre_total = pre_c["applied"]
        delta = post_total - pre_total
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"{name:<16} {pre_total:>6} {post_total:>6} {arrow}{abs(delta):>7}")

    # Disable candidates
    disable_list = []
    print(f"\n=== Disable candidates (<{args.threshold}% apply) ===")
    for name, c in rows:
        total = c["applied"] + c["manual"] + c["skipped"]
        pct = (c["applied"] / total * 100) if total > 0 else 0
        if pct < args.threshold and total >= 5:  # only if we have enough data
            disable_list.append(name)
            print(f"  🔴 {name}: {pct:.1f}% ({total} jobs processed)")

    if not disable_list:
        print(f"  (none — all portals above {args.threshold}% or insufficient data)")

    # Apply disable if asked
    if args.disable and disable_list:
        aa = PROJ_DIR / "auto_applier.py"
        text = aa.read_text(encoding="utf-8")
        # Find portal_map blocks
        # Match: portal_map = { ... } — only top-level {...}, not the {args.portal: ...} re-assignment
        # We'll do a string replace on specific portal lines
        n_disabled = 0

        if disable_list:
            portals_pattern = "|".join(map(re.escape, disable_list))
            line_old = re.compile(rf'^(\s*)"({portals_pattern})":\s+[A-Za-z]+\w*Portal,', re.MULTILINE)

            today_str = datetime.now().date()
            portal_counts = defaultdict(int)

            def repl(m):
                portal = m.group(2)
                portal_counts[portal] += 1
                return f'{m.group(1)}# "{portal}": DISABLED (weekly_compare.py {today_str})'

            text, n_disabled = line_old.subn(repl, text)

            for portal, n in portal_counts.items():
                print(f"  ✂️  Commented {n} entries for {portal}")

        if n_disabled > 0:
            aa.write_text(text, encoding="utf-8")
            print(f"\n✅ Wrote {n_disabled} disabled portal lines to auto_applier.py")
            print("   Verify: python auto_applier.py --list  (next run)")
        else:
            print("\n  (no portal_map lines matched — check names)")

    print("\n=== Recommendation ===")
    top = [n for n, c in rows if (c["applied"] + c["manual"] + c["skipped"]) > 0][:3]
    print(f"  Top performers: {', '.join(top) if top else '(no data yet)'}")
    print(f"  Disable: {', '.join(disable_list) if disable_list else 'nobody'}")


if __name__ == "__main__":
    main()
