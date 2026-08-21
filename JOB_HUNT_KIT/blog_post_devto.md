---
title: 'I Built 30+ Projects in a Year. JARVIS Was Just One of Them.'
published: false
description: 'A student developer story about shipping across Python, TypeScript, React, and ML — and what 30+ public repos taught me about building production systems.'
tags: 'career, productivity, ai, opensource, webdev'
canonical_url: https://github.com/venu0807
cover_image: https://raw.githubusercontent.com/venu0807/venu0807/main/assets/banner.png
---

If you've ever applied for a job in India as a fresh graduate, you know the math doesn't work. Cloud-AI tools promise to fix job hunting: they'll write your cover letters, optimize your resume, find openings, even auto-apply. They charge $200 a month. As a student, that might as well be a mortgage payment.

So I did what any stubborn engineer with 8 GB of RAM would do: I built my own.

30+ projects later, JARVIS is just one of them. This post is about what 30+ shipped projects in a year taught me about production engineering — and why I think every developer should be shipping constantly, not just learning.

## The Year of Shipping

Twelve months ago, I had a B.Sc in Computer Science and an MCA in progress. I knew Python, Django, and React from coursework. I had no idea what production engineering looked like.

So I started building. Not tutorials, not courses — actual projects with real users (even if "users" was just me).

**AI / ML (9 projects)**:
- [JARVIS](https://github.com/venu0807/Jarvis) — local-first AI automation platform (25+ workflows)
- [SafeAI](https://github.com/venu0807/SafeAI) — on-device audio threat detection (CNN, 89% accuracy)
- [Recommendation_System](https://github.com/venu0807/Recommendation_System) — movie recommender (Django + scikit-learn)
- [RoastMyCV](https://github.com/venu0807/roastmycv) — AI resume reviewer (TypeScript)
- [AI-Based-University-Query-Assistant](https://github.com/venu0807/AI-Based-University-Query-Assistant) — RAG chatbot
- [ai-coding-agent](https://github.com/venu0807/ai-coding-agent), [ai-coding-factory](https://github.com/venu0807/ai-coding-factory) — agentic AI tools
- ANN-Classification-Churn-Prediction · Synthetic-Fraud-AI · Nutrition_Agent

**Full Stack (7+ projects)**:
- [briefforge](https://github.com/venu0807/briefforge) — content tool
- [website-prospector](https://github.com/venu0807/website-prospector) — lead generation
- [picscore](https://github.com/venu0807/picscore) — visual scoring
- [affiliate-store](https://github.com/venu0807/affiliate-store) — e-commerce
- portfolio · portfolio_1 — portfolio sites
- finance_backend · DJ · HealthCare — Python backends

**Languages I shipped in**:
- **Python** (60% of repos)
- **TypeScript** (25%)
- **JavaScript** (10%)
- **Java** (5%)

That's not a stack — that's a habit.

## The Constraints That Made Me Better

JARVIS — my flagship project — taught me the most because it had the tightest constraints:

- **8 GB RAM** (WSL split: 5 GB WSL, 3 GB Windows)
- **4 GB VRAM** (GTX 1650 — entry-level GPU)
- **$0/month** budget (I'm a student)

These constraints forced real engineering decisions:

**1. Lazy model loading.** Ollama's `KEEP_ALIVE=0` auto-unloads models after each request. Three models needed (qwen2.5-coder, llama3.2, nomic-embed), only 4 GB VRAM. Pre-warm scheduler loads the right model 15 minutes before each scheduled run. RAM stays at 2.3 GB instead of 5.7 GB.

**2. Browser context pool.** Naïve scraping opens a new browser per request. I built a 2-worker semaphore pool that reuses contexts. Result: 5-10× faster, polite to rate limits, no IP bans.

**3. Prometheus + Grafana + AlertManager.** Real observability. ntfy.sh pushes alerts to my phone when something breaks. I sleep at night knowing my job applications are running.

**4. Sub-800ms P95 LLM inference.** Cloud AI is 200-2000ms per request. Local Ollama on a $200 GPU is 400-800ms. For high-volume use cases, local wins on latency and cost.

## What 30+ Projects Taught Me

### 1. Production ≠ Tutorial

Reading Django docs taught me Django. Shipping a Django REST Framework API with JWT auth, pagination, and ORM optimization taught me production. The difference is 10× more debugging time, but 100× more learning.

### 2. Constraints Are a Feature

If I'd had $1000/month for cloud AI, I'd have used OpenAI's API and never learned about model quantization, browser pool design, or rate limit handling. The constraints forced me to learn production engineering.

### 3. Local-First Is Viable for Solo Builders

Sub-800ms inference, $0 marginal cost, full privacy, works offline. For 80% of tasks where small open-source models work, local is faster and cheaper than cloud. The cloud-AI lock-in is optional, not mandatory.

### 4. Shipping > Learning

Each project taught me 5× more than the equivalent course. AI-Based-University-Query-Assistant taught me RAG pipelines. RoastMyCV taught me prompt engineering. JARVIS taught me production observability. No course covers this.

### 5. Breadth Beats Depth (At First)

Hiring managers for "Full Stack AI Engineer" roles want people who've shipped across the stack, not specialists. My 30+ projects across Python/TypeScript/Java/React signal that I can pick up any new tool. That signal is more valuable than mastery of one.

## The Hard Parts (That I'd Do Differently)

### 1. Should Have Started Docker Sooner

I tried to run everything natively on WSL for 6 months. It worked, but deployments were painful. I finally bit the bullet and added Docker Compose. Wish I'd done it on day 1.

### 2. Should Have Set Up CI/CD Earlier

Tests were "run locally and pray." Now I have GitHub Actions. Should've been there from project 5.

### 3. Should Have Documented as I Built

JARVIS has 15+ markdown files but I wrote most after the fact. Documenting-as-you-go is faster and more accurate.

### 4. Should've Rotated Portal Credentials Earlier

I had real Naukri/LinkedIn/Indeed/Foundit credentials in `.env` files for 6 months before I realized the security risk. Lesson: rotate credentials quarterly, use secrets managers, never commit `.env` to git.

## What's Next

I'm finishing my MCA in AI/ML while applying to Full Stack AI Engineer roles. JARVIS is my portfolio centerpiece, but the 30+ repos are my portfolio breadth. If you're hiring for Full Stack AI / AI Engineer / Backend Engineer roles and want someone who's shipped production systems across the stack — let's talk.

- **Portfolio**: [github.com/venu0807](https://github.com/venu0807) (30+ repos)
- **Email**: pvgreddy3@gmail.com
- **LinkedIn**: [linkedin.com/in/venu-gopal-reddy-palugulla-4948b8258](https://linkedin.com/in/venu-gopal-reddy-palugulla-4948b8258)

If you read this far — thanks. Keep shipping.

---

**Tags**: #ai #localfirst #career #opensource #productivity #fullstack

**Read time**: ~7 minutes
