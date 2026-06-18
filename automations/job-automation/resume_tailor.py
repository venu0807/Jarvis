"""
resume_tailor.py — Tailor user's resume for manual/skipped jobs using local Ollama
Outputs pixel-perfect LaTeX PDFs based on the exact provided template.
"""
import json
import argparse
import datetime
import os
import re
import time
import requests
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv(Path(__file__).parent / ".env")

# ── Route via JARVIS chokepoint (strict-zero-leak) ────────────────────────────
# Resume tailoring gets user-specific resume + job description. Audit-logged
# via ~/.jarvis/policy.call_llm(), force local.
try:
    # Prefer computed path (always correct relative to script) over env var
    JARVIS_HOME = str(Path(__file__).parent.parent.parent.resolve())
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm  # type: ignore
except Exception as _policy_err:  # pragma: no cover
    raise SystemExit(
        f"FATAL: resume_tailor cannot import ~/.jarvis/policy: {_policy_err!r}. "
        "Refusing direct ollama — strict-zero-leak requires policy audit log."
    )

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent / "output" / "resumes"

BASE_LATEX_RESUME = r"""\documentclass[{{FONT_SIZE}},a4paper]{article}

\usepackage[
  left={{MARGIN_SIDES}},
  right={{MARGIN_SIDES}},
  top={{MARGIN_TOP}},
  bottom={{MARGIN_BOTTOM}}
]{geometry}

\usepackage{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}

\setlength{\parindent}{0pt}
\pagenumbering{gobble}

\titleformat{\section}
  {\large\bfseries}
  {}
  {0em}
  {}
  [\titlerule]
\titlespacing*{\section}{0pt}{ {{SECTION_SPACE}} }{3pt}

\begin{document}

\begin{center}
    {\LARGE \textbf{${USER_FULL_NAME_UPPER}}} \\
    \vspace{1pt}
    \small 
    \href{mailto:${USER_EMAIL}}{${USER_EMAIL}} \;\; ${USER_PHONE} \;\; | \;\; \href{${USER_GITHUB_URL}}{GitHub} \;\; \href{${USER_LINKEDIN_URL}}{LinkedIn} \;\; \href{${USER_PORTFOLIO_URL}}{Portfolio} \;\; ${USER_LOCATION}
\end{center}

\section*{PROFESSIONAL SUMMARY}
{{SUMMARY}}

\section*{TECHNICAL SKILLS}
{{SKILLS}}

\section*{TECHNICAL PROJECTS \& EXPERIENCE}
\textbf{AI-Driven Audio Triggered Threat Detection} \textit{ | Backend and Android AI Developer} \hfill 2025 -- Present
\begin{itemize}[leftmargin=*, itemsep=1pt, topsep=1pt, parsep=0pt]
    \item Architected a CNN-based real-time audio classification pipeline for on-device inference using TensorFlow, achieving 89\% model accuracy with sub-100ms latency on Android hardware.
    \item Automated SMS threat alerts with live GPS location sharing triggered instantly on detection events, enabling real-time emergency response.
    \item Optimized the on-device deep learning inference pipeline to sustain 24x7 operation with under 5\% battery drain per hour, eliminating cloud dependency.
\end{itemize}

% \vspace{2pt}
\href{${USER_PROJECT_1_URL}}{\textbf{${USER_PROJECT_1_NAME}}} \textit{ | ${USER_PROJECT_1_ROLE}} \hfill 2024 -- 2025
\begin{itemize}[leftmargin=*, itemsep=1pt, topsep=1pt, parsep=0pt]
    \item Built an end-to-end ML-powered recommendation engine using content-based filtering, surfacing personalized results through a Django REST Framework backend and React.js frontend.
    \item Designed a normalized MySQL database schema managing 10,000+ records; applied strategic indexing and query optimization to reduce query latency by 60\%.
    \item Developed JWT-authenticated RESTful APIs with pagination and ORM-optimized queries, ensuring secure, performant, and scalable data delivery.
\end{itemize}

\section*{EDUCATION}
\textbf{Master of Computer Applications (AI \& ML)}\\ \hfill ${USER_UNIVERSITY} \hfill 2024 -- 2026 (Expected)
\textit{CGPA: 8.35 / 10} \\
% \vspace{2pt}
\textbf{Bachelor of Computer Science}\\ \hfill ${USER_UNDERGRAD_UNIVERSITY} \hfill 2019 -- 2022
\textit{Score: 85\%}

\section*{PROFESSIONAL TRAINING}

\href{https://drive.google.com/file/d/1CS81JFPO8L9vSmByeIGmTdETCP0P4K7V/view?usp=sharing}{\textbf{Full Stack Python Developer Program}} \textit{ | Besant Technologies} \hfill 2023 -- 2024 \\
Completed 400+ hours of project-based training in Python, Django, Django REST Framework, React.js, and MySQL. Delivered 5+ full-stack applications integrating machine learning models with production-ready backend APIs and responsive frontends. \\
% \vspace{2pt}
\href{https://drive.google.com/file/d/1ZVFwlRAh3_I4M5uSibgwYRN9qZ2K-_9M/view?usp=sharing}{\textbf{Full Stack Java Developer Program}} \textit{ | Wipro} \hfill July 2025 -- Oct 2025 \\
Enterprise curriculum covering Java, Object-Oriented Programming, Data Structures, SQL, and scalable API design with emphasis on algorithms and system architecture.

\section*{KEY ACHIEVEMENTS}
\begin{itemize}[leftmargin=*, itemsep=1pt, topsep=1pt, parsep=0pt]
    \item Reduced database query latency by 60\% through schema normalization, indexing strategy, and ORM optimization on a production recommendation platform.
    \item Achieved 89\% CNN model accuracy with real-time on-device inference under 100ms — without cloud dependency — on an Android-based threat detection system.
    \item Independently shipped ML-integrated applications across web (Django + React.js) and mobile (Android) platforms, demonstrating full-stack AI ownership. ecosystems.
\end{itemize}

\end{document}
"""


TAILOR_PROMPT = r"""\
You are an expert ATS (Applicant Tracking System) optimizer and resume writer. I need you to aggressively rewrite my Professional Summary and Technical Skills to perfectly match the provided Job Description.

STRICT VOLUME CONSTRAINTS (CRITICAL TO FIT EXACTLY 1 PAGE):
- Your summary MUST be exactly 50 to 65 words long. Do NOT exceed 65 words.
- Each of your 5 skill categories MUST contain exactly 5 to 6 skills. Do not exceed 6 skills per category.

STRICT RULES:
1. SKILLS EXPANSION: You MUST KEEP all of my existing skills. However, you MUST ALSO EXTRACT critical technical keywords from the Job Description and ADD THEM into my Technical Skills list (without exceeding the 8-skill limit per category).
2. SUMMARY REWRITE: Completely rewrite the summary. It must be a highly compelling paragraph that explicitly states I am an expert in the exact technologies requested by the job description. You MUST naturally include the exact Job Title.
3. CATEGORIZED SKILLS: You MUST NOT write the skills as a single paragraph. You MUST divide them into these exact categories using LaTeX syntax. Make sure you escape any & characters like \&:
\textbf{{Backend \& API Development:}} Python, Django, Django REST Framework (DRF), RESTful APIs, [INJECTED JOB KEYWORDS] \\
\textbf{{Frontend Development:}} React.js, JavaScript, HTML5, CSS3, Bootstrap, Responsive Design, [INJECTED JOB KEYWORDS] \\
\textbf{{Database Technologies:}} MySQL, Schema Design, Query Optimization, Indexing, ORM, [INJECTED JOB KEYWORDS] \\
\textbf{{Machine Learning:}} Scikit-learn, TensorFlow, CNNs, Feature Engineering, Model Training, [INJECTED JOB KEYWORDS] \\
\textbf{{Core Concepts:}} Object-Oriented Programming, Data Structures, Algorithms, [INJECTED JOB KEYWORDS]

4. Output ONLY the tailored summary and skills using these exact markers (do not output markdown or conversational text):

--- SUMMARY ---
[Your highly tailored, keyword-optimized professional summary here without any LaTeX formatting, just plain text]
--- SKILLS ---
[Your expanded technical skills here using the categorized LaTeX format shown above]

JOB TITLE: {title}
COMPANY: {company}
JOB DESCRIPTION:
{description}

MY CURRENT SUMMARY:
Full Stack Developer with hands-on experience building backend-driven applications using Python, Django, and Django REST Framework. Proven ability to design REST APIs, integrate machine learning models, and optimize database performance at scale. Strong focus on real-time processing, clean architecture, and production-ready AI systems.

MY CURRENT SKILLS:
Backend & API Development: Python, Django, Django REST Framework (DRF), RESTful APIs
Frontend Development: React.js, JavaScript, HTML5, CSS3, Bootstrap, Responsive Design
Database Technologies: MySQL, Schema Design, Query Optimization, Indexing, ORM
Machine Learning: Scikit-learn, TensorFlow, CNNs, Feature Engineering, Model Training
Core Concepts: Object-Oriented Programming, Data Structures, Algorithms
"""


# ── Ollama API ────────────────────────────────────────────────────────────────

def call_ollama(prompt: str) -> str:
    """
    Legacy helper name (kept for backward compatibility with callers that
    import this name). Routes through JARVIS policy: mode='run' forces local,
    pii_acknowledged=True because the prompt contains user's resume + job
    descriptions (PII class). Audit log gains one row per call.
    """
    try:
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=True,
            task_label="resume_tailor",
        )
        return (result.text or "").strip()
    except Exception as e:
        print(f"     ⚠️  Policy call_llm failed: {e}")
        return ""


# ── Resume tailor ─────────────────────────────────────────────────────────────

def tailor_resume(job: dict) -> str:
    """Pass job through AI and stitch it into the LaTeX template."""
    prompt = TAILOR_PROMPT.format(
        title=job.get("title", ""),
        company=job.get("company", ""),
        description=job.get("description") or f"Role: {job.get('title', '')}",
    )
    
    print(f"  🤖 Tailoring: {job.get('title', 'Unknown')} @ {job.get('company', 'Unknown')}")
    start = time.time()
    
    llm_output = call_ollama(prompt)
    
    # Extract the tailored summary and skills from LLM output
    summary_match = re.search(r"--- SUMMARY ---\s*(.*?)\s*--- SKILLS ---", llm_output, re.DOTALL)
    skills_match = re.search(r"--- SKILLS ---\s*(.*)", llm_output, re.DOTALL)

    new_summary = summary_match.group(1).strip() if summary_match else "Full Stack Developer building backend-driven applications with Python and Django."
    new_skills = skills_match.group(1).strip() if skills_match else "\\textbf{Backend \\& API Development:} Python, Django, Django REST Framework (DRF), RESTful APIs. \\\\\n\\textbf{Frontend Development:} React.js, JavaScript, HTML5, CSS3, Bootstrap, Responsive Design. \\\\\n\\textbf{Database Technologies:} MySQL, Schema Design, Query Optimization, Indexing, ORM \\\\\n\\textbf{Machine Learning:} Scikit-learn, TensorFlow, CNNs, Feature Engineering, Model Training \\\\\n\\textbf{Core Concepts:} Object-Oriented Programming, Data Structures, Algorithms."

    # ── Prevent LaTeX compilation crashes from unescaped symbols ──────────────
    def escape_latex(text: str) -> str:
        # Only escape if not already escaped by the AI
        text = re.sub(r"(?<!\\)&", r"\&", text)
        text = re.sub(r"(?<!\\)%", r"\%", text)
        text = re.sub(r"(?<!\\)\$", r"\$", text)
        text = re.sub(r"(?<!\\)#", r"\#", text)
        text = re.sub(r"(?<!\\)_", r"\_", text)
        return text

    new_summary = escape_latex(new_summary)
    new_skills = escape_latex(new_skills)
    # ──────────────────────────────────────────────────────────────────────────
    
    # ── Robust Skill Formatting ───────────────────────────────────────────────
    # If the AI used markdown bold instead of LaTeX bold, fix it
    new_skills = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", new_skills)
    
    # Ensure every bold category is on its own line with a LaTeX newline symbol
    fixed_skills = []
    for line in new_skills.split('\n'):
        line = line.strip()
        if not line: continue
        # Strip any markdown bullet points the AI might have hallucinated
        if line.startswith("- ") or line.startswith("* "):
            line = line[2:]
        # Enforce LaTeX line break if missing
        if r"\textbf{" in line and not line.endswith(r"\\"):
            line += r" \\"
        fixed_skills.append(line)
    
    new_skills = "\n".join(fixed_skills)
    # ──────────────────────────────────────────────────────────────────────────

    # ── Dynamic 1-Page Layout Resizer ─────────────────────────────────────────
    # We measure how much text the AI generated. If it's huge, we shrink the margins
    # and font so it perfectly fits 1 page. If it's small, we expand the spacing.
    total_len = len(new_summary) + len(new_skills)
    
    if total_len > 850:
        # Very long text: compress layout immediately to prevent spillover
        font_size = "10pt"
        m_sides = "0.4in"
        m_top = "0.4in"
        m_bot = "0.4in"
        item_sep = "0pt"
        sec_space = "4pt"
    elif total_len > 600:
        # Medium text: keep 11pt but aggressively tighten margins and padding
        font_size = "11pt"
        m_sides = "0.45in"
        m_top = "0.45in"
        m_bot = "0.4in"
        item_sep = "0pt"
        sec_space = "5pt"
    else:
        # Short text: normal/large layout to fill empty space
        font_size = "11pt"
        m_sides = "0.5in"
        m_top = "0.5in"
        m_bot = "0.5in"
        item_sep = "2pt"
        sec_space = "8pt"

    # Inject all dynamic size parameters and content into the base template
    final_latex = BASE_LATEX_RESUME.replace("{{SUMMARY}}", new_summary)\
                                   .replace("{{SKILLS}}", new_skills)\
                                   .replace("{{FONT_SIZE}}", font_size)\
                                   .replace("{{MARGIN_SIDES}}", m_sides)\
                                   .replace("{{MARGIN_TOP}}", m_top)\
                                   .replace("{{MARGIN_BOTTOM}}", m_bot)\
                                   .replace("{{ITEM_SEP}}", item_sep)\
                                   .replace("{{SECTION_SPACE}}", sec_space)
    
    # Fill in user placeholders from environment
    final_latex = final_latex.replace("${USER_FULL_NAME_UPPER}", os.getenv("USER_FULL_NAME_UPPER", "NAME"))\
                             .replace("${USER_EMAIL}", os.getenv("USER_EMAIL", "email@example.com"))\
                             .replace("${USER_PHONE}", os.getenv("USER_PHONE", "000-000-0000"))\
                             .replace("${USER_GITHUB_URL}", os.getenv("USER_GITHUB_URL", "https://github.com/"))\
                             .replace("${USER_LINKEDIN_URL}", os.getenv("USER_LINKEDIN_URL", "https://linkedin.com/"))\
                             .replace("${USER_PORTFOLIO_URL}", os.getenv("USER_PORTFOLIO_URL", "https://portfolio.com/"))\
                             .replace("${USER_LOCATION}", os.getenv("USER_LOCATION", "City, Country"))\
                             .replace("${USER_PROJECT_1_URL}", os.getenv("USER_PROJECT_1_URL", "https://github.com/"))\
                             .replace("${USER_PROJECT_1_NAME}", os.getenv("USER_PROJECT_1_NAME", "Project Name"))\
                             .replace("${USER_PROJECT_1_ROLE}", os.getenv("USER_PROJECT_1_ROLE", "Role"))\
                             .replace("${USER_UNIVERSITY}", os.getenv("USER_UNIVERSITY", "University Name"))\
                             .replace("${USER_UNDERGRAD_UNIVERSITY}", os.getenv("USER_UNDERGRAD_UNIVERSITY", "Undergrad University Name"))
    # ──────────────────────────────────────────────────────────────────────────

    print(f"     ✅ Done in {round(time.time()-start, 1)}s")
    return final_latex


TECTONIC_EXE = OUTPUT_DIR / "tectonic.exe"
TECTONIC_URL = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-pc-windows-msvc.zip"

def ensure_tectonic():
    """Automatically downloads a portable, standalone LaTeX compiler for Windows!"""
    if TECTONIC_EXE.exists():
        return True
    print("     📥 Downloading standalone Tectonic LaTeX compiler (~10MB) for local compilation...")
    zip_path = OUTPUT_DIR / "tectonic.zip"
    try:
        import urllib.request
        import zipfile
        urllib.request.urlretrieve(TECTONIC_URL, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(OUTPUT_DIR)
        zip_path.unlink()
        return True
    except Exception as e:
        print(f"     ⚠️  Failed to download Tectonic: {e}")
        return False


def save_latex_and_compile(content: str, job: dict) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    company = re.sub(r"[^\w\-]", "_", job.get("company", "Unknown")).strip("_")
    filename = f"Tailored_{company}_Resume"
    
    tex_path = OUTPUT_DIR / f"{filename}.tex"
    pdf_path = OUTPUT_DIR / f"{filename}.pdf"
    
    # Save the raw .tex file
    tex_path.write_text(content, encoding="utf-8")
    
    # ── Compile via Portable Tectonic ─────────────────────────────────────────
    if ensure_tectonic():
        try:
            result = subprocess.run(
                [str(TECTONIC_EXE), str(tex_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if result.returncode == 0:
                print(f"     📄 Compiled PDF (Local Tectonic): {pdf_path.name}")
                return {"tex": str(tex_path), "pdf": str(pdf_path)}
            else:
                print(f"     ⚠️  Tectonic compilation failed. Saved source .tex file: {tex_path.name}")
        except Exception as e:
            print(f"     ⚠️  Tectonic execution error: {e}")
    else:
        print(f"     ⚠️  No compiler available. Saved source .tex file: {tex_path.name}")

    # Clean up auxiliary files generated by LaTeX
    for ext in [".aux", ".log", ".out"]:
        aux_file = OUTPUT_DIR / f"{filename}{ext}"
        if aux_file.exists():
            try:
                aux_file.unlink()
            except:
                pass
                
    return {"tex": str(tex_path), "pdf": str(pdf_path) if pdf_path.exists() else None}


# ── Batch tailor (called from run_pipeline.py) ────────────────────────────────

def tailor_and_save(job: dict) -> dict:
    """Tailor resume for one job. Returns dict with paths."""
    tailored_latex = tailor_resume(job)
    paths = save_latex_and_compile(tailored_latex, job)
    return {
        "job":        job,
        "resume_txt": paths["tex"], # legacy key
        "resume_pdf": paths["pdf"], # legacy key
    }


# ── Standalone CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Resume Tailor — manual jobs only")
    parser.add_argument("--job-file",  required=True, help="Path to jobs JSON or application log JSON")
    parser.add_argument("--limit",     type=int,      default=20, help="Max jobs to tailor")
    args = parser.parse_args()

    with open(args.job_file, encoding="utf-8") as f:
        data = json.load(f)

    # Support both plain jobs list and application log format
    if isinstance(data, list):
        jobs = data[:args.limit]
    elif isinstance(data, dict) and "manual" in data:
        manual_entries = data.get("_manual_jobs", []) + data.get("_skipped_jobs", [])
        jobs = [e["job"] for e in manual_entries[:args.limit]]
    else:
        jobs = []

    print(f"\n📄 Resume Tailor (LaTeX Edition) — Job Automation Pipeline")
    print(f"   Model: {MODEL} (local Ollama)")
    print(f"   Jobs to tailor: {len(jobs)}\n")

    results = []
    for i, job in enumerate(jobs):
        print(f"[{i+1}/{len(jobs)}]")
        r = tailor_and_save(job)
        results.append(r)
        time.sleep(1)

    log_dir = Path(__file__).parent / "output" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"tailored_{datetime.date.today().isoformat()}.json"
    log_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Done! {len(results)} resumes tailored.")
    print(f"📁 Resumes: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
