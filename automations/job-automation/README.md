# OpenClaw Job Automation Pipeline

An automated pipeline designed to streamline the job search and application process. It handles everything from live-searching job listings across multiple portals to automatically applying, answering screening questions, tailoring resumes dynamically with AI, and sending an Email summary with the day's actions.

## 🌟 Features
- **Live Search & Auto Apply Engine**: Automates the search, login, and application process using Playwright. Navigates native application forms for active portals (LinkedIn outreach continues via `linkedin-outreach/`; see `portals/__init__.py` for the cut list). Active portals: Naukri, Internshala, Indeed, Foundit.
- **Smart Form Auto-Fill**: Automatically detects and answers screening questions on portals (e.g., filling in Fresher, 0 CTC, education, skills, and Yes/No questions).
- **External Site Detection**: Safely detects and skips applications that redirect to external company websites, logging them for manual review to prevent browser crashes.
- **AI Resume Tailoring**: Employs a local **Ollama** model to adapt and inject ATS-friendly keywords into a custom LaTeX resume. A local Tectonic compiler is automatically downloaded to stitch and compile pixel-perfect PDFs for manual applications.
- **Email Notifications** (Telegram removed 2026-06-16): Summarizes the day's actions, including auto-applied jobs, manual application links (with skip reasons), and generated tailored resumes, sent as an Email summary.
- **Auto Cleanup**: Maintains disk health by automatically purging local PDF resumes and JSON logs older than 7 days (168 hours).

## 🏗️ Project Architecture
- `auto_applier.py`: Uses `playwright` to load authenticated sessions, search dynamically, and apply for jobs directly on platform portals. Tracks applications to prevent duplicates.
- `resume_tailor.py`: Connects to a local Ollama server. Rewrites your professional summary and skills to match specific job descriptions and outputs a PDF using LaTeX.
- `notifier.py`: Formats the summary into an HTML email (and plain-text fallback) and sends it via Gmail.
- `run_pipeline.py`: The master orchestrator that automatically cleans old files, runs the auto-applier, tailors resumes, and sends notifications.

## 📋 Prerequisites
1. Python 3.10+
2. Local Ollama Server: Must be running with your chosen model (default: `phi4-mini`).
3. Playwright Browsers: Required for the auto applier.
4. Gmail App Password: Used by `notifier.py` for daily summaries (Telegram removed 2026-06-16 — no second credential required).

## 🚀 Setup & Installation

1. **Clone or Navigate to the Directory**:
   Ensure you are in the `job-automation` workspace.

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Browsers**:
   ```bash
   playwright install chromium
   ```

4. **Environment Configuration**:
   Create a `.env` file in the root of the project with your credentials and config:
   ```ini
   # Apply limits and execution mode
   DAILY_LIMIT=15
   HEADLESS=true
   OLLAMA_MODEL=phi4-mini

   # Portal Credentials
   NAUKRI_EMAIL=your_email
   NAUKRI_PASSWORD=your_password
   
   INTERNSHALA_EMAIL=your_email
   INTERNSHALA_PASSWORD=your_password
   
   LINKEDIN_EMAIL=your_email
   LINKEDIN_PASSWORD=your_password
   
   INDEED_EMAIL=your_email
   INDEED_PASSWORD=your_password
   
   # Email Notifier Credentials
   SMTP_EMAIL=your_smtp_email@gmail.com
   SMTP_PASSWORD=your_app_password
   NOTIFY_EMAIL=email_to_receive_updates@gmail.com
```

> **Removed 2026-06-16:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are no longer needed. Email is the sole notification channel.

## 💻 Usage

### Run the Full Pipeline
The easiest way to execute the entire workflow (Cleanup -> Live Search & Apply -> Tailor Resumes -> Email Summary).
```bash
python run_pipeline.py
```

### Run Individual Modules
If you want to run specific parts of the project:

- **Only run auto applier**:
  ```bash
  - **Only run auto applier**:
    ```bash
    python auto_applier.py --portal foundit             # single portal, headless
    python auto_applier.py --portal foundit --headful   # single portal, visible browser
    ```
  - **Only tailor resumes**:
    ```bash
    python resume_tailor.py --job-file output/logs/applications_YYYY-MM-DD.json
    ```

## 📂 Outputs
- Execution logs, compiled LaTeX `.tex` and `.pdf` tailored resumes will all be stored safely in the `output/` directory (auto-cleaned after 7 days).

## 🕒️ Cron Setup
- **Scheduled at:** 9:00 AM IST via `jarvis_scheduler.sh` (hour `09`). Standalone cron: `0 9 * * *`.
- **Custom cron:** edit `run_pipeline.py` to suit your needs
