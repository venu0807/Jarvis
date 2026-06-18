"""portal_rates.py — analyse per-portal success rates and recommend cuts."""
import sqlite3
from pathlib import Path

DB = Path("output/jobs.db")
if not DB.exists():
    DB = Path.home() / ".jarvis" / "automations" / "job-automation" / "output" / "jobs.db"

con = sqlite3.connect(str(DB))
rows = con.execute("SELECT portal, status, COUNT(*) FROM jobs GROUP BY portal, status").fetchall()
con.close()

# Merge case variants (LinkedIn / linkedin are the same portal)
agg = {}
for portal, status, count in rows:
    key = (portal or "unknown").lower().strip()
    agg.setdefault(key, {})[status] = agg.get(key, {}).get(status, 0) + count

print(f"{'Portal':<18}{'APPL':>6}{'MANU':>6}{'SKIP':>6}{'ERR':>6}{'TOT':>6}{'Apply%':>9}  Recommendation")
print("-" * 95)
results = []
for p, s in sorted(agg.items()):
    applied = s.get("applied", 0)
    manual  = s.get("manual", 0)
    skipped = s.get("skipped", 0)
    errored = s.get("error", 0)
    total   = applied + manual + skipped + errored
    pct     = applied / total * 100 if total else 0
    results.append((p, applied, manual, skipped, errored, total, pct))

results.sort(key=lambda r: -r[6])

for p, appl, man, sk, er, tot, pct in results:
    bar = "█" * max(1, int(pct / 4)) if pct > 0 else ""
    if tot < 10:
        verdict = f"KEEP (insufficient data — {tot} jobs)"
        mark = "?"
    elif pct >= 30:
        verdict = "KEEP — strong performer"
        mark = "✅"
    elif pct >= 15:
        verdict = "KEEP — acceptable"
        mark = "⚠️"
    elif pct >= 5:
        verdict = f"WATCH — only {pct:.1f}%"
        mark = "⚠️"
    else:
        verdict = f"REMOVE candidate — {pct:.1f}% over {tot} jobs"
        mark = "❌"
    print(f"{p:<18}{appl:>6}{man:>6}{sk:>6}{er:>6}{tot:>6}{pct:>8.1f}%  {mark} {verdict} {bar}")

print()
print("=== Cut list (recommendation) ===")
KEEP_MIN_PCT = 15        # below this = remove
KEEP_MIN_DATA = 10       # below this many jobs = keep (insufficient data)
to_remove = []
to_keep_weak = []
for p, appl, man, sk, er, tot, pct in results:
    if tot < KEEP_MIN_DATA:
        continue  # too little data to judge
    if pct < KEEP_MIN_PCT:
        to_remove.append((p, appl, man, sk, er, tot, pct))

if to_remove:
    for p, *_ in to_remove:
        print(f"   ❌ remove {p}")
else:
    print("   (none qualify for removal under current thresholds)")

print(f"\n   Thresholds: remove if <{KEEP_MIN_PCT}% AND ≥{KEEP_MIN_DATA} data points")
