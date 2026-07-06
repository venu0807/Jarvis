#!/bin/bash
export PATH="$HOME/bin:$PATH"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
export NETLIFY_AUTH_TOKEN="nfp_uRj7tbHAM8jaqYeqxURS3np8yQQ1QPdp5249"
SITE_ID="27f6f6c6-1511-4dd8-abea-4b28b27064a7"

cd /home/venu/Proposals/Jarvis/automations/ecommerce/affiliate-store

echo "Removing old build..."
rm -rf out .next

echo "Building fresh static export..."
npm run build

echo "Zipping output folder using Python..."
python3 -c "
import zipfile, os

out_dir = 'out'
zip_path = '/tmp/affiliate-store.zip'

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(out_dir):
        for file in files:
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, out_dir)
            zf.write(filepath, arcname)

print(f'Zip created: {zip_path} ({os.path.getsize(zip_path)} bytes)')
"

echo "Uploading to Netlify..."
DEPLOY_RESPONSE=$(curl -s -X POST \
  "https://api.netlify.com/api/v1/sites/$SITE_ID/deploys" \
  -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary @/tmp/affiliate-store.zip)

DEPLOY_STATE=$(echo "$DEPLOY_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state','unknown'))" 2>/dev/null)
echo ""
echo "=========================================="
echo "Deploy state: $DEPLOY_STATE"
echo "LIVE URL: https://affiliate-store-venu.netlify.app"
echo "=========================================="
