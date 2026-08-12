import os
import sys
import time
import re
import urllib.request
import zipfile
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))

from policy import call_llm

OUTPUT_DIR = BASE_DIR / "output" / "cheatsheets"

TECTONIC_EXE = OUTPUT_DIR / "tectonic.exe"
TECTONIC_URL = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-pc-windows-msvc.zip"

BASE_LATEX_CHEATSHEET = r"""\documentclass[11pt,a4paper]{article}

\usepackage[left=0.5in, right=0.5in, top=0.5in, bottom=0.5in]{geometry}
\usepackage{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{xcolor}

\setlength{\parindent}{0pt}
\pagenumbering{gobble}

\titleformat{\section}
  {\large\bfseries\color{blue!70!black}}
  {}
  {0em}
  {}
  [\titlerule]
\titlespacing*{\section}{0pt}{8pt}{4pt}

\begin{document}

\begin{center}
    {\LARGE \textbf{Interview Cheat Sheet}} \\
    \vspace{2pt}
    {\large \textbf{Company:} {{COMPANY_NAME}}} \\
    \vspace{2pt}
    \small \textit{Generated automatically by Jarvis AI}
\end{center}

\section*{COMPANY OVERVIEW}
{{OVERVIEW}}

\section*{PREDICTED TECHNICAL QUESTIONS}
\begin{itemize}[leftmargin=*, itemsep=2pt]
{{QUESTIONS}}
\end{itemize}

\section*{TECHNICAL REFRESHER}
{{REFRESHER}}

\section*{BEHAVIORAL TIPS}
\begin{itemize}[leftmargin=*, itemsep=2pt]
{{BEHAVIORAL}}
\end{itemize}

\end{document}
"""

PROMPT_TEMPLATE = r"""
You are an expert technical recruiter and senior engineering manager.
Based on the following email offering an interview or assessment to the candidate, generate a highly targeted Interview Cheat Sheet.

Email Subject: {subject}
Email Body: {body}

You MUST exhaustively extract every single technical skill, tool, framework, and library mentioned in the email or job description. 
Predict the top 4 technical questions they will ask (focusing specifically on those extracted skills).
Provide a comprehensive technical refresher that explicitly covers ALL extracted skills and libraries necessary to crack the job.
Finally, suggest 3 behavioral tips.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS (no markdown blocks, no conversational text):

--- COMPANY ---
[Extracted Company Name]
--- OVERVIEW ---
[1-2 sentences about what the company does and their likely tech stack]
--- QUESTIONS ---
\item \textbf{Question 1:} [Text]
\item \textbf{Question 2:} [Text]
\item \textbf{Question 3:} [Text]
\item \textbf{Question 4:} [Text]
--- REFRESHER ---
[A comprehensive technical refresher explicitly covering ALL skills, tools, and libraries mentioned in the email context. Use bold text to highlight key libraries.]
--- BEHAVIORAL ---
\item [Tip 1]
\item [Tip 2]
\item [Tip 3]
"""

def ensure_tectonic():
    if TECTONIC_EXE.exists():
        return True
    print("     📥 Downloading Tectonic LaTeX compiler for Cheatsheets...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = OUTPUT_DIR / "tectonic.zip"
    try:
        urllib.request.urlretrieve(TECTONIC_URL, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(OUTPUT_DIR)
        zip_path.unlink()
        return True
    except Exception as e:
        print(f"     ⚠️  Failed to download Tectonic: {e}")
        return False

def escape_latex(text: str) -> str:
    text = re.sub(r"(?<!\\)&", r"\&", text)
    text = re.sub(r"(?<!\\)%", r"\%", text)
    text = re.sub(r"(?<!\\)\$", r"\$", text)
    text = re.sub(r"(?<!\\)#", r"\#", text)
    text = re.sub(r"(?<!\\)_", r"\_", text)
    return text

def generate_cheatsheet(subject, body):
    print("🧠 Generating Interview Cheatsheet via LLM...")
    prompt = PROMPT_TEMPLATE.format(subject=subject, body=body[:1500])
    
    try:
        response = call_llm(prompt=prompt, mode="run", force="local", pii_acknowledged=True, task_label="cheatsheet_gen")
        llm_out = response.text.strip()
        
        company_m = re.search(r"--- COMPANY ---\s*(.*?)\s*--- OVERVIEW ---", llm_out, re.DOTALL)
        overview_m = re.search(r"--- OVERVIEW ---\s*(.*?)\s*--- QUESTIONS ---", llm_out, re.DOTALL)
        questions_m = re.search(r"--- QUESTIONS ---\s*(.*?)\s*--- REFRESHER ---", llm_out, re.DOTALL)
        refresher_m = re.search(r"--- REFRESHER ---\s*(.*?)\s*--- BEHAVIORAL ---", llm_out, re.DOTALL)
        behavioral_m = re.search(r"--- BEHAVIORAL ---\s*(.*)", llm_out, re.DOTALL)
        
        company = escape_latex(company_m.group(1).strip()) if company_m else "Unknown Company"
        overview = escape_latex(overview_m.group(1).strip()) if overview_m else "Overview not available."
        questions = escape_latex(questions_m.group(1).strip()) if questions_m else r"\item Generic Question"
        refresher = escape_latex(refresher_m.group(1).strip()) if refresher_m else "Refresher not available."
        behavioral = escape_latex(behavioral_m.group(1).strip()) if behavioral_m else r"\item Generic behavioral tip."
        
        # Ensure LaTeX itemize format is somewhat preserved even if LLM messes up
        if r"\item" not in questions:
            questions = r"\item " + questions.replace("\n", "\n\\item ")
        if r"\item" not in behavioral:
            behavioral = r"\item " + behavioral.replace("\n", "\n\\item ")
            
        latex = BASE_LATEX_CHEATSHEET.replace("{{COMPANY_NAME}}", company)
        latex = latex.replace("{{OVERVIEW}}", overview)
        latex = latex.replace("{{QUESTIONS}}", questions)
        latex = latex.replace("{{REFRESHER}}", refresher)
        latex = latex.replace("{{BEHAVIORAL}}", behavioral)
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe_company = re.sub(r"[^\w\-]", "_", company)
        tex_path = OUTPUT_DIR / f"Cheatsheet_{safe_company}.tex"
        pdf_path = OUTPUT_DIR / f"Cheatsheet_{safe_company}.pdf"
        
        tex_path.write_text(latex, encoding="utf-8")
        
        if ensure_tectonic():
            subprocess.run([str(TECTONIC_EXE), str(tex_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if pdf_path.exists():
                print(f"📄 Generated Cheatsheet PDF: {pdf_path}")
                return str(pdf_path)
            
        print(f"⚠️ PDF generation failed. Saved .tex file at {tex_path}")
        return str(tex_path)
        
    except Exception as e:
        print(f"❌ Failed to generate cheatsheet: {e}")
        return None
