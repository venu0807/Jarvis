# LinkedIn Cold-Mail Outreach Bot

**Tiered cold-email composer + sender** with zero-leak LLM routing.

> **Updated 2026-08-21**: Now with 5 email templates (T1-T5), tier-based targeting (T1/T2/T3), reply tracking, follow-up scheduling, and Google Sheets export.

## Overview

Automates LinkedIn recruiter outreach with tiered intelligence:

- Scrapes LinkedIn posts for target roles
- Extracts recruiter emails from post content
- Generates personalized cold emails via local LLM (Ollama, routed through `policy.call_llm`)
- **5 email templates** (T1-T5) for different outreach types
- **Tier-based targeting** (T1 = founders, T2 = hiring managers, T3 = recruiters)
- Sends emails via Gmail SMTP with resume attachment (saved to Drafts, not auto-sent)
- Tracks sent emails in SQLite to avoid duplicates
- **Reply tracking** with reply rate metrics
- **Auto Day-5 follow-ups** via T5 template
- **CSV export** for Google Sheets
- Respects daily caps and per-role limits

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Basic usage
python run.py                          # Normal run (15 personal emails/day cap)
python run.py --test-email you@domain.com  # Test email pipeline
python run.py --dry-run                # Scrape only; no emails sent
python run.py --limit 5                # Override daily cap

# Tier-based targeting (NEW)
python run.py --tier T1                # Only T1 founders (Sarvam, Yellow.ai, Haptik, etc.)
python run.py --tier T2                # Only T2 hiring managers
python run.py --tier T1,T2             # T1 and T2 only (skip T3 recruiters)

# Template selection (NEW)
python run.py --template T1            # Founder/CEO cold DM
python run.py --template T2            # LinkedIn hiring manager DM [DEFAULT]
python run.py --template T3            # Reply to recruiter
python run.py --template T4            # Cold email to startup HR (formal)
python run.py --template T5            # Follow-up Day 5

# Custom role subset
python run.py --roles "Python Developer,AI Engineer"

# Export to Google Sheets (NEW)
python run.py --export                 # Writes outreach_export.csv

# Send due follow-ups (NEW)
python run.py --followups              # Sends any Day-5 follow-ups that are due
```

## Architecture

```
linkedin-outreach/
├── run.py                 # Canonical entrypoint (thin wrapper)
├── cron.yaml              # Schedule declaration
├── main.py                # Orchestrator with caps, pacing, dedup, tiers, templates
├── scraper.py             # LinkedIn post scraper (Playwright)
├── extractor.py           # Email extraction from post text
├── composer.py            # Cold email generation via JARVIS policy + templates
├── templates.py           # 5 email templates (T1-T5) [NEW]
├── targets_tiered.csv     # 50+ pre-classified targets (T1/T2/T3) [NEW]
├── portfolio.json         # 25 real projects for portfolio citations [UPDATED]
├── mailer.py              # Gmail SMTP/IMAP sender
├── db_tracker.py          # SQLite tracker with replies + followups [UPDATED]
├── jarvis_browser.py      # Shared browser utils (compat layer)
├── shared_utils.py        # Logging, retry, metrics (from automations/)
├── policy.py              # Zero-leak LLM routing (from jarvis root)
├── .env                   # Credentials (gitignored)
├── logs/                  # Daily logs
├── playwright_profile/    # Browser session data
└── README.md              # This file
```

## 5 Email Templates

| ID | Audience | Length | When to Use |
|---|---|---|---|
| **T1** | Founder/CEO | <300 words | First contact to T1 founders (Sarvam, Yellow.ai, Haptik, Verloop, Observe.AI founders) |
| **T2** | Hiring Manager | <300 words | Default — most LinkedIn DMs to engineering managers (Razorpay, Freshworks, Meesho, etc.) |
| **T3** | Recruiter Reply | <300 words | When replying to an inbound recruiter message |
| **T4** | Startup HR | <400 words | Cold email to HR/People Ops with resume attached (formal cover letter style) |
| **T5** | Follow-up | <200 words | Auto Day-5 follow-up reminder |

## Tier-Based Targeting

| Tier | Audience | Daily Cap | Template |
|---|---|---:|---|
| **T1** | Founders/CEOs (Sarvam, Yellow.ai, Haptik, Verloop, Observe.AI) | 2-3/day | T1 (founder DM) |
| **T2** | Hiring Managers / Engineering Leads (Razorpay, Freshworks, Meesho, etc.) | 8-10/day | T2 (HM DM) |
| **T3** | Recruiters / HR (Naukri, Indeed, Foundit, Internshala) | 5-7/day | T3 (recruiter reply) |

Total: 15 emails/day cap (configurable via `DAILY_PERSONAL_CAP`)

## Tracking Schema

```sql
-- Sent emails with tier + template
sent_emails:
  recipient, role, company, subject, sent_at,
  is_fallback, status, tier, template_id

-- Reply tracking (NEW)
replies:
  recipient, subject, snippet, received_at, sentiment

-- Follow-up scheduling (NEW)
followups:
  recipient, scheduled_for, template_id, sent_at, status
```

The existing `sent_emails` table is **auto-migrated** to add `tier` and `template_id` columns — no manual SQL needed.

## Configuration (.env)

```bash
# Email (Gmail SMTP/IMAP)
SMTP_USER=pvgreddy3@gmail.com
SMTP_APP_PASSWORD=your_app_password_here

# Resume
RESUME_PATH=/home/venu/V/VenuGopalReddy-Palugulla-FullStackAI-Resume.pdf

# Caps (defaults shown)
DAILY_PERSONAL_CAP=15
DAILY_FALLBACK_CAP=30
PER_ROLE_CAP=2

# Fallback (for posts with external apply links)
FALLBACK_EMAIL=pvgreddy3@gmail.com

# LLM chain (overrides default)
OLLAMA_FALLBACK_CHAIN=qwen2.5-coder:3b,llama3.2:3b

# Cloud opt-in (default: NOT set, strict-zero-leak)
# JARVIS_ALLOW_CLOUD=1
```

## Metrics Export → Google Sheets

```bash
python run.py --export
# → writes outreach_export.csv with sent_emails + replies joined
# → import this CSV into your Google Sheets "Outreach" tab
```

Output CSV columns:
```
recipient, role, company, tier, template_id,
subject, sent_at, is_fallback, status,
replied_at, sentiment
```

## Reply Tracking (Manual)

When a recruiter replies, record it:

```python
from db_tracker import SentTracker
tracker = SentTracker()
tracker.record_reply(
    "recruiter@example.com",
    subject="Re: Application",
    snippet="Thanks for reaching out...",
    sentiment="positive",  # positive | neutral | negative
)
```

## Follow-Up Scheduling

Every non-fallback `record_sent` auto-schedules a Day-5 follow-up via T5. To send all due follow-ups:

```bash
python run.py --followups
```

## Best Practices

1. **Always `--dry-run` first** before sending:
   ```bash
   python run.py --tier T1 --template T1 --dry-run
   ```

2. **Use `--test-email` to verify SMTP**:
   ```bash
   python run.py --test-email you@gmail.com
   ```

3. **Export to Google Sheets daily** to track ROI:
   ```bash
   python run.py --export
   ```

4. **Check stats regularly**:
   ```bash
   python -c "from db_tracker import SentTracker; import json; print(json.dumps(SentTracker().stats(), indent=2))"
   ```

## Why Tiered Targeting?

Sending the same generic email to a founder, hiring manager, and recruiter wastes outreach budget:

- **Founders** care about product signal ("I built JARVIS") — use T1
- **Hiring managers** care about technical fit — use T2
- **Recruiters** want a quick resume — use T3

Tiered targeting prioritizes **highest-conversion** outreach first.

## Cron Schedule

See `cron.yaml` for the default schedule (10 AM IST daily).

```yaml
schedule:
  cron: "0 10 * * *"
  timezone: "Asia/Kolkata"
  command: "python run.py --tier T1,T2 --template T1"
```

## Troubleshooting

### "Database is locked" / "no such column: tier"
- Run `python run.py --dry-run` once to trigger auto-migration
- Or manually: `python -c "from db_tracker import SentTracker; SentTracker()"`

### "SMTP auth failed"
- Check `SMTP_APP_PASSWORD` (Gmail requires app-specific password, not account password)
- Enable 2FA + create app password: https://myaccount.google.com/apppasswords

### "composer refused: PII detected"
- This is INTENTIONAL (zero-leak policy). Don't disable.
- All PII stays local; only local Ollama models process it.

## Related Files

- `../../policy.py` — zero-leak LLM routing
- `../../jarvis_browser.py` — browser context pool
- `../../JOB_HUNT_KIT/cold_outreach_templates.md` — manual outreach templates
- `../../JOB_HUNT_KIT/cold_dms_ready_to_send.md` — 5 ready-to-send LinkedIn DMs
- `../../JOB_HUNT_KIT/target_companies.md` — 50+ company target list
