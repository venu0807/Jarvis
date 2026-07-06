#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
cd /home/venu/Proposals/Jarvis/automations/ecommerce
npx -y create-next-app@latest affiliate-store --typescript --tailwind --eslint --app --src-dir --import-alias '@/*' --use-npm
