# `~/.jarvis/automations/` — Single Home for All Automations

> **Last consolidation:** 2026-06-14 (eliminated duplicate copies under `~/.openclaw/workspace/`)
> **Owner:** JARVIS (zero-leak LLM router)
> **Rule:** All automation code (hermes-driven and openclaw-driven) lives here, full stop.

---

## What's here

```
~/.jarvis/automations/
├── README.md                       ← you are here
├── hermes-scripts/                 ← utilities used by Hermes scheduler/cron
│   └── weekly_compare.py
├── job-automation/                 ← 10-portal job scraper + auto-applier
├── linkedin-outreach/              ← LinkedIn cold-mail composer + sender
├── pinned-outreach/                ← Pinterest pin generator + poster (Playwright)
├── openclaw-archive/               ← OpenClaw identity files (AGENTS/SOUL/TOOLS) — not active code
└── interview_scheduler_prep_bot/   ← interview prep from email listener (Gmail API)
```

All code uses `Path.home()`-relative paths (no hardcoded `/c/Users/Venu/...`). Paths that previously resolved to `~/.openclaw/workspace/...` now resolve to `~/.jarvis/automations/...`.

---

## The canonical layout for a NEW automation

Drop a folder here with this skeleton:

```
~/.jarvis/automations/<project-slug>/
├── run.py                 # single entrypoint; routes via from jarvis.policy import call_llm
├── cron.yaml              # optional — declared schedule (consumed by openclaw scheduler)
├── README.md              # what this automation does, how to invoke, env it needs
├── requirements.txt       # pip deps (frozen — pin versions)
├── .env.example           # template env vars (NEVER commit .env itself)
│
├── scripts/               # small support scripts (one file = one job)
│
├── output/                # runtime artifacts:
│   ├── logs/              #   daily JSONL / .log files
│   ├── resumes/           #   generated files (PDFs, DOCX, etc.)
│   └── *.db, *.sqlite     #   sqlite state DBs
│
├── .sessions/             # playwright browser session cookies (auto-created)
├── scratch/               # throwaway screenshots / debug dumps (auto-created)
│
└── tests/
    └── test_smoke.py
```

### Hard rules (any project under here MUST follow)

1. **All LLM calls go through `~/.jarvis/policy.call_llm()`.** No direct ollama / cloud API calls. The policy enforces:
   - `mode="build"` → cloud OK, no PII
   - `mode="run"` → local only (phi4-mini / qwen2.5-coder)
   - override with `force="local"` / `force="cloud"` + explicit approval flag, OR set `JARVIS_ALLOW_CLOUD=1`
2. **No hardcoded home paths.** Use `Path.home() / ".jarvis" / "automations" / "<project-slug>" / ...`.
3. **`.env` is gitignored.** Public repos (mirror the legacy `job-automation` workflow in `~/.openclaw/.git`-style history if needed). Real secrets stay in `~/.jarvis/.secrets/` (mode 600), referenced by symlink or env var.
4. **Lifecycle gate before live.** `draft → test → stage → 3× dry-run → live` (enforced by `~/.jarvis/lifecycle.py`).
5. **Cron targets the run.py at the canonical jarvis path.** `cron.yaml` should reference `~/.jarvis/automations/<project>/run.py` — NEVER `~/.openclaw/workspace/...`.

### Adding a NEW automation

Tell JARVIS (in chat, edit files directly, or any future channel — Telegram channel retired 2026-06-16). The build flow is:

1. **BUILD mode** — `call_llm(prompt=<task spec>, mode="build", model="<cloud-model-allowed-by-policy>")` scaffolds `run.py`, `cron.yaml`, `README.md`. No PII in prompt.
2. **TEST** — synthetic data only. Validate it imports without PII errors.
3. **STAGE** — copy your anonymised template / fixtures, run dry-run 3×. Each dry-write goes to `~/.jarvis/automations/<project>/output/test_*` and audit-logs `call_llm(..., dry=True)`.
4. **DEPLOY** — first live run uses `mode="run", force="local"` so the policy guarantees no cloud round-trip.
5. **PROMOTE** — flip the state machine in `policy.json` so future runs auto-route.

### When you need to update an existing automation

- Edit at `~/.jarvis/automations/<project>/...` directly.
- Any cloud-side LLM edits need `JARVIS_ALLOW_CLOUD=1` exported for that session, OR you pass `force="cloud"` explicitly with the audit reason logged.
- After changes, run the project tests: `cd <project> && python tests/test_smoke.py`.

---

## What you might be looking for (frequently)

| Looking for... | Path |
|---|---|
| Project home | `~/.jarvis/automations/<project>/` |
| Live cron schedules | `~/.jarvis/automations/<project>/cron.yaml` |
| JARVIS policy | `~/.jarvis/policy.py` + `policy.json` |
| PII / leak audit | `~/.jarvis/leak_check.py` |
| Lifecycle stage checker | `~/.jarvis/lifecycle.py` |
| Recent LLM calls (audit) | `~/.jarvis/audit.log` |
| OpenClaw scheduling DB | `~/.openclaw/cron/` |
| OpenClaw runtime DB | `~/.openclaw/flows/registry.sqlite`, `~/.openclaw/tasks/runs.sqlite` |
| Old duplicate backup (didn't keep code, only runtime state) | `~/.openclaw/.runtime-backup-2026-06-14/` |
| Career-page scrape cache (live) | `~/.jarvis/automations/job-automation/output/career_pages/` |

---

## Why one home, not two

Before 2026-06-14 every automation lived in TWO byte-identical copies — one under `~/.jarvis/automations/`, one under `~/.openclaw/workspace/`. Seven source files had hardcoded `~/.openclaw/workspace/...` paths that wouldn't follow a symlink cleanly, and the `output/career_pages/` runtime scrape data had diverged (51 jobs on openclaw, 6 on jarvis, with 0 overlap in some companies). Eliminated the duplicate; merged the data; rewrote all 7 hardcoded paths.

**Going forward: never put automation code outside this tree.** The policy guard in `~/.jarvis/policy.py` will log a warning if anything imports from `~/.openclaw/workspace/...`.
