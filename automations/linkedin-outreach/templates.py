"""templates.py — 5 cold-email templates (T1-T5) per 2-month plan.

T1 — Founder/CEO cold DM (formal, short, product-focused)
T2 — LinkedIn hiring manager DM (medium, balance skills+project)
T3 — Reply to recruiter (short, reply-style, attached resume)
T4 — Cold email to startup HR (formal, full cover letter, resume attached)
T5 — Follow-up Day 5-7 (very short, value-add reminder)

Each template uses {first_name}, {role}, {company}, {specific_thing}
placeholders. The composer fills these from post + bio context.
"""

# T1 — Founder/CEO cold DM (LinkedIn-friendly, <300 chars)
T1_FOUNDER_DM = """Subject: Quick question on {company}'s {role} opening

Hi {first_name},

Saw your post on LinkedIn about the {role} role at {company}.

I built JARVIS — a local-first AI automation platform that runs 25+ workflows on a laptop using Ollama (qwen2.5-coder + llama3.2). 99.2% uptime, $0 cloud AI cost.

{specific_thing}

Worth a 15-min chat this week?

— Venu
github.com/venu0807"""

# T2 — LinkedIn hiring manager DM (medium, project-focused)
T2_HIRING_MANAGER_DM = """Subject: {role} at {company} — fit for your team?

Hi {first_name},

Following up on your post about the {role} opening.

Quick context: I'm finishing my MCA in AI/ML, ship 30+ public projects (Python, TypeScript, React, ML), and built production systems with observability, rate-limiting, and zero-leak LLM routing.

{specific_thing}

My portfolio: github.com/venu0807

Open to a 20-min chat about your team's hiring process?

— Venu"""

# T3 — Reply to recruiter (short, direct, resume-ready)
T3_REPLY_RECRUITER = """Subject: Re: {role} at {company}

Hi {first_name},

Thanks for reaching out about the {role} role at {company}. Yes, I'm actively looking and very interested.

Quick background:
- MCA AI/ML (in progress, Galgotias University)
- 30+ shipped projects on GitHub (AI/ML, full-stack, DevOps)
- Production experience: Docker, PostgreSQL, Ollama, Playwright, Prometheus

{specific_thing}

Resume attached. Could we schedule a 15-min intro call this week?

— Venu
pvgreddy3@gmail.com"""

# T4 — Cold email to startup HR (formal, full cover letter, resume attached)
T4_COLD_EMAIL_HR = """Subject: Application for {role} — Venu Gopal Reddy

Hi {first_name},

I'm writing to express my interest in the {role} position at {company}. I'm finishing my MCA in AI/ML at Galgotias University and have shipped 30+ public projects across Python, TypeScript, React, and ML.

What I bring:
• Production engineering, not tutorial engineering — JARVIS has 25+ workflows, 99.2% uptime, real observability
• Full-stack across Python, TypeScript, Java, React, Django, FastAPI
• Resource-conscious — built for 8 GB RAM and 4 GB VRAM, which means I obsess about efficiency
• Local-first mindset — privacy and cost matter

{specific_thing}

My most relevant project for this role is JARVIS (github.com/venu0807/Jarvis) — a local-first AI automation platform that scrapes 4 job portals and applies with AI-tailored cover letters.

Resume attached. I'd value the chance to discuss how my background could fit {company}'s engineering team.

Best,
Venu Gopal Reddy
pvgreddy3@gmail.com
github.com/venu0807"""

# T5 — Follow-up Day 5-7 (very short, value-add reminder)
T5_FOLLOW_UP = """Subject: Following up on {role} at {company}

Hi {first_name},

Just following up on my note from earlier this week. I know you're busy — wanted to make sure my message didn't get buried.

Still very interested in the {role} role at {company}. Happy to share more about my JARVIS work (5-min demo) if useful.

Any updates on your end?

— Venu"""

TEMPLATES = {
    "T1": T1_FOUNDER_DM,
    "T2": T2_HIRING_MANAGER_DM,
    "T3": T3_REPLY_RECRUITER,
    "T4": T4_COLD_EMAIL_HR,
    "T5": T5_FOLLOW_UP,
}


def get_template(template_id: str) -> str:
    """Return template body by ID. Defaults to T2 if ID is unknown."""
    return TEMPLATES.get(template_id, T2_HIRING_MANAGER_DM)


def list_templates() -> list:
    """Return list of available template IDs."""
    return list(TEMPLATES.keys())
