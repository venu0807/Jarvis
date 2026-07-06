#!/bin/bash
export PATH="$HOME/bin:$PATH"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "Logging into GitHub..."
gh auth login --web --hostname github.com --git-protocol https
