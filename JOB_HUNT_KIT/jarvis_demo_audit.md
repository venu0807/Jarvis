# JARVIS Demo-Ready Audit

> **Goal**: Make JARVIS look production-grade in a 5-min Loom.
> **Don't refactor — just remove visible flaws.**
> **Time available**: 1-2 hours before recording.

This audit was done against `/home/venu/Proposals/Jarvis/` (actual files). Below are the issues I found, prioritized.

---

## 🔴 SECTION 1: MUST FIX (do these in next 1–2 hours)

### Issue 1.1: NO ROOT README — recruiters land on a blank project

**Problem**: `/home/venu/Proposals/Jarvis/README.md` does NOT exist. Recruiters who land on the GitHub repo see... nothing.

**Severity**: 🔴 CRITICAL. This is the single highest-impact fix.

**Fix**: 
- Copy `/home/venu/Proposals/Jarvis/JOB_HUNT_KIT/README.md` → `/home/venu/Proposals/Jarvis/README.md`
- Run:
```bash
cd /home/venu/Proposals/Jarvis
cp JOB_HUNT_KIT/README.md README.md
git add README.md
git commit -m "Add project README"
git push
```

**Time**: 2 min

---

### Issue 1.2: `.env` files are committed with credentials

**Problem**: Multiple `.env` files in `/home/venu/Proposals/Jarvis/automations/*/` contain real portal credentials (Naukri, Internshala, Indeed, Foundit passwords).

**Severity**: 🔴 CRITICAL. This is a security red flag that ANY reviewer will catch. Plus, your credentials are now in git history.

**Fix** (do this IMMEDIATELY):
```bash
cd /home/venu/Proposals/Jarvis

# 1. Remove .env files from git tracking
git rm --cached automations/job-automation/.env
git rm --cached automations/pinterest/.env
git rm --cached automations/linkedin-outreach/.env 2>/dev/null
git rm --cached automations/interview_scheduler_prep_bot/.env 2>/dev/null
# (any others with secrets)

# 2. Verify .gitignore covers .env files
grep -q "^\.env$" .gitignore && echo "✓ .env is gitignored" || echo "^\.env$" >> .gitignore

# 3. Create .env.example files in each automation folder (replace real values with placeholders)
cd automations/job-automation
cp .env .env.example
sed -i 's/=.*/=/' .env.example  # zero out values, keep keys
sed -i 's/$/REPLACE_ME/' .env.example
# Repeat for other automations

# 4. Commit the fixes
git add -A
git commit -m "Remove .env files from tracking, add .env.example"
git push

# 5. ROTATE YOUR PASSWORDS NOW (they're in git history)
# - Naukri: log in → change password
# - Internshala: same
# - Indeed, Foundit: same
# Then update your local .env files with new passwords
```

**Time**: 10 min (including password rotation)

---

### Issue 1.3: Hardcoded password values in `.env` files

**Problem**: The grep `password = "..."` style hardcoded values still exist in env files.

**Severity**: 🔴 Even after git rm, the values are still in your FILESYSTEM. Recruiters who clone and run `cat .env` will see them.

**Fix**:
```bash
# After rotating passwords (see 1.2), the new .env files will have new passwords
# But also: rotate ALL secrets via your secrets_manager.py
cd /home/venu/Proposals/Jarvis
python automations/secrets_rotation.py  # if it exists
```

If `secrets_rotation.py` doesn't fully automate this, manually:
```bash
# Edit each .env file and replace the password values with NEW passwords
nano automations/job-automation/.env
```

**Time**: 5 min

---

### Issue 1.4: Dashboard URL not in README

**Problem**: The JARVIS dashboard (Next.js) is mentioned in your cover letter and demos, but the README doesn't tell recruiters how to see it (screenshot or running URL).

**Severity**: 🟡 HIGH. Without a visual, "25 workflows" is just a claim.

**Fix**:
1. **Take a screenshot of the dashboard** while it's running:
```bash
# Start the dashboard
cd /home/venu/Proposals/Jarvis
docker compose up -d
# Open http://localhost:3000 in browser, take a screenshot

# Save screenshot
mkdir -p docs/screenshots
# Move screenshot to docs/screenshots/dashboard.png
```

2. **Add it to README** (in `JOB_HUNT_KIT/README.md`):
```markdown
## 📸 Dashboard

![JARVIS Dashboard](docs/screenshots/dashboard.png)
*Real-time view of scraper activity, applications sent, and alert pipeline.*
```

3. **Commit and push**.

**Time**: 10 min

---

### Issue 1.5: docker-compose.yml only has postgres — no other services

**Problem**: The `docker-compose.yml` only defines `postgres`. Your README claims "25 automations", "Grafana", "Prometheus", etc., but none of those services are in compose.

**Severity**: 🟡 HIGH. Recruiters who clone the repo will run `docker compose up` and only get a database.

**Fix**: Either:
- (A) Add the missing services to compose (Grafana, Prometheus, the automations themselves)
- (B) Update the README to be honest about what's dockerized

**Recommended fix (A)** — extend `docker-compose.yml`:
```yaml
version: '3.8'

services:
  postgres:
    # ... existing config ...

  prometheus:
    image: prom/prometheus:latest
    container_name: jarvis-prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/rules:/etc/prometheus/rules
    ports:
      - "9090:9090"
    networks:
      - jarvis-network

  grafana:
    image: grafana/grafana:latest
    container_name: jarvis-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASS:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    networks:
      - jarvis-network

  job-automation:
    build: ./automations/job-automation
    container_name: jarvis-job-auto
    env_file: ./automations/job-automation/.env
    depends_on:
      - postgres
    networks:
      - jarvis-network

# ... add pinterest, linkedin-outreach, etc. similarly

volumes:
  postgres_data:
  grafana_data:

networks:
  jarvis-network:
    driver: bridge
```

**Time**: 20 min

---

## 🟡 SECTION 2: SHOULD FIX (do these if there's time)

### Issue 2.1: Multiple `fix_*.py` files at root level

**Problem**: `/home/venu/Proposals/Jarvis/` has `fix_alert_triggers.py`, `fix_nl.py`, `fix_ollama_func.py`, `fix_fstrings.py`, `write_b64.py`, `test_fstring.py`, etc. These look like one-off scripts left behind.

**Severity**: 🟡 Looks unprofessional in a recruiter's first scan.

**Fix**: Move them to `scripts/maintenance/`:
```bash
cd /home/venu/Proposals/Jarvis
mkdir -p scripts/maintenance
mv fix_*.py scripts/maintenance/
mv write_b64.py scripts/maintenance/
mv test_*.py tests/  # if they're real tests
rm test_write.txt  # looks like a debug artifact
```

**Time**: 5 min

---

### Issue 2.2: `__pycache__` folders committed

**Problem**: `/home/venu/Proposals/Jarvis/__pycache__/` exists in git. Should be gitignored.

**Fix**:
```bash
cd /home/venu/Proposals/Jarvis
# Add to .gitignore (if not already)
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Remove from tracking
git rm -r --cached automations/__pycache__ 2>/dev/null
git rm -r --cached automations/job-automation/__pycache__ 2>/dev/null
git rm -r --cached automations/pinterest/__pycache__ 2>/dev/null
# etc.
git commit -m "Remove __pycache__ from tracking"
```

**Time**: 5 min

---

### Issue 2.3: Multiple "report" markdown files at root

**Problem**: `ALERT_STATUS_REPORT.md`, `ALERT_TRIGGER_REPORT.md`, `HEALTH_CHECK_REPORT.md`, `CEO_SETUP_PLAN.md`, `CEO_SETUP_PLAN_UPDATED.md` — these are operational notes, not project docs.

**Fix**: Move to `docs/operations/`:
```bash
cd /home/venu/Proposals/Jarvis
mkdir -p docs/operations
mv *_REPORT*.md docs/operations/
mv CEO_SETUP_PLAN*.md docs/operations/
```

**Time**: 2 min

---

### Issue 2.4: No CONTRIBUTING.md

**Problem**: Standard for open-source projects.

**Fix**: Create `/home/venu/Proposals/Jarvis/CONTRIBUTING.md`:
```markdown
# Contributing to JARVIS

## Reporting Issues
Open an issue at https://github.com/venu0807/Jarvis/issues with:
- What you tried
- What happened
- What you expected

## Pull Requests
1. Fork the repo
2. Create a branch (`git checkout -b feature/your-feature`)
3. Make changes + add tests
4. Run `python -m pytest tests/`
5. Push + open a PR

## Local Development
```bash
git clone https://github.com/venu0807/Jarvis.git
cd Jarvis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-base.txt
docker compose up -d
```
```

**Time**: 5 min

---

### Issue 2.5: Badges missing from README

**Problem**: The README I wrote includes placeholder badges, but they need to be real.

**Fix**: Edit the README to add real badges. Use https://shields.io:

```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](https://www.docker.com/)
[![Ollama](https://img.shields.io/badge/llm-ollama-black.svg)](https://ollama.com/)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)
```

**Time**: 2 min

---

### Issue 2.6: No `.github/ISSUE_TEMPLATE` or `PULL_REQUEST_TEMPLATE`

**Problem**: Looks like a project that's never had outside contributors.

**Fix**:
```bash
cd /home/venu/Proposals/Jarvis
mkdir -p .github/ISSUE_TEMPLATE .github/PULL_REQUEST_TEMPLATE
```

Create `.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug Report
about: Something is broken
title: '[BUG] '
labels: bug
---

## What happened
## Steps to reproduce
1. 
2. 
3. 
## Expected behavior
## Logs
```
[paste logs here]
```
```

**Time**: 5 min

---

## 🟢 SECTION 3: NICE TO HAVE (skip if no time)

- **Add GitHub Actions CI badge**: Already have `.github/workflows/ci.yml` (good!), just need a badge in README showing pass/fail status.
- **Add a sample `screenshots/` directory** with: dashboard.png, grafana.png, terminal.png
- **Add a CHANGELOG.md** documenting recent work
- **Add unit tests** in `tests/` for `secrets_manager.py`, `alert_manager.py`, `browser_pool.py`
- **Add type hints** to functions that lack them (mostly in `automations/shared_utils.py`)
- **Add a `.editorconfig`** for consistent formatting
- **Add a `Makefile`** with targets: `make up`, `make down`, `make test`, `make logs`

---

## 🔥 Recording Day — Final Pre-Recording Checklist (T-30 min)

Before you hit record, verify ALL of these are green:

- [ ] Root README exists and renders correctly on GitHub
- [ ] No `.env` files in git history (search: `git log --all --full-history -- automations/job-automation/.env` should return nothing)
- [ ] `.env.example` files exist in each automation folder with placeholder values
- [ ] Passwords ROTATED (Naukri, Internshala, Indeed, Foundit)
- [ ] Dashboard runs and shows real data (not "0" everywhere)
- [ ] Grafana runs and shows metrics
- [ ] All `fix_*.py`, `test_*.py` moved out of root
- [ ] `__pycache__` removed from tracking
- [ ] Root directory has ONLY: README.md, Dockerfile.base, docker-compose.yml, requirements-base.txt, automations/, docs/, scripts/, .github/, .gitignore

---

## 🎯 Priority Stack (do in this order)

```
1. Rotate passwords (5 min) → do this FIRST
2. Remove .env from git, add .env.example (5 min)
3. Copy JOB_HUNT_KIT/README.md → root README.md (2 min)
4. Take dashboard screenshot, add to README (10 min)
5. Move fix_*.py files to scripts/maintenance/ (5 min)
6. Remove __pycache__ from tracking (5 min)
7. Move reports to docs/operations/ (2 min)
8. Extend docker-compose.yml with Grafana + Prometheus (20 min)
9. Add CONTRIBUTING.md, badges, issue templates (10 min)
10. Final pre-flight check from loom_demo_runbook.md (15 min)

Total: ~80 min if you do everything
Minimum viable: steps 1-3 + 10 (~25 min)
```

---

## After Recording — Polish Round (next day)

Once your Loom is published:
- [ ] Add the Loom URL to README header
- [ ] Add Loom URL to all 4 resume variants (replace `jarvis-demo.loom` placeholder)
- [ ] Add Loom URL to LinkedIn Featured section
- [ ] Add Loom URL to GitHub profile README
- [ ] Add Loom thumbnail as `docs/screenshots/thumbnail.png`

Then start applying. 🚀
