#!/bin/bash
service postgresql start

cp /mnt/c/Users/Venu/Proposals/Jarvis/automations/pinterest/aesthetic_blender.py /home/venu/Proposals/Jarvis/automations/pinterest/aesthetic_blender.py
chown venu:venu /home/venu/Proposals/Jarvis/automations/pinterest/aesthetic_blender.py

su - venu -c '
cd /home/venu/Proposals/Jarvis/automations/pinterest
source venv/bin/activate

echo "=== 1. DASHBOARD ==="
python dashboard.py

echo "=== 2. AUTO BLOGGER ==="
python blog_generator.py

echo "=== 3. VIRAL REPINNER ==="
python repin_old.py

echo "=== 4. AESTHETIC BLENDER ==="
python aesthetic_blender.py
'
