"""main.py — Orchestrator for the LinkedIn cold-mail bot.

Fixes applied:
- #5: Separate daily cap for fallback (job-link) emails — won't spam
  your fallback inbox.
- #8: Distribute the 15-email daily cap across *all* target roles
  (not just the first 15 posts of the first role). Each role gets
  PER_ROLE_CAP, default 2.
- #9: Use an absolute path to .env (next to main.py), not CWD-relative.
- #10: Random staggering between actions + per-role cooldown so we
  look human.
- Verbose progress logging so cron failures show actionable output.

UPDATE 2026-08-21 (per 2-month plan):
- Tier-based targeting (T1/T2/T3) — prioritizes founders > hiring managers > recruiters
- 5 email templates (T1-T5) — picked per tier + outreach type
- Reply tracking — auto-records replies + computes reply_rate
- Follow-up scheduling — auto Day 5 follow-ups via templates.py
- CSV export — exports tracker for Google Sheets import

Usage:
    python main.py                       # normal run
    python main.py --test-email a@b.com  # test the email pipeline
    python main.py --dry-run             # scrape only; no emails sent
    python main.py --limit 5             # override daily cap
    python main.py --template T1         # override default template (T2)
    python main.py --tier T1             # target only Tier 1 founders
    python main.py --export              # export to CSV for Google Sheets
    python main.py --followups           # send all due follow-ups
"""

import argparse
import os
import random
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

from scraper import scrape_linkedin_posts, scrape_recruiter_profile
from extractor import extract_contact_info
from composer import generate_cold_email
from mailer import send_email
from templates import list_templates

import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared_utils import setup_logging, log_metric

# ── Paths & config ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent

log = setup_logging("linkedin_outreach", log_dir=BASE_DIR / "logs")

# ── Updated role list (per 2-month plan) — AI/ML focus ────────────────
DEFAULT_ROLES = [
    "Full Stack AI Engineer",      # PRIMARY target
    "AI Engineer",
    "AI ML Engineer",
    "Machine Learning Engineer",
    "Backend Engineer",             # secondary
    "Python Developer",
    "Django Developer",
    "Full Stack Developer",
    "Full Stack Python Developer",
    "Software Engineer",
    "SDE",
]

# ── Tier-priority mapping ─────────────────────────────────────────────
# T1 = founders/CEOs (highest priority, smallest daily cap to be safe)
# T2 = hiring managers / engineering leads
# T3 = recruiters / HR (largest daily cap)
DEFAULT_TIERS = ["T1", "T2", "T3"]


def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _hr(text: str = ""):
    bar = "=" * 56
    if text:
        print(f"\n{bar}\n  {text}\n{bar}")
    else:
        print()


def _send_email_wrapped(recipient, subject, body, attachment):
    ok = send_email(recipient, subject, body, attachment)
    recipient_short = recipient[:50]
    if ok:
        print(f"  📧 sent OK → {recipient_short}")
    else:
        print(f"  ❌ send FAILED → {recipient_short}")
    return ok


# ── SQLite-based dedup tracker ────────────────────────────────────────

try:
    from db_tracker import SentTracker
    _sent_tracker = SentTracker()
    _use_tracker = True
except Exception as e:
    print(f"  ⚠️  Could not init SQLite tracker: {e}")
    _use_tracker = False


def _already_contacted(recipient: str) -> bool:
    if _use_tracker:
        return _sent_tracker.already_sent_to(recipient)
    return False


def _record_sent(recipient: str, role: str, company: str,
                 subject: str, is_fallback: bool = False,
                 tier: str = "T3", template_id: str = "T2") -> None:
    if _use_tracker:
        _sent_tracker.record_sent(
            recipient, role, company, subject,
            is_fallback=is_fallback, tier=tier, template_id=template_id
        )


# ── Test mode ──────────────────────────────────────────────────────────

def _run_test_email(to_address: str) -> None:
    print(f"Sending test email to {to_address}...")
    subject, body = generate_cold_email(
        "Looking for a Python Developer! Apply today.", "Test Recruiter",
        template_id="T2", tier="T3"
    )
    if not body:
        print("  ❌ composer returned None — check Ollama")
        return
    ok = _send_email_wrapped(
        to_address, subject, body, os.environ.get("RESUME_PATH"),
    )
    print("  ✅ Test email OK" if ok else "  ❌ Test email FAILED")


# ── Follow-up mode ────────────────────────────────────────────────────

def _run_followups() -> None:
    """Send all due follow-ups (auto Day-5 reminders)."""
    if not _use_tracker:
        print("  ❌ Tracker not available — cannot send follow-ups")
        return
    due = _sent_tracker.get_due_followups()
    if not due:
        print("  ℹ No due follow-ups today")
        return
    print(f"  📬 {len(due)} follow-up(s) due today")
    for f in due:
        recipient = f["recipient"]
        template_id = f["template_id"]
        if _already_contacted(recipient):
            # Already re-contacted since follow-up was scheduled — skip
            _sent_tracker.mark_followup_sent(f["id"])
            continue
        # Look up last sent email to get role/company/subject
        # (simplified — just send generic T5 follow-up)
        subject = f"Following up — quick reminder"
        body = f"""Hi there,

Just a quick follow-up on my earlier note. Happy to share more about my work if useful.

— Venu
github.com/venu0807
"""
        ok = _send_email_wrapped(recipient, subject, body,
                                  os.environ.get("RESUME_PATH"))
        if ok:
            _sent_tracker.mark_followup_sent(f["id"])
            print(f"  ✅ Follow-up sent → {recipient[:50]}")
        time.sleep(random.uniform(30, 90))


# ── Export mode ───────────────────────────────────────────────────────

def _run_export() -> None:
    """Export tracker DB to CSV for Google Sheets import."""
    if not _use_tracker:
        print("  ❌ Tracker not available — cannot export")
        return
    out_path = BASE_DIR / "outreach_export.csv"
    _sent_tracker.export_to_csv(str(out_path))
    print(f"  ✅ Exported to {out_path}")
    stats = _sent_tracker.stats()
    print(f"  📊 Stats:")
    print(f"     total sent:     {stats['total_sent']}")
    print(f"     today sent:     {stats['today_sent']}")
    print(f"     total replied:  {stats['total_replied']}")
    print(f"     reply rate:     {stats['reply_rate']*100:.1f}%")
    print(f"     pending follow-ups: {stats['pending_followups']}")
    if stats['per_role']:
        print(f"     per-role:")
        for role, cnt in stats['per_role'].items():
            print(f"       {role}: {cnt}")
    if stats['per_tier']:
        print(f"     per-tier:")
        for tier, cnt in stats['per_tier'].items():
            print(f"       {tier}: {cnt}")


# ── Main loop ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Outreach Bot")
    parser.add_argument("--test-email", help="Send a single test email")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape + extract only; never send email")
    parser.add_argument("--limit", type=int, default=None,
                        help="Override daily personal-email cap")
    parser.add_argument("--roles", default=None,
                        help="Comma-separated role subset (otherwise default 11)")
    parser.add_argument("--tiers", default="T1,T2,T3",
                        help="Comma-separated tiers (T1=founders, T2=HM, T3=recruiters)")
    parser.add_argument("--template", default="T2",
                        choices=list_templates(),
                        help="Email template (default T2 = LinkedIn hiring manager DM)")
    parser.add_argument("--export", action="store_true",
                        help="Export tracker DB to CSV for Google Sheets")
    parser.add_argument("--followups", action="store_true",
                        help="Send all due follow-ups (Day 5)")
    args = parser.parse_args()

    if args.test_email:
        _run_test_email(args.test_email)
        return
    if args.export:
        _run_export()
        return
    if args.followups:
        _run_followups()
        return

    roles = [r.strip() for r in args.roles.split(",")] if args.roles else DEFAULT_ROLES
    tiers = [t.strip() for t in args.tiers.split(",")]

    fallback_email = os.environ.get("FALLBACK_EMAIL")
    personal_email_cap = args.limit if args.limit is not None else _env_int("DAILY_PERSONAL_CAP", 15)
    personal_per_role = _env_int("PER_ROLE_CAP", 2)
    fallback_cap = _env_int("DAILY_FALLBACK_CAP", 30)

    _hr("🐟 LinkedIn Cold-Mail Bot")
    print(f"  roles:           {len(roles)}")
    print(f"  tiers:           {tiers}")
    print(f"  template:        {args.template}")
    print(f"  personal cap:    {personal_email_cap} (per role: ≤{personal_per_role})")
    print(f"  fallback cap:    {fallback_cap} → {fallback_email or '(disabled)'}")
    print(f"  dry-run:         {args.dry_run}")
    rate_label = "humanised random"
    print(f"  rate-limit mode: {rate_label}")

    if not fallback_email:
        print("\n  ⚠ FALLBACK_EMAIL not set — posts with external links will be skipped.\n")

    emails_sent_today = 0
    fallbacks_sent_today = 0
    start = time.time()

    # Priority order: T1 founders → T2 hiring managers → T3 recruiters
    tier_cycle = []
    for tier in tiers:
        tier_cycle.extend([tier] * personal_email_cap)

    for role_idx, role in enumerate(roles):
        if emails_sent_today >= personal_email_cap:
            _hr(f"Hit personal email cap ({personal_email_cap}). Stopping.")
            break
        if fallbacks_sent_today >= fallback_cap:
            _hr(f"Hit fallback cap ({fallback_cap}). Stopping.")
            break

        # Pick tier in cycle order
        current_tier = tier_cycle[emails_sent_today] if emails_sent_today < len(tier_cycle) else "T3"

        _hr(f"[{role_idx + 1}/{len(roles)}] Scraping role: {role} (tier={current_tier})")

        posts = scrape_linkedin_posts(role)
        if not posts:
            print(f"  ℹ no posts found. Skipping to next role.")
            continue

        per_role_sent = 0
        for post in posts:
            if per_role_sent >= personal_per_role:
                print(f"  (per-role cap of {personal_per_role} reached for {role})")
                break
            if emails_sent_today >= personal_email_cap:
                break

            # ── External apply link → fallback
            if post.get("has_link"):
                if not fallback_email:
                    print(f"  ↪ @{post['name']} has external link, no fallback set — skip")
                    continue
                if fallbacks_sent_today >= fallback_cap:
                    print(f"  ↪ fallback cap reached, skipping link post")
                    continue
                body = (
                    f"Job posted by {post['name']} at {post['company']}.\n\n"
                    f"Post Text:\n{post['text']}\n\nLink Context:\n{post['link']}"
                )
                ok = _send_email_wrapped(
                    fallback_email,
                    f"Job Link: {post['name']} - {post['company']}",
                    body, None,
                )
                if ok:
                    fallbacks_sent_today += 1
                    _record_sent(fallback_email, role, post.get("company", ""),
                                 f"Job Link: {post['name']} - {post['company']}",
                                 is_fallback=True, tier=current_tier,
                                 template_id="T4")
                continue

            # ── Extract email
            email, source = extract_contact_info(post["text"], post["name"], post["company"])
            if not email:
                print(f"  ↪ no email found for {post['name']} — skip")
                continue

            # ── Dedup
            if _already_contacted(email):
                print(f"  ↪ already contacted {email} (dedup) — skip")
                continue

            print(f"  📇 found email ({source}): {email}")

            time.sleep(random.uniform(2, 5))

            bio_text = scrape_recruiter_profile(post.get("profile_url", ""))

            subject, body = generate_cold_email(
                post["text"], post["name"], bio_text,
                template_id=args.template, tier=current_tier,
            )
            if not body:
                print(f"  ↪ composer failed for {post['name']} — skip")
                continue

            if args.dry_run:
                print(f"  [DRY-RUN] would send to {email}")
                print(f"  [DRY-RUN] Subject: {subject}")
                print(f"  [DRY-RUN] Body:\n{body}\n---")
                emails_sent_today += 1
                per_role_sent += 1
                continue

            ok = _send_email_wrapped(
                email, subject, body, os.environ.get("RESUME_PATH"),
            )
            if ok:
                emails_sent_today += 1
                per_role_sent += 1
                _record_sent(email, role, post.get("company", ""),
                             subject, tier=current_tier,
                             template_id=args.template)
                log_metric("emails_sent", "Cold Outreach", 1)

                # Humanised pacing
                if emails_sent_today % 5 == 0:
                    backoff = random.uniform(60, 180)
                    print(f"  ⏸ backoff: sleeping {backoff:.0f}s between role-batches")
                    time.sleep(backoff)
                else:
                    time.sleep(random.uniform(20, 60))

        # Between roles: longer humanised cooldown
        if role_idx < len(roles) - 1 and emails_sent_today < personal_email_cap:
            cooldown = random.uniform(90, 240)
            print(f"  cooldown between roles: {cooldown:.0f}s")
            time.sleep(cooldown)

    elapsed = time.time() - start
    _hr("📊 Run summary")
    print(f"  personal emails:  {emails_sent_today} / cap {personal_email_cap}")
    print(f"  fallback emails:  {fallbacks_sent_today} / cap {fallback_cap}")
    print(f"  elapsed:          {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    if _use_tracker:
        stats = _sent_tracker.stats()
        print(f"  reply rate:       {stats['reply_rate']*100:.1f}% ({stats['total_replied']}/{stats['total_sent']})")
        print(f"  pending follow-ups: {stats['pending_followups']}")


if __name__ == "__main__":
    main()
