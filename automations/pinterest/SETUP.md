# =========================================
# PINTEREST AFFILIATE BOT — SETUP GUIDE
# =========================================

## STEP 1: Install Dependencies
Open PowerShell and run:
```
pip install -r requirements.txt
playwright install chromium
```

## STEP 2: Configure .env
Open `.env` (or copy from `.env.example`) and fill in:

```
PINTEREST_ACCESS_TOKEN=your_pinterest_access_token_here
PINTEREST_BOARD_ID=your_pinterest_board_id_here
AMAZON_AFFILIATE_TAG=your_amazon_tag_here
```

- **PINTEREST_ACCESS_TOKEN**: Get from https://developers.pinterest.com/
  (Create App → Generate Token with pins:write, pins:read, boards:read)
  → If not approved yet, browser fallback will be used automatically!

- **PINTEREST_BOARD_ID**: Run `python get_boards.py` after setting the token

- **AMAZON_AFFILIATE_TAG**: Get from https://affiliate-program.amazon.com/
  (Sign up → Your tag looks like: yourstore-20)

## STEP 3: Populate Products
```
python main.py refill
```
This adds 25+ products + 12 content pin templates to data.csv.

## STEP 4: Post Your First Pins!
```
python main.py run
```
First time → a browser will open. Log into Pinterest ONCE.
After that, your session is saved for future runs.

## COMMANDS
| Command | What it does |
|---------|-------------|
| `python main.py run` | Post pending pins (20 per run) |
| `python main.py run --count 5` | Post only 5 pins |
| `python main.py run --category tech` | Post only tech products |
| `python main.py refill` | Add more products to CSV |
| `python main.py stats` | Show stats dashboard |
| `python main.py schedule` | Post at optimal times all day |

## SCHEDULE DAILY RUNS
```
schtasks /create /tn "PinterestBot" /tr "C:\Users\Venu\.jarvis\automations\pinterest\run_daily.bat" /sc daily /st 07:00
```

## EARNING STRATEGY
- Post 20-40 pins daily (4x more = 4x earnings)
- Focus on trending categories (tech, dorm decor)
- Add your own products to data.csv
- Run the bot daily for 30 days to see real results!
