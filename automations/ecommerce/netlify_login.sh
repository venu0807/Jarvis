#!/bin/bash
export PATH="$HOME/bin:$PATH"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd /home/venu/Proposals/Jarvis/automations/ecommerce/affiliate-store

echo "Installing Netlify CLI..."
npm install -g netlify-cli

echo "Logging into Netlify..."
netlify login
