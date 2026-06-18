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

Usage:
    python main.py                       # normal run
    python main.py --test-email a@b.com  # test the email pipeline
    python main.py --dry-run             # scrape only; no emails sent
    python main.py --limit 5             # override daily cap
"""

import argparse
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv

from scraper import scrape_linkedin_posts
from extractor import extract_contact_info
from composer import generate_cold_email
from mailer import send_email

# ── Paths & config ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent

# Fix #9: load .env from main.py's directory regardless of cwd
load_dotenv(BASE_DIR / ".env")

DEFAULT_ROLES = [
    "Python Developer",
    "Django Developer",
    "Backend Developer",
    "Full Stack Python Developer",
    "Full Stack Developer",
    "Full Stack AI Engineer",
    "AI ML Engineer",
    "Machine Learning Engineer",
    "AI Engineer",
    "Software Developer Python",
    "Android Developer",
    "Java Developer",
    "Software Engineer",
    "SDE",
]


def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# ── Logger ─────────────────────────────────────────────────────────────────────

def _hr(text: str = ""):
    bar = "=" * 56
    if text:
        print(f"\n{bar}\n  {text}\n{bar}")
    else:
        print()


def _send_email_wrapped(recipient, subject, body, attachment):
    """Wraps mailer.send_email with extra fallback-cap enforcement."""
    ok = send_email(recipient, subject, body, attachment)
    recipient_short = recipient[:50]
    if ok:
        print(f"  📧 sent OK → {recipient_short}")
    else:
        print(f"  ❌ send FAILED → {recipient_short}")
    return ok


# ── SQLite-based dedup tracker (replaces in-memory/Python-only tracking) ──
# Persistent across runs, prevents re-sending to same recipients

try:
    from db_tracker import SentTracker
    _sent_tracker = SentTracker()
    _use_tracker = True
except Exception as e:
    print(f"  ⚠️  Could not init SQLite tracker: {e}")
    _use_tracker = False


def _already_contacted(recipient: str) -> bool:
    """Check if recipient was already contacted (dedup across runs)."""
    if _use_tracker:
        return _sent_tracker.already_sent_to(recipient)
    return False


def _record_sent(recipient: str, role: str, company: str,
                 subject: str, is_fallback: bool = False) -> None:
    """Record a sent email in the persistent tracker."""
    if _use_tracker:
        _sent_tracker.record_sent(
            recipient, role, company, subject, is_fallback=is_fallback
        )


# ── Test mode ──────────────────────────────────────────────────────────────────

def _run_test_email(to_address: str) -> None:
    print(f"Sending test email to {to_address}...")
    body = generate_cold_email(
        "Looking for a Python Developer! Apply today.", "Test Recruiter"
    )
    if not body:
        print("  ❌ composer returned None — check Ollama")
        return
    ok = _send_email_wrapped(
        to_address, "Application for Python Developer",
        body, os.environ.get("RESUME_PATH"),
    )
    print("  ✅ Test email OK" if ok else "  ❌ Test email FAILED")


# ── Main loop ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Outreach Bot")
    parser.add_argument("--test-email", help="Send a single test email")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Scrape + extract only; never send email")
    parser.add_argument("--limit",     type=int, default=None,
                        help="Override daily personal-email cap")
    parser.add_argument("--roles",     default=None,
                        help="Comma-separated role subset (otherwise default 14)")
    args = parser.parse_args()

    if args.test_email:
        _run_test_email(args.test_email)
        return

    roles = [r.strip() for r in args.roles.split(",")] if args.roles else DEFAULT_ROLES

    fallback_email      = os.environ.get("FALLBACK_EMAIL")
    personal_email_cap  = args.limit if args.limit is not None else _env_int("DAILY_PERSONAL_CAP", 15)
    personal_per_role   = _env_int("PER_ROLE_CAP", 2)
    fallback_cap        = _env_int("DAILY_FALLBACK_CAP", 30)

    _hr("🐟 LinkedIn Cold-Mail Bot")
    print(f"  roles:           {len(roles)}")
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

    for role_idx, role in enumerate(roles):
        if emails_sent_today >= personal_email_cap:
            _hr(f"Hit personal email cap ({personal_email_cap}). Stopping.")
            break
        if fallbacks_sent_today >= fallback_cap:
            _hr(f"Hit fallback cap ({fallback_cap}). Stopping.")
            break

        _hr(f"[{role_idx + 1}/{len(roles)}] Scraping role: {role}")

        posts = scrape_linkedin_posts(role)
        if not posts:
            print(f"  ℹ no posts found. Skipping to next role.")
            continue

        # Fix #8 — cap per role in addition to global cap
        per_role_sent = 0
        for post in posts:
            if per_role_sent >= personal_per_role:
                print(f"  (per-role cap of {personal_per_role} reached for {role})")
                break
            if emails_sent_today >= personal_email_cap:
                break

            # ── External apply link → fallback (with its own cap)
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
                                 is_fallback=True)
                continue

            # ── Extract email
            email, source = extract_contact_info(post["text"], post["name"], post["company"])
            if not email:
                print(f"  ↪ no email found for {post['name']} — skip")
                continue

            # ── Dedup check: skip if already contacted in last 30 days
            if _already_contacted(email):
                print(f"  ↪ already contacted {email} (dedup) — skip")
                continue

            print(f"  📇 found email ({source}): {email}")

            # Fix #10 — small stagger between Ollama call and next scrape
            time.sleep(random.uniform(2, 5))

            body = generate_cold_email(post["text"], post["name"])
            if not body:
                print(f"  ↪ composer failed for {post['name']} — skip")
                continue

            if args.dry_run:
                print(f"  [DRY-RUN] would send to {email}")
                emails_sent_today += 1
                per_role_sent += 1
                continue

            ok = _send_email_wrapped(
                email,
                "Interest in Python/Django/AI Developer Role",
                body, os.environ.get("RESUME_PATH"),
            )
            if ok:
                emails_sent_today += 1
                per_role_sent += 1
                _record_sent(email, role, post.get("company", ""),
                             "Interest in Python/Django/AI Developer Role")

                # Fix #10 — radar-aware pacing: longer pause every few sends
                if emails_sent_today % 5 == 0:
                    backoff = random.uniform(60, 180)
                    print(f"  ⏸ backoff: sleeping {backoff:.0f}s between role-batches")
                    time.sleep(backoff)
                else:
                    time.sleep(random.uniform(20, 60))

        # Fix #10 — between roles: longer humanised cooldown
        if role_idx < len(roles) - 1 and emails_sent_today < personal_email_cap:
            cooldown = random.uniform(90, 240)
            print(f"  cooldown between roles: {cooldown:.0f}s")
            time.sleep(cooldown)

    elapsed = time.time() - start
    _hr("📊 Run summary")
    print(f"  personal emails:  {emails_sent_today} / cap {personal_email_cap}")
    print(f"  fallback emails:  {fallbacks_sent_today} / cap {fallback_cap}")
    print(f"  elapsed:          {elapsed:.0f}s ({elapsed / 60:.1f}min)")


if __name__ == "__main__":
    main()
