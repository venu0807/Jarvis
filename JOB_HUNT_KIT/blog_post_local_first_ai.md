# Building a Local-First AI Automation Platform on 8 GB of RAM

*How I cut my cloud-AI bill to $0, automated my job search, and shipped 25 production workflows on a laptop*

---

If you've ever applied for a job in India as a fresh graduate, you know the math doesn't work. Cloud-AI tools promise to fix job hunting: they'll write your cover letters, optimize your resume, find openings, even auto-apply. They charge $200 a month. As a student, that might as well be a mortgage payment.

So I did what any stubborn engineer with 8 GB of RAM would do: I built my own.

I call it JARVIS — a local-first AI automation platform that runs on a laptop. It applied to 200+ jobs in its first month, costs $0 in cloud AI fees, and never once sent my resume to OpenAI's servers. Five minutes to read this post, and you'll understand how I built it, why I think every solo developer should consider local-first, and what I'd do differently next time.

## The Problem: Job Hunting Is Broken

Three forces make fresh-grad job hunting brutal:

**Manual work**. The naive approach — open Naukri, search "full stack AI engineer Hyderabad", filter by date, read each JD, write a custom cover letter, submit, repeat — burns 5 hours a day. Multiply by 30 days and you've spent 150 hours for what statistically becomes a 2% callback rate.

**Expensive tools**. The startups selling AI job assistants charge $100-$300/month. Useful, but unaffordable. Most freshers in India can't pay that without cutting into food or rent.

**Privacy**. Every time you paste your resume into ChatGPT or any cloud LLM, it leaves your machine. Your job search strategy — the companies you're targeting, the gaps you're trying to fill, the salary you're hoping for — all of it gets logged on someone else's server. I don't love that.

The real problem isn't a missing script. It's missing infrastructure. You need parallel scraping, AI generation, observability, alerting, recovery, and a feedback loop. Almost nobody builds all of it.

## Why Local-First Won Me Over

I considered three architectures:

**Cloud-only** (use OpenAI API, scrape via cloud functions). Pros: zero local CPU pressure. Cons: $200+/month, privacy issues, network round-trip latency.

**Hybrid** (local for embeddings, cloud for generation). Pros: cheaper. Cons: still leaks sensitive prompts, still network-dependent.

**Local-first** (everything on the laptop). Pros: $0 marginal cost, full privacy, sub-800ms inference, learning-by-building. Cons: 8 GB RAM is a real constraint.

I picked local-first because the constraints would force me to design around real production limits, not paper over them with cloud capacity. Constraints drive better engineering.

## The Architecture

```
Naukri ────┐
LinkedIn ──┤
Pinterest ─┤── JARVIS Orchestrator ──┬── Browser Pool ──┬── Applications
Indeed ────┤                         │                  │
Foundit ───┤                         ├── Ollama ─────────┤── Cover Letters
           │                         │   (qwen2.5,      │
n8n ───────┘                         │    llama3.2,     └── Embeddings
                                     │    nomic-embed)
                                     │
                                     ├── PostgreSQL ────── State
                                     │
                                     └── Prometheus ────── Metrics
                                            │
                                            └── Grafana + AlertManager
                                                   │
                                                   └── ntfy.sh (mobile push)
```

Five things matter here.

**Browser context pool**. Instead of spinning up a fresh Chromium per job application (10x slower, eats memory), I keep a pool of 5 warm browser contexts. When a worker needs to scrape, it grabs a context, runs its job, releases. Pool warming cut application latency from ~12s to ~2s.

**2-worker semaphore**. I cap concurrent scrapers at 2. Naukri, Internshala, Indeed, and Foundit all rate-limit. Going above 2 workers gets your IP temporarily banned. The semaphore is non-negotiable politeness.

**Lazy model loading**. Ollama serves three models — qwen2.5-coder (for selectors and code), llama3.2 (for reasoning and writing), nomic-embed-text (for embeddings). Each takes ~1.5 GB of VRAM when loaded. Total: 4.5 GB. I have 4 GB VRAM on a GTX 1650. So I keep only nomic-embed loaded permanently, and pre-warm the others 15 minutes before a scheduled automation runs. After each run, OLLAMA_KEEP_ALIVE=0 unloads them.

**Local LLM serving via Ollama**. This is the secret sauce. Ollama runs qwen2.5-coder:3b at ~50 tokens/sec on my GTX 1650. Sub-800ms P95 inference. No network round-trip. The model is the same one I'd use on OpenAI for many tasks — and it's free.

**Observability stack**. Every automation exposes a `/metrics` endpoint. Prometheus scrapes them every 15 seconds. Grafana renders four dashboards: scrapes per hour, applications sent, model latency P95, error budget. AlertManager evaluates rules and pushes to ntfy.sh when something breaks. I get a phone notification the moment a scraper fails. That's how I sleep at night.

## The Hard Parts

Three engineering challenges nearly killed the project. Each one taught me something.

### Browser Pool Warming

My first version spawned a fresh Chromium for every job application. Each Chromium startup: 800ms cold start, 1.2 GB memory peak. With 50 applications/hour, that's 50 GB-hours of memory churn daily.

The fix:

```python
class BrowserPool:
    def __init__(self, size: int = 5):
        self._pool = asyncio.Queue(maxsize=size)
        for _ in range(size):
            ctx = await self._create_context()
            await self._pool.put(ctx)

    async def acquire(self) -> BrowserContext:
        return await self._pool.get()

    async def release(self, ctx: BrowserContext):
        # Clear cookies + storage between uses
        await ctx.clear_cookies()
        await self._pool.put(ctx)
```

A pool of 5 warm contexts, reused across requests, cut scraper memory pressure by 80% and reduced per-application latency by 8x. The trick: clear cookies and storage between uses so contexts don't leak state across jobs.

### Model Memory Pressure

Qwen2.5-coder is 1.8 GB. Llama3.2 is 1.7 GB. nomic-embed is 250 MB. My GPU has 4 GB. All three loaded simultaneously: 3.75 GB — almost full, but technically fits. In practice, it OOMed whenever a model was switching contexts.

The fix was a three-part strategy:

1. **Pre-warm before scheduled runs** — 15 minutes before the cron fires, I `ollama run` each model with a tiny prompt. This loads it into VRAM.
2. **OLLAMA_KEEP_ALIVE=0** — after each request, the model unloads automatically. No manual eviction logic needed.
3. **Always-on embeddings model** — nomic-embed is small and used everywhere. It stays loaded permanently.

```bash
# Pre-warm script (run 15 min before scheduled automation)
ollama run qwen2.5-coder:3b "ready" --verbose=false
ollama run llama3.2:3b "ready" --verbose=false
# nomic-embed stays loaded
```

This pattern — pre-warm + auto-unload + always-on small model — is reusable for anyone running multiple models on constrained hardware.

### Portal Rate Limits

Naukri silently rate-limits after ~80 requests/hour from the same IP. I learned this the hard way — my scraper spiked to 250 applications/hour on day 3, then got 0 responses for 48 hours while my IP was throttled.

The fix:

```python
# Portal-specific throttle settings
THROTTLE_CONFIG = {
    "naukri":     {"rps": 0.5,  "burst": 3,   "cooldown": 300},  # 1 req / 2s
    "internshala": {"rps": 1.0, "burst": 5,   "cooldown": 60},
    "indeed":     {"rps": 0.3,  "burst": 2,   "cooldown": 600},
    "foundit":    {"rps": 0.8,  "burst": 4,   "cooldown": 120},
}

# Retry with exponential backoff
async def scrape_with_backoff(portal: str, fn):
    for attempt in range(5):
        try:
            return await fn()
        except RateLimitError:
            wait = 2 ** attempt * THROTTLE_CONFIG[portal]["cooldown"]
            await asyncio.sleep(wait)
    raise MaxRetriesExceeded()
```

Each portal has its own throttle profile. Failures trigger exponential backoff. After 5 failed attempts, the alert fires to my phone and the scraper moves on to the next portal.

## Observability Matters

The biggest lesson: observability isn't optional, it's how you ship without anxiety.

My Prometheus + Grafana + AlertManager setup gives me:

- **Counters**: `applications_sent_total`, `cover_letters_generated_total`, `errors_total`
- **Histograms**: `model_inference_duration_seconds`, `scraper_duration_seconds`
- **Gauges**: `browser_pool_size`, `model_memory_mb`

A simple alert rule:

```yaml
# prometheus/rules/job-automation.yml
- alert: HighScraperErrorRate
  expr: |
    rate(errors_total{automation="job-automation"}[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Job scraper error rate > 10%"
    description: "{{ $value }} errors/sec over last 5 min"
```

When this fires, AlertManager routes to ntfy.sh. My phone buzzes. I check the dashboard, see which portal is failing, and either fix the scraper or accept the throttle and wait.

Without this stack, I'd be checking terminal output every 30 minutes, hoping nothing broke. With it, I check once a day, because the system tells me when something needs attention.

## What I Learned

**Forced constraints drive better design**. 8 GB RAM wasn't a limitation — it was a forcing function. I had to think about memory, model loading, semaphore sizing, and observability in ways I'd have skipped if I'd had 32 GB and an unlimited cloud budget.

**Observability is the difference between a side project and a production system**. Any developer can write a scraper. Few ship one that tells you when it's broken.

**Local-first is viable for solo builders and small teams**. Cloud AI has its place — when you need GPT-4 quality or billion-vector retrieval. But for the 80% of tasks where a small open-source model works, local serving is faster, cheaper, and more private.

**Production-grade ≠ complex**. JARVIS has 25 workflows, real observability, real recovery, real alerting. None of it is novel engineering. It's all patterns anyone can apply: pools, semaphores, retries, metrics, alerts.

## What's Next

Three things on my roadmap:

**Multi-user support**. Right now JARVIS is single-tenant. Adding auth + per-user secrets would let me share it with friends who are also job hunting.

**Plugin system for community automations**. A simple YAML schema for declaring an automation. Anyone can contribute without knowing Python internals.

**Vector memory layer across automations**. JARVIS already has an embeddings model. The next step is a shared vector store so that, say, the LinkedIn outreach automation can reference successful cover letters from the job auto-applier.

## Ship Your Own

If you're a hiring manager reading this: JARVIS is open source at [github.com/venu0807/Jarvis](https://github.com/venu0807/Jarvis). I'd love to walk you through it.

If you're a student reading this: your constraint is your advantage. Mine was 8 GB of RAM. It forced me to design something that works on real hardware. Yours might be budget, time, or both. Build around them.

And if you're just curious about the code: it's documented. The interesting parts are in `automations/browser_pool.py` and `automations/job-automation/auto_applier.py`.

---

**Venu Gopal Reddy** is an MCA AI/ML student at Galgotias University, building automation tools to make fresh-grad job hunting less painful. He lives in Hyderabad, works on a laptop with 8 GB of RAM, and is currently looking for his first Full Stack AI Engineer role.

- GitHub: [@venu0807](https://github.com/venu0807)
- Email: pvgreddy3@gmail.com
- LinkedIn: [linkedin.com/in/venu0807](https://linkedin.com/in/venu0807)
