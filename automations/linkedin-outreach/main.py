"""main.py — Orchestrator for the LinkedIn Cold-Mail Bot (Direct Recruiter Outreach).

Key Behavior:
- NEVER sends job post notification emails to the user (no self-spam).
- Extracts recruiter email directly from LinkedIn hiring posts, author profiles, and bio.
- Composes smooth, polite, professional cold emails tailored to Venu (MCA 2026, Python/Full Stack).
- Sends smooth cold email directly to the recruiter with attached resume.
- Records all interactions in sent_tracker.db and Outreach Hub.
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

# ── Target Roles ──────────────────────────────────────────────────────────────
DEFAULT_ROLES = [
    "Python Developer",
    "Full Stack Python Developer",
    "Django Developer",
    "Software Engineer",
    "Web Developer Intern",
    "AI ML Engineer",
    "Full Stack Developer",
    "Software Tester",
    "SDE",
]

# ── Tier-priority mapping ─────────────────────────────────────────────────────
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
    print(f"Sending test cold email to {to_address}...")
    subject, body = generate_cold_email(
        "Hiring Python & Web Developer Interns at Tech Solutions! Reach out if interested.",
        "Hiring Manager",
        template_id="T2", tier="T2"
    )
    if not body:
        print("  ❌ composer returned None — check Ollama")
        return
    ok = _send_email_wrapped(
        to_address, subject, body, os.environ.get("RESUME_PATH"),
    )
    print("  ✅ Test cold email OK" if ok else "  ❌ Test email FAILED")


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
            _sent_tracker.mark_followup_sent(f["id"])
            continue
        subject = f"Following up on our conversation — Venu Gopal Reddy"
        body = f"""Hi there,

I hope you're having a good week.

Just wanted to follow up briefly on my earlier note regarding software engineering opportunities. I'd love to connect if you have 10 minutes this week.

My resume and portfolio (github.com/venu0807) are available anytime.

Best regards,
Venu Gopal Reddy
pvgreddy3@gmail.com
"""
        ok = _send_email_wrapped(recipient, subject, body, os.environ.get("RESUME_PATH"))
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


# ── Main loop ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Cold Outreach Bot")
    parser.add_argument("--test-email", help="Send a single test email")
    parser.add_argument("--dry-run", action="store_true", help="Scrape + extract only; never send email")
    parser.add_argument("--limit", type=int, default=None, help="Override daily recruiter-email cap")
    parser.add_argument("--roles", default=None, help="Comma-separated role subset")
    parser.add_argument("--tiers", default="T1,T2,T3", help="Comma-separated tiers (T1=founders, T2=HM, T3=recruiters)")
    parser.add_argument("--template", default="T2", choices=list_templates(), help="Email template")
    parser.add_argument("--export", action="store_true", help="Export tracker DB to CSV")
    parser.add_argument("--followups", action="store_true", help="Send all due follow-ups (Day 5)")
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

    personal_email_cap = args.limit if args.limit is not None else _env_int("DAILY_PERSONAL_CAP", 15)
    personal_per_role = _env_int("PER_ROLE_CAP", 2)

    _hr("🤝 LinkedIn Cold Outreach Engine (Recruiter Direct)")
    print(f"  roles:           {len(roles)}")
    print(f"  tiers:           {tiers}")
    print(f"  template:        {args.template}")
    print(f"  personal cap:    {personal_email_cap} (per role: ≤{personal_per_role})")
    print(f"  dry-run:         {args.dry_run}")
    print(f"  self-spam:       DISABLED (No job notification emails sent to user)")

    emails_sent_today = 0
    start = time.time()

    # Priority order: T1 founders → T2 hiring managers → T3 recruiters
    tier_cycle = []
    for tier in tiers:
        tier_cycle.extend([tier] * personal_email_cap)

    for role_idx, role in enumerate(roles):
        if emails_sent_today >= personal_email_cap:
            _hr(f"Hit daily recruiter email cap ({personal_email_cap}). Stopping.")
            break

        current_tier = tier_cycle[emails_sent_today] if emails_sent_today < len(tier_cycle) else "T3"

        _hr(f"[{role_idx + 1}/{len(roles)}] Scanning LinkedIn posts for: {role} (tier={current_tier})")

        posts = scrape_linkedin_posts(role)
        if not posts:
            print(f"  ℹ No posts found for {role}. Moving to next role.")
            continue

        per_role_sent = 0
        for post in posts:
            if per_role_sent >= personal_per_role:
                print(f"  (Per-role cap of {personal_per_role} reached for {role})")
                break
            if emails_sent_today >= personal_email_cap:
                break

            # ── 1. Always attempt to extract recruiter email from post text and author
            email, source = extract_contact_info(post.get("text", ""), post.get("name", ""), post.get("company", ""))
            
            # If not found directly in text, check link context or author bio
            if not email and post.get("link"):
                email, source = extract_contact_info(post.get("link", ""), post.get("name", ""), post.get("company", ""))

            # ── 2. If NO recruiter email is found, skip cleanly (NEVER email user)
            if not email:
                print(f"  ↪ No recruiter email found for post by @{post.get('name', 'Unknown')} — skipped")
                continue

            # ── 3. Dedup check
            if _already_contacted(email):
                print(f"  ↪ Already contacted {email} (dedup) — skipped")
                continue

            print(f"  🎯 Found Recruiter Email ({source}): {email}")

            time.sleep(random.uniform(2, 5))

            bio_text = scrape_recruiter_profile(post.get("profile_url", ""))

            # ── 4. Generate smooth, professional cold email
            subject, body = generate_cold_email(
                post.get("text", ""), post.get("name", "Hiring Manager"), bio_text,
                template_id=args.template, tier=current_tier,
            )
            if not body:
                print(f"  ↪ Composer could not generate email for {post.get('name', '')} — skipped")
                continue

            if args.dry_run:
                print(f"  [DRY-RUN] Would send smooth cold email to recruiter: {email}")
                print(f"  [DRY-RUN] Subject: {subject}")
                print(f"  [DRY-RUN] Body:\n{body}\n---")
                emails_sent_today += 1
                per_role_sent += 1
                continue

            # ── 5. Send smooth cold email directly to the recruiter
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

                # Humanised pacing between recruiter sends
                if emails_sent_today % 5 == 0:
                    backoff = random.uniform(60, 120)
                    print(f"  ⏸ Backoff: sleeping {backoff:.0f}s between batches")
                    time.sleep(backoff)
                else:
                    time.sleep(random.uniform(15, 45))

        # Cooldown between roles
        if role_idx < len(roles) - 1 and emails_sent_today < personal_email_cap:
            cooldown = random.uniform(45, 90)
            print(f"  Cooldown between roles: {cooldown:.0f}s")
            time.sleep(cooldown)

    elapsed = time.time() - start
    _hr("📊 Outreach run summary")
    print(f"  Recruiter cold emails sent: {emails_sent_today} / cap {personal_email_cap}")
    print(f"  Self-notification emails:    0 (Disabled)")
    print(f"  Elapsed:                     {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    if _use_tracker:
        stats = _sent_tracker.stats()
        print(f"  Total sent in database:      {stats['total_sent']}")
        print(f"  Reply rate:                  {stats['reply_rate']*100:.1f}% ({stats['total_replied']}/{stats['total_sent']})")


if __name__ == "__main__":
    main()
