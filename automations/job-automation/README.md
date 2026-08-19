# Job Automation Pipeline

**10-portal job scraper + auto-applier** for Indian job market.

## Overview

Automates job applications across major Indian job portals:
- **Naukri** — India's largest job portal
- **Internshala** — Internships & fresher jobs
- **Indeed** — Global job aggregator
- **Foundit** (formerly Monster) — Enterprise job board

Uses **Playwright** for browser automation with persistent sessions (cookies stored locally, no re-login needed daily).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure credentials
cp .env.example .env
# Edit .env with your portal credentials

# Run once manually
python run.py

# Or run with options
python run.py --headful          # Visible browser for debugging
python run.py --portal naukri    # Single portal only
python run.py --limit 10         # Override daily apply limit
```

## Architecture

```
job-automation/
├── run.py                 # Canonical entrypoint
├── cron.yaml              # Schedule declaration
├── auto_applier.py        # Main orchestrator
├── run_pipeline.py        # Full pipeline with cleanup + notifications
├── portals/               # Portal implementations
│   ├── base.py           # BasePortal abstract class
│   ├── naukri.py         # Naukri Quick Apply
│   ├── internshala.py    # Internshala Easy Apply
│   ├── indeed.py         # Indeed Quick Apply
│   └── foundit.py        # Foundit Quick Apply
├── db_logger.py          # SQLite logging for interview prep
├── notifier.py           # Email summary sender
├── jarvis_browser.py     # Shared browser utils (compat layer)
├── shared_utils.py       # Logging, retry, metrics, path helpers
├── policy.py             # Zero-leak LLM routing (imported from jarvis root)
├── .env                  # Credentials (gitignored)
├── .sessions/            # Playwright storage_state (auto-created)
├── output/
│   ├── logs/             # Daily JSONL logs
│   └── jobs.db           # SQLite for interview prep bot
├── tests/
│   └── test_smoke.py     # Basic import/smoke tests
└── scripts/              # One-off utilities
```

## Configuration

### `.env` (required)

```bash
# Portal credentials
NAUKRI_EMAIL=your@email.com
NAUKRI_PASSWORD=yourpassword
INTERNSHALA_EMAIL=your@email.com
INTERNSHALA_PASSWORD=yourpassword
INDEED_EMAIL=your@email.com
INDEED_PASSWORD=yourpassword
FOUNDIT_EMAIL=your@email.com
FOUNDIT_PASSWORD=yourpassword

# Email notifications
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASS=your-app-password

# LLM (optional - for resume tailoring)
JARVIS_ALLOW_CLOUD=0  # Set to 1 to allow cloud models for build tasks

# Behavior
DAILY_LIMIT=20        # Max applies per portal per day
HEADLESS=true         # Set false for visible browser
```

### `cron.yaml` (for JARVIS scheduler)

```yaml
schedule: "0 9 * * *"  # Daily at 9:00 AM IST
timezone: "Asia/Kolkata"
```

## Scheduling

The pipeline runs **daily at 9:00 AM IST** via `jarvis_scheduler.sh` (cron every 15 min with catch-up logic for sleep/wake).

Manual trigger:
```bash
cd /home/venu/Proposals/Jarvis/automations/job-automation
python run.py
```

## Output

- **Applied jobs**: Saved to `output/logs/applications_YYYY-MM-DD.json`
- **Manual jobs**: Listed in email with direct links (no PDF generation)
- **Email summary**: Sent via Gmail SMTP after each run
- **Database**: `output/jobs.db` for Interview Prep Bot

## LLM Usage

All LLM calls route through `~/.jarvis/policy.call_llm()`:
- **Mode**: `run` (local only, PII present)
- **Model**: `phi4-mini:latest` (default local)
- **No cloud calls** unless `JARVIS_ALLOW_CLOUD=1` explicitly set

## Testing

```bash
# Smoke test
python -m pytest tests/test_smoke.py -v

# Test specific portal
python -c "from portals.naukri import NaukriPortal; print('OK')"
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Session rejected" | Delete `.sessions/{portal}.json` and re-run headful once |
| "Login failed" | Check credentials in `.env`; ensure 2FA not blocking |
| "No jobs found" | Verify role/city lists in `auto_applier.py` match portal |
| Playwright errors | Run `playwright install chromium --with-deps` |

## Security

- `.env` is gitignored; real secrets never committed
- All LLM calls audit-logged to `~/.jarvis/audit.log`
- Sessions stored locally with 600 permissions
- Browser runs with `--disable-blink-features=AutomationControlled`

## Extending

To add a new portal:
1. Create `portals/newportal.py` extending `BasePortal`
2. Implement `login()`, `search_and_apply()`, `apply_to_job()`
3. Add to `portal_map` in `auto_applier.py`
4. Add credentials to `.env.example`
5. Add tests in `tests/`