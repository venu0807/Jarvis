# Your Automated Pinterest Bot

This bot is fully set up on your computer to automatically generate aesthetic Pinterest Pins for Amazon products and upload them to your Pinterest account!

## How to use it

### 1. Get your API Keys (One-time setup)
You need to give the bot permission to post to your Pinterest.
1. Go to [developers.pinterest.com](https://developers.pinterest.com/) and log in with your Pinterest account.
2. Click **Create App**. (You can name it "My Auto Poster").
3. Under your new app, generate an **Access Token** with permissions to `boards:read` and `pins:write`.
4. Open the file `.env.example` in this folder, rename it to `.env`, and paste your token inside.
5. You also need your `PINTEREST_BOARD_ID`. You can get this by going to your board on Pinterest, and the ID is a long number in the URL or page source. Put this in `.env` as well.

### 2. Add your Products
1. Open the file `data.csv`.
2. Add your Amazon product names, the direct link to their images, and your Amazon affiliate links.
3. Save the file.

### 3. Run the Bot!
Whenever you want the bot to run through your spreadsheet and post everything that hasn't been pinned yet, just open PowerShell and type:

```powershell
cd $env:USERPROFILE\.jarvis\automations\pinterest
.\venv\Scripts\activate
python main.py
```

The bot will automatically download the product images, crop them onto the beautiful aesthetic background, write the title in bold font, and upload it to Pinterest with your link!
