# Portfolio Site Update Guide — `venureddy.vercel.app`

> **Time**: 60 minutes
> **Goal**: Update your live portfolio to reflect all 30+ projects, JARVIS prominently, and the job hunt narrative

---

## 📍 Current State

**Live URL**: https://venureddy.vercel.app
**Repo**: `portfolio` or `portfolio_1` (check which deploys)

---

## 🎯 What Needs Updating

### 1. Hero Section
- **Current**: Likely generic "Full Stack Developer"
- **New**: "Full Stack AI Engineer | 30+ Shipped Projects | Local-First AI | JARVIS • SafeAI • RoastMyCV"
- **CTA**: "View Projects" → scroll to projects section

### 2. About Section
- **Current**: Brief bio
- **New**: 3-paragraph narrative:
  1. **Who**: MCA AI/ML student, 30+ projects across Python/TypeScript/React/ML
  2. **What**: Built JARVIS (local-first AI automation), SafeAI (89% accuracy CNN), Recommendation System (60% query reduction)
  3. **Looking for**: Full Stack AI Engineer role, India (Gurugram/Delhi/remote), entry-level

### 3. Featured Projects (Top 6 — reorder to these)

| # | Project | Repo | Live Demo | Key Tech | One-Liner |
|---|---|---|---|---|---|
| 1 | **JARVIS** | github.com/venu0807/Jarvis | — | Python, Ollama, Playwright, PostgreSQL, Prometheus | 25+ production workflows, local-first AI, 99.2% uptime, $0 cloud |
| 2 | **SafeAI** | github.com/venu0807/SafeAI | — | Python, TensorFlow, Android | CNN audio threat detection, 89% accuracy, sub-100ms edge inference |
| 3 | **RoastMyCV** | github.com/venu0807/roastmycv | — | TypeScript, React, AI | AI resume reviewer with brutal honest feedback |
| 4 | **Recommendation_System** | github.com/venu0807/Recommendation_System | — | Django, React, MySQL, Scikit-learn | Full-stack movie rec, 60% query latency reduction |
| 5 | **AI-Based-University-Query-Assistant** | github.com/venu0807/AI-Based-University-Query-Assistant | — | Python, RAG, Vector DB | RAG chatbot for university queries |
| 6 | **ai-coding-agent** | github.com/venu0807/ai-coding-agent | — | Python, Agentic loops | Agentic AI coding assistant |

### 4. All Projects Grid (30+ projects)

Group by category:

#### AI / ML (9)
- JARVIS, SafeAI, Recommendation_System, RoastMyCV, AI-Based-University-Query-Assistant, ai-coding-agent, ai-coding-factory, ANN-Classification-Churn-Prediction, Synthetic-Fraud-AI, Nutrition_Agent, Machine_Learining-Deep_Learining

#### Full Stack (8)
- briefforge, website-prospector, picscore, affiliate-store, portfolio, portfolio_1, venureddy.vercel.app, node-easy-notes-app

#### Backend / DevOps (7)
- finance_backend, DJ, HealthCare, hn-scraper, JWT, Event-Intelligence-Program, Automation---QA-Developer

#### Others (6)
- Automation---QA-Developer, ai-excel-interviewer, rls-guard-dog, ...

---

## 🛠️ How To Update

### Option A: If using `portfolio` repo (Next.js + Tailwind)

```bash
cd ~/portfolio  # or wherever your portfolio repo is
git pull origin main

# Edit these files:
# - src/app/page.tsx (hero + about)
# - src/components/FeaturedProjects.tsx (top 6)
# - src/components/AllProjects.tsx (30+ grid)
# - data/projects.ts (project data)

git add -A
git commit -m "Update portfolio: 30+ projects, JARVIS featured, job hunt narrative"
git push origin main
# Vercel auto-deploys
```

### Option B: If using `portfolio_1` repo

Same process, check which repo deploys to `venureddy.vercel.app` (check Vercel dashboard).

### Option C: Quick manual edit via Vercel

1. Go to https://vercel.com/dashboard
2. Select `venureddy` project
3. **Deployments** → Latest → **View Source** → Edit files directly in Vercel (for quick text changes)

---

## 📝 Content to Copy-Paste

### Hero (Markdown for reference)
```markdown
# Full Stack AI Engineer
## 30+ Shipped Projects • Local-First AI • Python · TypeScript · React · ML
### [View Projects] • [LinkedIn] • [GitHub] • [Email]
```

### About (3 paragraphs)
```
I build AI systems that run on a laptop, not in someone else's cloud.

My flagship project is JARVIS — a local-first AI automation platform that runs 25+ production workflows using Ollama (qwen2.5-coder + llama3.2) with zero cloud AI cost. It scrapes 4 job portals, generates personalized cover letters, and applies automatically — all with full observability (Prometheus/Grafana) and zero data leakage.

Beyond JARVIS, I've shipped 30+ public projects across AI/ML (SafeAI: 89% accuracy CNN audio threat detection, sub-100ms inference), full-stack (Recommendation System: Django + React, 60% query latency reduction), and DevOps (PostgreSQL, Docker, Prometheus/Grafana). I'm finishing my MCA in AI/ML at Galgotias University and looking for a Full Stack AI Engineer role in Gurugram, Delhi, or remote.

Tech I use daily: Python, TypeScript, React, Django, FastAPI, PostgreSQL, Ollama, Playwright, Docker, Prometheus/Grafana.
```

---

## ✅ Post-Update Checklist

- [ ] Hero reflects "Full Stack AI Engineer"
- [ ] About section mentions 30+ projects, JARVIS, SafeAI, metrics
- [ ] Featured Projects: JARVIS #1, SafeAI #2, RoastMyCV #3, RecSys #4, RAG #5, ai-coding-agent #6
- [ ] All 30+ projects listed in grid, grouped by category
- [ ] Each project card: name, 1-line desc, tech badges, GitHub link
- [ ] Loom demo embedded or linked in JARVIS card
- [ ] Contact: email, LinkedIn, GitHub all working
- [ ] Mobile responsive check
- [ ] Deployed to Vercel successfully

---

## 🔗 Links to Verify After Deploy

- https://venureddy.vercel.app (hero + about)
- https://venureddy.vercel.app/projects (all 30+)
- https://venureddy.vercel.app/projects/jarvis (JARVIS detail)
- Mobile view (Chrome DevTools device toolbar)

---

## 📋 If You Want Me To Do It

Give me access to the portfolio repo (or tell me which one: `portfolio` or `portfolio_1`) and I can:
1. Pull the repo
2. Update all content
3. Commit + push
4. Vercel auto-deploys

**Just tell me the repo name/location and I'll handle it.**