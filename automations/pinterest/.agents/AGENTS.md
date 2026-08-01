# Pinterest Bot Architecture & Persistence
- **PostgreSQL over CSV:** The Pinterest automation bot uses a local PostgreSQL database (`pinterest_db` -> `products` table) as its primary source of truth, not just `data.csv`. If you need to make bulk updates (like changing an affiliate tag), you MUST execute SQL queries against the database in addition to modifying any flat files.
- **Hardcoded Variables:** When debugging configuration issues (like wrong tags or paths), always check the core scraping scripts (e.g., `amazon_scraper.py`, `bio_page.py`) for hardcoded constants that might be overriding the `.env` file.

# WSL & Database Services
- **Service Lifecycles:** When running the bot or interacting with the database via `wsl -d Ubuntu bash -c "..."`, always remember that `postgresql` might not be running (especially after a system reboot or `wsl --shutdown`). Prepend commands with `sudo service postgresql start &&` to prevent `Connection refused` errors.
- **Currency Conversion:** Amazon scraping in this environment defaults to pulling `INR` pricing due to geolocation. The pipeline requires runtime conversion to USD using regex and a live exchange rate before passing prices to image/video generators.
