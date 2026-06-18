"""
Bio Page Deploy Helper — Free hosting setup for the bio link page.

Three free options to host the bio link page:
1. GitHub Pages (most reliable, free, custom domain possible)
2. Netlify Drop (drag-and-drop, instant)
3. Surge.sh (terminal-only, 1 command)

After hosting, paste the URL into your TikTok / Instagram / YouTube bio.

Usage:
  python deploy_bio.py github <github-username>   # creates/updates GitHub repo
  python deploy_bio.py surge                      # surge.sh quick deploy
  python deploy_bio.py netlify                    # opens drag-and-drop page
  python deploy_bio.py guide                      # print deployment guide
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


BIO_DIR = "bio"
DEPLOY_DIR = "bio_deploy"


def _setup_deploy_dir():
    """Copy bio/index.html into a single-file deploy dir."""
    os.makedirs(DEPLOY_DIR, exist_ok=True)
    src = os.path.join(BIO_DIR, "index.html")
    if not os.path.exists(src):
        print(f"  ❌ {src} not found. Run: python main.py bio")
        sys.exit(1)
    shutil.copy(src, os.path.join(DEPLOY_DIR, "index.html"))
    print(f"  📁 Copied to: {DEPLOY_DIR}/index.html")


def deploy_github(username: str):
    """Create a GitHub Pages repo for the bio page."""
    print(f"\n  🐙 GitHub Pages deployment")
    print(f"  ─────────────────────────")

    bio_username = username.strip().lower()
    if not bio_username:
        print("  ❌ Username required: python deploy_bio.py github <username>")
        return

    repo_name = "bio"  # username.github.io/bio
    bio_url = f"https://{bio_username}.github.io/{repo_name}/"

    print(f"  📦 Repo: {bio_username}/{repo_name}")
    print(f"  🌐 URL: {bio_url}")

    # Initialize git repo
    cwd = os.path.abspath(DEPLOY_DIR)
    if not os.path.exists(os.path.join(cwd, ".git")):
        _setup_deploy_dir()
        os.chdir(cwd)
        subprocess.run(["git", "init"], check=False)
        subprocess.run(["git", "branch", "-M", "main"], check=False)
        subprocess.run(
            ["git", "add", "index.html"], check=False
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial bio page"], check=False
        )

    print(f"\n  ✅ Next steps:")
    print(f"     1. Create empty repo at: github.com/new → name: {repo_name}")
    print(f"     2. Run these commands from {DEPLOY_DIR}/:")
    print(f"        git remote add origin https://github.com/{bio_username}/{repo_name}.git")
    print(f"        git push -u origin main")
    print(f"     3. Settings → Pages → Source: main → Save")
    print(f"     4. URL will be live: {bio_url}")
    print(f"     5. Add {bio_url} to your TikTok / IG / YouTube bio")


def deploy_surge():
    """Deploy via surge.sh (terminal-only)."""
    print(f"\n  ⚡ Surge.sh deployment")
    print(f"  ─────────────────────")

    _setup_deploy_dir()

    # Check if surge is installed
    if not shutil.which("surge"):
        print("  ⚠️  surge not installed. Install with: npm install -g surge")
        print("     (requires Node.js)")
        return

    print(f"  ✅ Run this command:")
    print(f"     cd {DEPLOY_DIR}")
    print(f"     surge . student-bio-page.surge.sh")
    print(f"  📝 First time: enter email + create password")


def deploy_netlify():
    """Open Netlify Drop page for drag-and-drop."""
    print(f"\n  🟢 Netlify Drop deployment")
    print(f"  ─────────────────────────")
    _setup_deploy_dir()

    drag_path = os.path.abspath(DEPLOY_DIR)
    print(f"  1. Open: https://app.netlify.com/drop")
    print(f"  2. Drag this folder: {drag_path}")
    print(f"  3. Get instant URL like: https://random-name-123.netlify.app")
    print(f"  4. (Optional) Rename site in Netlify dashboard")


def print_guide():
    """Print high-level guide for all options."""
    print("""
  ╔════════════════════════════════════════════════════════╗
  ║         BIO PAGE HOSTING — 3 FREE OPTIONS              ║
  ╠════════════════════════════════════════════════════════╣

  🥇 Best: GitHub Pages (free + custom domain + reliable)
     • Drag the bio_deploy/ folder to github.com → new repo
     • Enable Pages in repo Settings
     • URL: yourname.github.io/bio

  🥈 Fastest: Netlify Drop (drag-and-drop, no signup needed)
     • app.netlify.com/drop
     • Drag bio_deploy/ folder
     • Get instant URL

  🥉 Terminal: Surge.sh (1 command)
     • npm install -g surge
     • cd bio_deploy && surge .

  ─────────────────────────────────────────────────────────
  STEP 1: Generate bio page:
     python main.py bio

  STEP 2: Run helper:
     python deploy_bio.py github yourname
     python deploy_bio.py netlify
     python deploy_bio.py surge

  STEP 3: Copy resulting URL into TikTok / IG / YouTube bio

  STEP 4: Re-deploy after every product update:
     python main.py bio && python deploy_bio.py github yourname
""")


# ── CLI ──────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "guide":
        print_guide()
    elif sys.argv[1] == "github":
        username = sys.argv[2] if len(sys.argv) > 2 else ""
        deploy_github(username)
    elif sys.argv[1] == "surge":
        deploy_surge()
    elif sys.argv[1] == "netlify":
        deploy_netlify()
    else:
        print(f"  Unknown command: {sys.argv[1]}")
        print("  Try: python deploy_bio.py guide")
