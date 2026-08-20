# JARVIS 5-Minute Loom Demo Script

> **Goal**: Recruiter watches this, gets it in 60 seconds, schedules interview in 5 min.
> **Pace**: 150 words/min narration. Confident, conversational, slightly informal.
> **Total**: ~750 words across 5 segments.

---

## [0:00 – 0:30] COLD OPEN — The Hook

**[NARRATION]** *(matter-of-fact, slightly tired tone — like you're venting to a friend)*
> "Job hunting is broken. A hundred portals. A hundred cover letters. Five hours a day, every day, for weeks. Two percent response rate. And every AI tool that promises to help wants $200 a month. I got tired of it — so I built something that fixes it."

**[SCREEN ACTION]**
- Frame 1: Split screen — left, calendar showing "5 hrs/day, 6 weeks" blocked out. Right, phone notification spam from job portals
- Frame 2 (cut): Bash terminal, command line: `python auto_applier.py --target=naukri --skills=python,react,ml`
- Frame 3 (cut): Dashboard refreshes, "47 applications sent today" counter ticks up

**[NOTES]**
- Don't say your name. Don't say "Hi, welcome to my demo."
- Background music: lo-fi, low volume
- Title card at bottom-right (subtle): "JARVIS — Local-First AI Automation"

---

## [0:30 – 1:30] THE PROBLEM — Set the Stakes

**[NARRATION]** *(leaning into specifics, slightly frustrated energy)*
> "Three problems. First — manual job hunting is a productivity sink. Five hours a day for a 2% response rate means you're trading weeks of your life for nothing. Second — the AI tools that exist cost $200-plus a month. Fresh grads can't afford that, and honestly, sending your resume and cover letter through someone else's API is a privacy risk. Third — every solution I've seen treats this as a 'script' problem. But it's actually an infrastructure problem. You need scraping, AI generation, parallel execution, observability, alerting, and recovery. So I built all of it."

**[SCREEN ACTION]**
- Slide 1: Big number "5 hrs/day" with strikethrough, replaced with "47 applications in 23 min"
- Slide 2: "Cloud AI: $200+/month" — crossed out, replaced with "$0 — runs entirely local"
- Slide 3: Architecture boxes start appearing one-by-one as you list them (scraping, AI, parallel, observability, alerting, recovery)

**[NOTES]**
- Don't apologize for "being too ambitious"
- This section earns you the right to show what you built

---

## [1:30 – 3:00] LIVE DEMO — Show, Don't Tell

### [1:30 – 2:00] Demo #1: Job Auto-Applier

**[NARRATION]** *(energetic, this is the money shot)*
> "Here's the auto-applier. I'm running it against Naukri right now — four portals configured, Naukri, Internshala, Indeed, Foundit. Watch this — it's scraping job listings, filtering for 'Full Stack AI Engineer' or 'Python Developer AI/ML', generating a tailored cover letter for each one with a local Ollama model — that's right, no OpenAI calls, no data leaving this machine — and applying. Forty-seven applications in twenty-three minutes. The same thing manually would take me a week."

**[SCREEN ACTION]**
- Terminal showing `auto_applier.py` running with live logs scrolling
- Highlight the "Local Ollama: qwen2.5-coder:3b" line — zoom in
- Cut to a counter: "47 / 50" with applications tally
- Brief glimpse of a generated cover letter being reviewed

**[NOTES]**
- Show real output, not mocked
- Keep cursor moving — recruiters can tell fake demos

### [2:00 – 2:30] Demo #2: Grafana Dashboard

**[NARRATION]** *(calmer, professional — "I know what I'm doing" energy)*
> "Every automation ships with observability. This is Grafana. Real metrics, scraped by Prometheus, scraped every fifteen seconds. I'm tracking scrapes per hour, applications sent, model latency, error rates, alert count. This is what production looks like. I didn't just build a script — I built a system."

**[SCREEN ACTION]**
- Grafana dashboard with multiple panels (scrapes, applications, latency P95, error rate, model switch count)
- Click into one panel — show the drill-down
- Briefly mention the `ollama_health` panel tracking model load times

**[NOTES]**
- Don't over-explain every metric — name 3, move on
- "Production observability" is a phrase junior devs don't say — say it confidently

### [2:30 – 3:00] Demo #3: AlertManager

**[NARRATION]** *(charming, slightly funny)*
> "And alerts. This is AlertManager wired to ntfy.sh. I get a push notification the moment something breaks. Let me trigger a fake error — watch my phone."

**[SCREEN ACTION]**
- Trigger an error in the terminal
- Cut to phone screen showing ntfy.sh notification arriving in real-time
- Tag notification: "🚨 JARVIS: scraper timeout on naukri.com"

> "I get alerts before my coffee gets cold."

**[NOTES]**
- The coffee line lands — smile when you say it
- Phone screen recording adds authenticity — use real phone, not a mockup

---

## [3:00 – 4:00] ARCHITECTURE & TRADE-OFFS

**[NARRATION]** *(thoughtful, "let me explain my thinking" energy)*
> "Three design decisions worth knowing. One — why local Ollama? Cost is obvious — zero marginal cost per inference. Privacy — your resume never leaves your machine. And latency — no network round-trip, I'm getting responses in under 800 milliseconds. Two — browser context pooling. Instead of spinning up a fresh Chromium for every job application, I keep warm browser contexts. Five to ten times faster, and way more polite to the job portals. Three — and this is the constraint that made me clever — I have eight gigabytes of RAM total. Eight. So I lazy-load models, only keep embeddings in memory, run two scrapers in parallel through a semaphore. Forced optimization. Best thing that ever happened to the architecture."

**[SCREEN ACTION]**
- Mermaid architecture diagram fills the screen
  - Top: User inputs (Naukri, LinkedIn, Pinterest)
  - Middle: JARVIS core (browser pool, semaphores, Ollama, PostgreSQL)
  - Bottom: Outputs (applications, posts, dashboard, alerts)
- Highlight each of the 3 decisions with a callout box as you talk

**[NOTES]**
- Don't oversell — these are real trade-offs you made
- The "forced optimization" reframe turns a constraint into a strength

---

## [4:00 – 4:30] THE OTHER PROJECTS — Breadth

**[NARRATION]** *(steady, no rush)*
> "JARVIS isn't a one-off. Here's SafeguardAI — a deep-learning audio threat-detection system. Real-time inference, custom CNN architecture, deployed on edge devices. And Movie Recommendation — hybrid collaborative-content filtering on the MovieLens 20-million dataset, served through a FastAPI backend. Same philosophy across all three — ship production-grade, not tutorial-grade. Real users, real alerts, real observability."

**[SCREEN ACTION]**
- Quick cuts: SafeguardAI demo (15 sec), Movie Recommender UI (15 sec)
- End on a montage of all three dashboards in a grid

**[NOTES]**
- Don't demo these in depth — just enough to show you build across domains
- "Production-grade, not tutorial-grade" is your tagline — repeat it

---

## [4:30 – 5:00] CLOSE — The Ask

**[NARRATION]** *(calm, direct, confident — not begging)*
> "I'm looking for a team that builds AI products where infrastructure matters. Where someone cares whether the alerts fire, whether the latency holds at P99, whether the model serving costs a dollar or a hundred. If that's you, the links are below — GitHub, resume, email. Thanks for watching."

**[SCREEN ACTION]**
- JARVIS dashboard in the foreground, "All Systems Nominal" green banner
- Lower third fades in with:
  - `github.com/venu0807`
  - `pvgreddy3@gmail.com`
  - LinkedIn handle placeholder
- Hold final frame for 3 seconds before cutting

**[NOTES]**
- End on the dashboard, not your face. Show the thing you built.
- "If that's you" is permission — they're not opting in to reject you; they're opting in to interview you

---

## 🎯 Production Checklist (Before Recording)

- [ ] **Clean runs**: do 3 dry runs to make sure all demos work
- [ ] **Real phone**: have ntfy.sh app installed and signed in
- [ ] **Audio**: use a decent mic; test levels
- [ ] **Lighting**: face the window, not away from it
- [ ] **Browser bookmarks bar**: hide it
- [ ] **Notifications**: mute Slack, email, Discord on recording machine
- [ ] **Terminal font**: bump to 16pt+ so it's readable on a 1080p Loom
- [ ] **Tab title**: change to "JARVIS Demo — Venu Gopal Reddy" so it shows in screen recordings
- [ ] **Dress code**: solid color t-shirt or hoodie, no logos competing with your work
- [ ] **BGM**: lo-fi at 10-15% volume, fade in at 0:05, fade out at 4:55

## 🎯 Post-Production

- [ ] Add **captions** (Loom auto-generates; review for accuracy)
- [ ] Add **chapters** at each timestamp boundary
- [ ] Thumbnail: dashboard screenshot with "JARVIS in 5 min" text
- [ ] Pin to: GitHub profile README, LinkedIn featured, resume top section
- [ ] Embed in JARVIS README + personal portfolio site

---

## 💡 Recording Tips

1. **Re-record takes** — don't be precious about the first run. Each take gets tighter.
2. **Speak 10% slower than feels natural** — you'll sound more confident on playback.
3. **Pause after each big claim** — let it land. "Forty-seven applications in twenty-three minutes." *(beat)* "The same thing manually would take me a week."
4. **Smile when you say "I get alerts before my coffee gets cold"** — it's the only joke, make it count.
5. **Cut every "um" and "uh"** in post — Loom makes this easy.
