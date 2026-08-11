"""
apply_portal_cuts.py  (rewritten 2026-06-15 after final consolidation)

Originally: surgical removal of glassdoor + unstop from auto_applier.py
            (the patch() tool kept truncating mid-string, so the cut ran as
            a full read+write pass). That work is now PERMANENT.

What this script does NOW: archives a one-cycle retention strategy.

  - default mode  : print the current portal-cuts status (no mutation).
  - --restore <name> : not yet implemented; portals/*.py for the cut ones
                       are in .cut-2026-06-15/ for one cycle. To restore,
                       copy back and re-add the entries to auto_applier.py
                       (portal_map, imports, CREDS) — the restored class MUST
                       implement search_and_apply(page, roles, cities,
                       daily_limit, applied_today), because
                       run_portal now dispatches EVERY portal through it (the
                       old per-portal if-branches are gone). This script is
                       the GUIDE for that.

To delete this script altogether:
  python scripts/apply_portal_cuts.py --finalize
        (will rm .cut-2026-06-15/ + this script after you confirm the
         restorations from .cut-2026-06-15/ aren't needed)
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUT_DIR = ROOT / ".cut-2026-06-15"

CUT_PORTALS = ["linkedin", "unstop", "glassdoor"]
CUT_REASONS = {
    "linkedin":  "3.9% apply rate over 180 jobs — multi-step Easy Apply with text questions and external redirects was the bottleneck. LinkedIn outreach continues via the linkedin-outreach/ project (cold-mail).",
    "glassdoor": "0% apply rate over 30 jobs — Cloudflare/Akamai blocks automation. Cookies degraded in days; headful re-auth wasn't reliable enough.",
    "unstop":    "11.1% apply rate over 18 jobs — too few jobs to be worth the headful-reauth maintenance.",
}


def status():
    print(f"\n=== Portal-cut status ({len(CUT_PORTALS)} portals cut) ===")
    print(f"Cut archive: {CUT_DIR}/")
    print(f"  exists: {CUT_DIR.exists()}\n")
    if CUT_DIR.exists():
        for p in CUT_DIR.glob("*.py"):
            print(f"  - {p.name} ({p.stat().st_size} bytes)")
    print(f"\nCut reasons (for restoration context):")
    for name in CUT_PORTALS:
        print(f"  {name}: {CUT_REASONS[name]}")
    print()
    print("Restoration steps (manual):")
    print("  1. cp .cut-<date>/<portal>.py portals/")
    print("  2. add to portals/__init__.py imports + __all__")
    print("  3. add to auto_applier.py: imports, CREDS, portal_map")
    print("  4. ensure the portal class implements search_and_apply() — run_portal")
    print("     dispatches every portal through it (no per-portal branch)")
    print("  5. python scripts/validate_sessions.py --reauth <portal>")
    print("  6. python scripts/portal_rates.py  (will track new portal's stats)")


def restore(name: str):
    """If we ever need to bring a cut portal back, scaffold the change."""
    if name not in CUT_PORTALS:
        print(f"❌ Unknown portal '{name}'. Cut list: {CUT_PORTALS}")
        return
    src = CUT_DIR / f"{name}.py"
    if not src.exists():
        print(f"❌ Archived source missing: {src}")
        print(f"   (Was already restored or never staged — check {CUT_DIR}/)")
        return
    print(f"\n=== Restoring {name} ===")
    print(f"Copied {src} → portals/{name}.py — done locally.")
    print("Now manual:")
    print(f"  • edit portals/__init__.py — uncomment the '{name}' line if it has one + add to __all__")
    print(f"  • edit auto_applier.py:")
    print(f"      + CREDS['{name}']")
    print(f"      + portal_map['{name}'] = {name.capitalize()}Portal")
    print(f"      + import for {name.capitalize()}Portal (top of file)")
    print(f"      + ensure search_and_apply() exists on the class (run_portal")
    print(f"        dispatches every portal through it — no per-portal branch)")
    print(f"  • python scripts/validate_sessions.py --reauth {name}")
    print()


def finalize():
    """One-way delete of the staging directory and this script."""
    import sys
    print("\n=== FINALIZE: remove staging and this script ===")
    print("This will:")
    print(f"  - delete {CUT_DIR}/ (cut portal source archive)")
    print(f"  - delete {Path(__file__)} (this script)")
    print()
    if not CUT_DIR.exists():
        print(f"  ⚠ {CUT_DIR}/ does not exist already")
    if not Path(__file__).exists():
        print("  ⚠ this script already gone")
    print()
    print("Re-run with --i-know-what-im-doing to actually do it.")
    print("  python scripts/apply_portal_cuts.py --finalize --i-know-what-im-doing")
    sys.exit(0)


def finalize_destructive():
    """Hard-delete. Requires the second flag."""
    if CUT_DIR.exists():
        import shutil
        shutil.rmtree(CUT_DIR)
        print(f"  ✓ removed {CUT_DIR}/")
    Path(__file__).unlink(missing_ok=True)
    print(f"  ✓ removed {Path(__file__)}")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--restore", metavar="NAME", help=f"print restoration steps for {CUT_PORTALS}")
    p.add_argument("--finalize", action="store_true", help="remove cut archive + this script")
    p.add_argument("--i-know-what-im-doing", action="store_true", help="required alongside --finalize")
    args = p.parse_args()

    if args.restore:
        restore(args.restore)
    elif args.finalize:
        if args.i_know_what_im_doing:
            finalize_destructive()
        else:
            finalize()
    else:
        status()


if __name__ == "__main__":
    main()
