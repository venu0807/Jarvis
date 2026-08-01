# 🦞 Jarvis — AI-Powered Automation Suite

Personal automation orchestrator for job applications, Pinterest affiliate marketing, LinkedIn outreach, and interview prep — running 100% locally with Playwright browser automation.

## Architecture

```
D:\Proposals\Jarvis\
├── .env.example              # Centralized credential template
├── jarvis_browser.py         # Shared Playwright context managers (AsyncBrowser + SyncBrowser)
├── policy.py                 # Zero-leak LLM policy engine (routes calls to local Ollama)
├── shared_utils.py           # Logging, retry decorators, atomic writes, IST helpers
├── lifecycle.py              # Process lifecycle management
├── daily_report.py           # Daily email report generator
│
├── automations/
│   ├── job-automation/       # 🎯 Auto-apply to Naukri, Indeed, Internshala, Workday, etc.
│   │   ├── auto_applier.py   #   Portal orchestrator
│   │   ├── run_pipeline.py   #   Master pipeline (apply → tailor → notify)
│   │   ├── resume_tailor.py  #   LaTeX-based resume tailoring per job
│   │   ├── portals/          #   9 portal implementations (Playwright form-fill)
│   │   └── .sessions/        #   Persisted login sessions (auto-generated)
│   │
│   ├── pinterest/            # 📌 Pinterest affiliate marketing bot
│   │   ├── main.py           #   Orchestrator (run, refill, stats, crosspost)
│   │   ├── poster.py         #   API v5 → Playwright browser fallback poster
│   │   ├── generator.py      #   Pin image generation (Pillow)
│   │   ├── products.py       #   Product database + affiliate link builder
│   │   └── data.csv          #   Pin queue (auto-generated)
│   │
│   ├── linkedin-outreach/    # 💼 LinkedIn cold-email outreach
│   │   ├── main.py           #   Orchestrator (scrape → extract → compose → send)
│   │   ├── scraper.py        #   Playwright LinkedIn post scraper
│   │   ├── composer.py       #   LLM-based email composer (local Ollama)
│   │   ├── extractor.py      #   Apollo.io email extraction
│   │   └── mailer.py         #   SMTP email sender
│   │
│   ├── interview-scheduler-  # 📅 Interview prep generator + Google Calendar
│   │   prep-bot/
│   │
│   └── hermes-scripts/       # 📊 Analytics & reporting scripts
│
├── tests/
│   └── test_jarvis_browser.py # 62 unit tests for shared browser utility
│
├── scripts/
│   ├── health_dashboard.py    # System health monitoring
│   ├── jarvis_audit.py        # Audit log viewer
│   └── leak_check.py          # Secret/PII leak scanner
│
├── backups/                   # Automatic workspace backups
└── wd_browser/                # Workday browser profiles (auto-generated)
```

## Quick Start

### 1. Prerequisites

- Python 3.9+
- [Playwright](https://playwright.dev/python/) (`pip install playwright && playwright install chromium`)
- [Ollama](https://ollama.com/) with a local model (e.g., `phi4-mini`)

### 2. Setup

```powershell
# Clone / enter the project
cd D:\Proposals\Jarvis

# Copy environment template
copy .env.example .env

# Edit .env with your credentials (see each automation's README)
# ---

# Install dependencies per automation
pip install -r automations\job-automation\requirements.txt
pip install -r automations\pinterest\requirements.txt
pip install -r automations\linkedin-outreach\requirements.txt
```

### 3. Run an Automation

```powershell
# Job automation pipeline
python automations\job-automation\run_pipeline.py

# Pinterest bot
python automations\pinterest\main.py

# LinkedIn outreach
python automations\linkedin-outreach\main.py
```

## Security

- **Zero-leak policy**: All LLM calls route through `policy.call_llm()`, which forces local Ollama inference unless `JARVIS_ALLOW_CLOUD=1` is explicitly set
- **No hardcoded credentials**: Every secret reads from `.env` via `os.getenv()`
- **Pre-commit hook**: Blocks commits containing secrets, API keys, or `.env` files
- **Session persistence**: Playwright `storage_state` keeps login sessions — no password replay

## Logging

All automations log to `output/logs/{name}_{date}.log` with structured `[HH:MM:SS] LEVEL message` format. Use `shared_utils.setup_logging()` in new scripts.

```python
from shared_utils import setup_logging
log = setup_logging("my_bot")
log.info("Pipeline started")
log.error("Something failed", exc_info=True)
```

## Testing

```powershell
# Run the shared browser utility tests
python -m pytest tests\test_jarvis_browser.py -v

# Run automation-specific tests
python -m pytest automations\job-automation\tests\
python -m pytest automations\linkedin-outreach\tests\
python -m pytest automations\pinterest\tests\
```

## License

Private — personal automation infrastructure.
