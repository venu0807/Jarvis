"""templates.py — 5 smooth cold-email templates (T1-T5) for recruiters and hiring managers.

T1 — Founder/CEO cold DM (short, high-impact, product-focused)
T2 — Hiring Manager / Recruiter cold email (smooth, polite, project-focused)
T3 — Reply to recruiter (short, direct, resume-ready)
T4 — Cold email to Startup HR (formal cover letter, resume attached)
T5 — Follow-up Day 5-7 (very short, value-add reminder)

Each template uses {first_name}, {role}, {company}, {specific_thing} placeholders.
"""

# T1 — Founder/CEO cold DM (LinkedIn-friendly, <300 chars)
T1_FOUNDER_DM = """Subject: Quick question regarding {company}'s {role} opening

Hi {first_name},

I saw your recent update about the {role} role at {company}.

I built JARVIS — a local-first AI automation platform running 25+ workflows with local LLMs (Ollama qwen2.5-coder), 99.2% uptime, and zero API costs.

{specific_thing}

Would you be open to a brief 10-min introductory chat this week?

Best regards,
Venu Gopal Reddy
github.com/venu0807"""

# T2 — Smooth, respectful, project-focused cold email for recruiters / hiring managers
T2_HIRING_MANAGER_DM = """Subject: {role} opening at {company} — Venu Gopal Reddy

Hi {first_name},

I hope you're having a great week.

I came across your post regarding the {role} opportunity at {company} and wanted to reach out directly to express my interest.

I am an MCA graduate specializing in Software Engineering and AI/ML. I actively build and deploy production systems, including JARVIS (a local automation platform with 25+ workflows, rate-limiting, and intelligent LLM routing).

{specific_thing}

My core stack includes Python, TypeScript, React, Next.js, PostgreSQL, Docker, and REST APIs.

I've attached my resume for your review and would appreciate the opportunity to discuss how I can contribute to your team.

Portfolio: github.com/venu0807

Thank you for your time,
Venu Gopal Reddy
pvgreddy3@gmail.com"""

# T3 — Reply to recruiter (short, direct, resume-ready)
T3_REPLY_RECRUITER = """Subject: Re: {role} at {company} — Venu Gopal Reddy

Hi {first_name},

Thank you for sharing the {role} opportunity at {company}. I am actively looking and very interested in this role.

Quick background:
- MCA in Computer Applications / AI & Software Development (2026, 8.35 CGPA)
- Built and shipped 30+ public projects on GitHub (Python, TypeScript, AI/ML, full-stack)
- Hands-on experience with Docker, PostgreSQL, Ollama, Playwright, and FastAPI

{specific_thing}

I have attached my resume. Could we schedule a 15-min intro call this week?

Best regards,
Venu Gopal Reddy
pvgreddy3@gmail.com
github.com/venu0807"""

# T4 — Cold email to startup HR (formal, full cover letter, resume attached)
T4_COLD_EMAIL_HR = """Subject: Application for {role} — Venu Gopal Reddy

Hi {first_name},

I hope this email finds you well.

I am writing to express my strong interest in the {role} position at {company}. I am an MCA student (2026) with a passion for software engineering, web development, and AI systems.

What I bring:
• Practical Engineering: Built JARVIS — a 25+ workflow automation ecosystem with 99.2% uptime and robust system monitoring.
• Full-stack & Backend: Strong proficiency in Python, JavaScript, TypeScript, React, Next.js, Django, and SQL.
• Problem Solver: Consistent track record in building clean, efficient, and well-documented applications.

{specific_thing}

I have attached my resume for your consideration and would welcome the chance for an interview.

Best regards,
Venu Gopal Reddy
pvgreddy3@gmail.com
github.com/venu0807"""

# T5 — Follow-up Day 5-7 (very short, value-add reminder)
T5_FOLLOW_UP = """Subject: Following up on {role} at {company} — Venu Gopal Reddy

Hi {first_name},

I hope you're doing well.

I wanted to quickly follow up on my note from earlier regarding the {role} position at {company}. I know you have a busy schedule and wanted to make sure my message didn't get buried.

I remain very interested in the role and would love to connect for a quick 10-minute introductory conversation.

Thank you again for your time!

Best regards,
Venu Gopal Reddy
pvgreddy3@gmail.com"""

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
