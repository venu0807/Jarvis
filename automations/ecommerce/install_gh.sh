#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "Installing GitHub CLI to user home bin..."
mkdir -p "$HOME/bin"
GH_VERSION="2.49.2"
curl -L "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" -o /tmp/gh.tar.gz
tar -xzf /tmp/gh.tar.gz -C /tmp
cp /tmp/gh_${GH_VERSION}_linux_amd64/bin/gh "$HOME/bin/gh"
chmod +x "$HOME/bin/gh"
rm -rf /tmp/gh.tar.gz /tmp/gh_${GH_VERSION}_linux_amd64
export PATH="$HOME/bin:$PATH"
echo "Done! GitHub CLI version: $($HOME/bin/gh --version)"
