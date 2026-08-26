# Python Version & Syntax Compatibility
- **F-String Compatibility (Python <= 3.11):** Never use backslashes or escaped double quotes inside `{...}` f-string expressions (e.g., avoid `f"{d[\"k\"]}"`). Always use single quotes inside double-quoted f-strings (`f"{d['k']}"`) or extract into a local variable before interpolation to ensure 100% compatibility across Python 3.10, 3.11, and CI runners.

# GitHub Actions & CI Pipelines
- **Subdirectory Node.js Builds:** When configuring `actions/setup-node` for Next.js or frontend apps located in subdirectories (e.g. `automations/dashboard-nextjs`), do not specify root `cache: npm` unless `cache-dependency-path` points explicitly to the subfolder's `package-lock.json`. Use `working-directory` with `npm install` and `npm run build` for reliable CI validation.

# Git Hygiene & Repository Safety
- **Large Binary Exclusion:** Never commit vendor/plugin prebuilt binaries (e.g., Grafana plugin binaries, browser binaries). Always verify directory sizes before `git add .` and ensure `.gitignore` excludes binary directories, logs (`logs/`, `*.log*`), lock files, SQLite WAL/SHM files, and Playwright session storage states.

# Autonomous Outreach & Email Routing
- **Direct Recruiter Delivery:** Cold outreach engines must strictly filter and route outbound emails to verified recruiter/HR addresses extracted from postings. Never spam or send job-posting notifications to the candidate's own email inbox.

# WSL2 Memory Architecture & Lifecycle Management
- **.wslconfig Memory Formatting:** Always format memory allocations using whole integer strings (e.g., \memory=3GB\ or \memory=3500MB\). Never use decimals (like \3.5GB\) which cause parsing errors.
- **On-Demand Daemon Control:** Keep heavy daemons (Docker, Redis, PM2, Ollama) disabled from systemd autostart. Always use explicit on-demand start/stop orchestration scripts (\jarvis_boot.sh\ / \jarvis_stop.sh\) to maintain a clean ~150 MB idle baseline.
- **Ollama Memory Reclamation:** Always set \OLLAMA_KEEP_ALIVE=30s\ in environment configurations so local AI models unload from RAM within 30 seconds of task completion.
- **Language Server Hygiene:** Ensure workspace \.vscode/settings.json\ excludes build artifacts (ode_modules\, \.next\, \dist\, \.venv\, \__pycache__\) from file watchers to prevent \language_server_windows_x64\ memory bloat.
