#!/bin/bash
export PATH="$HOME/bin:$PATH"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd /home/venu/Proposals/Jarvis/automations/ecommerce/affiliate-store

# Initialize git if not already done
if [ ! -d ".git" ]; then
  git init
  git branch -M main
fi

# Configure git user
git config user.email "venu@affiliate-store.com"
git config user.name "Venu"

# Add all files and commit
git add .
git commit -m "Initial commit: Zero-cost affiliate storefront"

# Create GitHub repo and push
echo "Creating GitHub repository..."
gh repo create affiliate-store --public --source=. --remote=origin --push

echo "SUCCESS! Repo pushed to GitHub."
gh repo view --web 2>/dev/null || echo "Done! Check github.com/venu0807/affiliate-store"
