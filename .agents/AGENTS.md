# Jarvis Operating System Architecture

- **UI Framework:** Streamlit is permanently deprecated for the Jarvis dashboard. All UI work must be done in the unified Next.js 14 application located at `~/Proposals/Jarvis/automations/dashboard-nextjs`.
- **Aesthetic Standards:** Any new components added to the Next.js dashboard must adhere to the premium "dark-mode glassmorphism" aesthetic defined in `globals.css` (e.g., using radial gradients, glowing cyan accents, and translucent panels).
- **Database Security:** Never hardcode PostgreSQL or SQLite credentials in source code. All Node.js/Next.js database connections must read from `.env.local`.
- **Remote Command Center:** The `imap_scanner.py` script in `inbox-monitor` is not just for scraping recruiters; it acts as Jarvis's remote control. If you add new automations, ensure they can be triggered remotely by adding a new `JARVIS: <COMMAND>` parser in the IMAP scanner.
- **Cron Wakeup:** Remember that WSL `cron` does not start on boot. If debugging scheduling issues, always verify that `sudo service cron start` has been executed.

# Startup & Shutdown Architecture

- **Invisible Auto-Boot:** Jarvis starts 100% invisibly when Windows boots. This is handled by a silent VBS script in the Windows Startup folder that triggers `/home/venu/Proposals/Jarvis/automations/jarvis_boot.sh` inside WSL. Never create visible `.bat` files for the auto-boot sequence.
- **Decoupled Desktop Controls:** The system is split into two modules to save RAM and battery:
  1. **Heavy Engine (UI & Database):** Docker (PostgreSQL) and the Next.js Dashboard. These consume ~3GB of RAM and should be stoppable via `Stop UI & Database.bat` (which calls `jarvis_stop_heavy.sh`).
  2. **Core Brain (Listeners):** Cron (handles the 15-min Inbox Monitor) and the Python Email Listener. These are extremely lightweight and MUST be left running in the background all day so recruiter emails are never missed.
- **Rule:** Never modify the desktop stop scripts to kill the Core Brain listeners unless the user explicitly requests a total shutdown (via `Stop EVERYTHING.bat`).
