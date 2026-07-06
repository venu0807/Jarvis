#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
cd /home/venu/Proposals/Jarvis/automations/pinterest
echo -e "pvgreddy3@gmail.com\nVenureddy@123\n" | npx surge ./bio venu-deals-hub.surge.sh
