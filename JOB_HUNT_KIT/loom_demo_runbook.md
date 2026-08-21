# JARVIS Demo Runbook — Pre-Flight + Run-of-Show + Backups

> **Print this. Have it on your desk during recording.**
> Goal: a flawless 5-min Loom that gets callbacks.

---

## PART A: Pre-Flight Checklist (do 30–60 min before recording)

Tick each box. Don't start recording until ALL are green.

### Environment

- [ ] **WSL Ubuntu running** — open Ubuntu terminal, type `uname -a` → should show Linux
- [ ] **Ollama running** — `curl -s http://localhost:11434/api/tags | head -50` → should list 3+ models
- [ ] **Models pre-loaded** — `ollama list` → must show `qwen2.5-coder:3b`, `llama3.2:3b`, `nomic-embed-text`
- [ ] **Pre-warm** — `ollama run qwen2.5-coder:3b "hi" --verbose=false && ollama run llama3.2:3b "hi" --verbose=false && ollama run nomic-embed-text "hi" --verbose=false` → all respond in <2s
- [ ] **Docker stack up** — `docker compose ps` → all services show `healthy` or `running`
- [ ] **No disk pressure** — `df -h /` → less than 85% used

### Dashboard & Monitoring

- [ ] **JARVIS dashboard** — open http://localhost:3000 in browser → shows real metrics (not "0" on everything)
- [ ] **Grafana** — open http://localhost:3001 → log in → dashboards show data
- [ ] **Prometheus** — http://localhost:9090 → Status → Targets → all targets `UP`
- [ ] **Sample data populated** — check DB: `docker exec -it jarvis-postgres psql -U jarvis -c "SELECT COUNT(*) FROM applications"` → ≥ 50 rows

### Communication

- [ ] **ntfy.sh topic configured** — check `/home/venu/Proposals/Jarvis/.env` for `NTFY_TOPIC=...`
- [ ] **Phone app logged in** — open ntfy.sh app, subscribed to your topic
- [ ] **Test notification** — `curl -d "Demo test" ntfy.sh/YOUR_TOPIC` → push arrives on phone within 5s

### Visual Setup

- [ ] **Terminal font** — 18pt minimum, dark theme, no banners or MOTD
- [ ] **Tab title** — set to "JARVIS Demo — Venu Gopal Reddy" (shows in screen recordings)
- [ ] **Browser clean** — close ALL tabs except the JARVIS-related ones you'll demo; hide bookmarks bar (Ctrl+Shift+B)
- [ ] **Notifications silenced** — Slack, Discord, email, OS notifications ALL off (Focus Assist = Alarms Only)
- [ ] **Recording software** — Loom or OBS; record 10s test, verify audio + screen capture both work
- [ ] **Phone charged** — for the ntfy.sh demo moment
- [ ] **Lighting + mic** — face window for natural light; mic level green in Loom

### Backup Materials (have these ready)

- [ ] **2–3 dashboard screenshots** in `~/Proposals/Jarvis/screenshots/` showing real metrics
- [ ] **Sample cover letter** generated earlier — open in editor, ready to show
- [ ] **JSON dump of last 50 applications** — `docker exec jarvis-postgres pg_dump -t applications --data-only` saved to file
- [ ] **Old ntfy notification screenshot** — pull from phone, save to desktop

### What Success Looks Like

Every pre-flight item shows:
- ✅ **GREEN** (works as expected)
- ⚠️ **YELLOW** (works but cosmetic issue — fix if time)
- 🔴 **RED** (broken — DO NOT record, fix first)

**Rule: any RED → don't record. Reschedule.**

---

## PART B: 5-Minute Demo Run-of-Show

Match this exactly. Each segment has: TIMESTAMP / ACTION / SAY / SEE.

---

### 🎬 [0:00–0:30] COLD OPEN — The Hook

**Action**: Camera on you, dark room, screen share starts at 0:05
**Say**:
> "Job hunting for a fresher in India is broken. You either spend 5 hours a day on it, or you pay $200 a month for cloud AI tools that ship your resume to someone else's API. I built JARVIS instead — a local-first AI automation platform that runs on a laptop, costs $0 in cloud AI fees, and applied to 200+ jobs in its first month. Five minutes — I'll show you exactly how it works."

**See**: Your face (2 sec) → screen share (28 sec)
**Risk**: Going long on hook → **Mitigation**: hard cut at 0:30, jump to problem

---

### 🎬 [0:30–1:30] THE PROBLEM — Why This Matters

**Action**: Switch to browser showing dashboard at http://localhost:3000
**Say**:
> "Here's what I'm solving for. Job search has three problems — manual work, expensive tools, and your private data leaving your machine. Cloud AI costs $200 a month. Manual work takes 5 hours a day. And every time you paste your resume into ChatGPT, it goes to OpenAI's servers. I wanted all three fixed."

**See**: Dashboard home page, cursor pointing at "Applications sent" counter
**Risk**: Counter shows 0 → **Mitigation**: have backup screenshot in `screenshots/dashboard_200_apps.png`

---

### 🎬 [1:30–3:00] LIVE DEMO — Show JARVIS Working

**Action 1**: Open terminal, run the auto-applier
```bash
cd ~/Proposals/Jarvis/automations/job-automation
python run.py --headless=false --query "Full Stack AI Engineer" --limit 5
```
**Say**:
> "Watch this — I'm running the job auto-applier against Naukri, Internshala, Indeed, and Foundit. It scrapes, filters by my skills, and applies with an AI-tailored cover letter. The cover letter generation runs on local Ollama — qwen2.5-coder for selectors, llama3.2 for writing, nomic-embed for embeddings. Zero cloud API calls."

**See**: Terminal streaming log output, jobs appearing in the Applications tab

**Risk #1**: Ollama hangs → **Mitigation**: model already pre-warmed (3–5s response), or use pre-generated cover letter from `/tmp/demo_cover_letter.txt`
**Risk #2**: Portal blocks → **Mitigation**: have JSON dump of past 50 applications ready: `cat ~/jarvis_demo_backup/applications.json | jq '. | length'`

---

**Action 2** (at 2:15): Switch to Grafana at http://localhost:3001
**Say**:
> "Here's the observability stack — Prometheus scraping every automation's `/metrics` endpoint, Grafana visualizing it. Four dashboards: scrapes per hour, applications sent, model latency P95, and error budget. Right now we're at 99.2% uptime with sub-800 millisecond P95 inference."

**See**: Grafana dashboard with real-time counters updating
**Risk**: Grafana has no data → **Mitigation**: switch to http://localhost:9090 (raw Prometheus) and run query `rate(http_requests_total[5m])`

---

**Action 3** (at 2:40): Trigger an alert, show phone notification
```bash
curl -d "JARVIS demo alert: high error rate detected in job scraper" \
  ntfy.sh/YOUR_TOPIC
```
**Say**:
> "This is my error budget — when something breaks, AlertManager fires to ntfy.sh. I get a push notification on my phone in under five seconds. That's how I sleep at night."

**See**: Phone screen showing the notification arriving
**Risk**: Phone doesn't ping → **Mitigation**: have screenshot of an old notification: `ls ~/screenshots/ntfy_*.png`

---

### 🎬 [3:00–4:00] ARCHITECTURE — Why It Works

**Action**: Open the architecture diagram in README (or use draw.io)
**Say**:
> "Here's how it fits together. Inputs on the left — four job portals, LinkedIn, Pinterest. JARVIS core in the middle — orchestrator routes to a browser context pool with a 2-worker semaphore, fetches AI responses from Ollama, persists to PostgreSQL, exports metrics to Prometheus. Outputs on the right — applications, posts, dashboard, alerts. The big design decision: I'm constrained to 8 GB of RAM total. So I lazy-load models, pre-warm before scheduled runs, and use OLLAMA_KEEP_ALIVE=0 to auto-unload after each job. Embeddings model stays loaded because it's small and I use it everywhere."

**See**: Clean architecture diagram, cursor walking through each box
**Risk**: Diagram not clear → **Mitigation**: fall back to ASCII art in terminal:
```
[Naukri]──┐
[LinkedIn]──┤
[Pinterest]─┤──[Orchestrator]──[Browser Pool]──[Ollama]
[n8n]────┘         │              │             │
                   ▼              ▼             ▼
              [PostgreSQL]──[Prometheus]──[Grafana]
                                  │
                                  ▼
                          [AlertManager]
                                  │
                                  ▼
                          [ntfy.sh / Email]
```

---

### 🎬 [4:00–4:30] OTHER PROJECTS — Show Range

**Action**: Open GitHub in browser, show repo list
**Say**:
> "JARVIS is one of three projects I've shipped. SafeguardAI is on-device audio threat detection — CNN classifier, 89% accuracy, sub-100ms inference on Android. Movie Recommendation is a Django + React ML platform with normalized schema and JWT auth. The through-line: production-grade engineering, not tutorials."

**See**: github.com/venu0807 with 3 repos visible
**Risk**: GitHub is down → **Mitigation**: have screenshots of repo pages ready
**Risk**: Repos are empty → **Mitigation**: skip this segment, jump to closing

---

### 🎬 [4:30–5:00] CLOSE — The Ask

**Action**: Camera on you, full screen share still up
**Say**:
> "If you're hiring a Full Stack AI Engineer who ships production systems, not tutorials — I'd love to talk. JARVIS is open source at github.com/venu0807/Jarvis. My email is pvgreddy3@gmail.com. Thanks for watching."

**See**: Your face, calm energy, slight smile
**Risk**: Going over 5 min → **Mitigation**: hard cut at 4:50, jump straight to "Thanks for watching"

---

## PART C: Demo Day Backup Plans

For each high-risk moment, here's the fallback:

| If This Breaks | Have This Ready |
|---|---|
| **JARVIS dashboard down** (http://localhost:3000) | Screenshot of dashboard from `~/Proposals/Jarvis/screenshots/dashboard_real.png` |
| **Grafana has no data** | Switch to Prometheus raw at http://localhost:9090, query `rate(http_requests_total[5m])` |
| **Ollama slow to respond** | Pre-generated cover letter at `/tmp/demo_cover_letter.txt` — open in `code .` and walk through it |
| **ntfy.sh doesn't ping phone** | Screenshot of an old notification on desktop, OR send a Slack message to yourself and show the desktop notification |
| **Job scraper fails** | JSON dump of past 50 apps at `~/jarvis_demo_backup/applications.json` — `jq '. | length'`, then `jq '.[0]'` to show one record |
| **Docker stack is down** | Screenshots of `docker compose ps` output AND Grafana from a previous run |
| **Internet drops** | All demos are local-first, but GitHub at [4:00] needs internet. Have screenshots of repos ready. |
| **You stumble on a word** | Pause silently for 1 sec, then continue. Better than "um" or "uh". |
| **Time running over** | Hard cuts at 3:00 (skip segment 4 — repos), 4:00 (skip segment 5 — close), 4:50 (jump to "Thanks") |
| **Audio cuts out** | Re-record that segment. Loom makes this trivial. |

### Pre-stage All Backups BEFORE Recording

```bash
# Create backup folder
mkdir -p ~/jarvis_demo_backup
cd ~/jarvis_demo_backup

# Take dashboard screenshot (Chrome dev tools screenshot)
# Save as: dashboard_real.png

# Export applications table to JSON
docker exec jarvis-postgres psql -U jarvis -c "SELECT * FROM applications LIMIT 50" \
  --csv > applications.csv

# Generate sample cover letter ahead of time
ollama run llama3.2:3b "Write a 200-word cover letter for a Full Stack AI Engineer at Sarvam AI" \
  > demo_cover_letter.txt

# Pre-render the architecture diagram
# Save the Mermaid output as architecture.png

# Verify everything
ls -la ~/jarvis_demo_backup/
```

---

## PART D: Common Mistakes to Avoid

### 1. **Speaking too fast**
You naturally speed up when nervous. **Mitigation**: count "one Mississippi" between key sentences. Aim for 150 words/min.

### 2. **Saying "um" / "uh" / "like"**
Every "um" is a signal of nervousness. **Mitigation**: silent pause instead. Train yourself: when you'd say "um", just stop talking for 1 sec. It feels long to you, fine to viewers.

### 3. **Showing terminal with typos**
Recruiters notice typos. **Mitigation**: dry run the demo 3 times first. Or `clear` and re-type live.

### 4. **Saying "I don't know"**
This kills credibility. **Mitigation**: have a fallback line: "That's an interesting design decision — I'd dig into it in production, but here's how I'd approach it..." Then offer a reasoned guess.

### 5. **Going over 5 minutes**
Viewers drop off after 5 min. **Mitigation**: time yourself with a stopwatch. Hard cut at 4:50 to closing.

### 6. **Apologizing for things**
"I'm not sure this works perfectly..." "Sorry about the font..." **Mitigation**: never apologize. State facts. If something breaks, say "let me show you the backup" — calm, professional.

### 7. **Looking at the screen, not the camera**
Breaks connection with viewer. **Mitigation**: look at webcam when making eye contact points; look at screen when showing code.

### 8. **Showing empty / placeholder UIs**
A "Coming soon" or "TODO" in a demo = instant rejection. **Mitigation**: pre-flight check catches this. If you see it during recording, switch to a backup screenshot.

### 9. **Mumbling on technical terms**
"qwen2.5-coder" → "Q-WEN 2 point 5 CODER". **Mitigation**: practice saying technical terms out loud 5 times before recording.

### 10. **Forgetting the CTA (call to action)**
You MUST end with: "Here's my email, here's my GitHub, I'd love to talk." **Mitigation**: write the CTA on a sticky note on your monitor. Look at it before recording.

---

## PART E: Post-Recording Checklist

After you finish recording:

- [ ] **Watch the whole video back** before publishing — catch any issues
- [ ] **Add auto-captions** (Loom does this automatically; review for accuracy)
- [ ] **Add chapter markers** at each timestamp boundary (0:30, 1:30, 3:00, 4:00, 4:30)
- [ ] **Set thumbnail**: dashboard screenshot with "JARVIS in 5 min" text overlay
- [ ] **Save the Loom URL** — you'll use it in:
  - LinkedIn Featured section
  - GitHub profile README
  - JARVIS README
  - All cover letters (replace `loom.com/share/jarvis-demo` placeholder)
  - Email signature

- [ ] **Push to repos**: copy `~/Proposals/Jarvis/JOB_HUNT_KIT/README.md` → `~/Proposals/Jarvis/README.md` → commit → push

---

## Quick Reference: Commands You'll Run During Recording

```bash
# Pre-warm models (one-time, before recording)
ollama run qwen2.5-coder:3b "hi" --verbose=false
ollama run llama3.2:3b "hi" --verbose=false
ollama run nomic-embed-text "hi" --verbose=false

# Run the job auto-applier (live demo)
cd ~/Proposals/Jarvis/automations/job-architecture
python run.py --headless=false --query "Full Stack AI Engineer" --limit 5

# Trigger an alert (demo the ntfy.sh pipeline)
curl -d "JARVIS demo alert: high error rate detected" ntfy.sh/YOUR_TOPIC

# Verify dashboard is up
curl -s http://localhost:3000/healthz | jq .

# Verify Prometheus is up
curl -s http://localhost:9090/-/healthy | jq .

# Tail the auto-applier log
tail -f ~/Proposals/Jarvis/logs/job-automation.log
```

---

## Quick Reference: URLs You'll Open During Recording

| Service | URL | What to Show |
|---|---|---|
| JARVIS Dashboard | http://localhost:3000 | Application count, success rate |
| Grafana | http://localhost:3001 | 4 dashboards with real-time metrics |
| Prometheus | http://localhost:9090 | Raw query interface (backup) |
| ntfy.sh topic | https://ntfy.sh/YOUR_TOPIC | Recent alert history |
| GitHub | github.com/venu0807 | JARVIS, SafeguardAI, Movie Recommendation |

---

## Recording Day Schedule (suggested)

| Time | Activity |
|---|---|
| **T-60min** | Run full pre-flight checklist. Fix any RED items. |
| **T-30min** | Pre-warm models, populate demo data, take backup screenshots |
| **T-15min** | Final visual check: font, theme, tab title, bookmarks hidden |
| **T-5min** | Phone out, Loom/OBS ready, mic test, take 3 deep breaths |
| **T-0** | Hit record. Pause for 2 sec before speaking (clean audio). |
| **T+5min** | Stop recording. Watch the playback. |
| **T+15min** | Add captions, chapters, thumbnail. Publish. |
| **T+30min** | Update LinkedIn, GitHub, all resumes with Loom URL |

---

## Final Tip

The first take will be rough. **Record 3 takes minimum.** Use take 1 as practice, take 2 as the real one, take 3 as backup. Each take is ~7 min total (5 min demo + 2 min setup/cleanup). Total recording time: ~30 min for 3 takes.

When you watch take 1, you'll see 5 things you want to fix. Do them. Take 2 will be 80% better.

**Don't aim for perfect. Aim for: confident, specific, honest, 5 minutes.**

Good luck. Land the job. 🎯
