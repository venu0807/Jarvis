#!/bin/bash

echo "👻 Initializing Jarvis Ghost Protocol..."

CRON_FILE="/tmp/jarvis_cron"
crontab -l > $CRON_FILE 2>/dev/null || true

# Remove old jarvis entries to prevent duplicates
sed -i '/Jarvis Ghost Protocol/d' $CRON_FILE
sed -i '/imap_scanner.py/d' $CRON_FILE
sed -i '/run_pipeline.py/d' $CRON_FILE

echo "# Jarvis Ghost Protocol" >> $CRON_FILE
echo "*/15 * * * * cd /home/venu/Proposals/Jarvis/automations/inbox-monitor && /usr/bin/python3 imap_scanner.py >> /home/venu/Proposals/Jarvis/automations/jarvis_cron.log 2>&1" >> $CRON_FILE
echo "0 9 * * * cd /home/venu/Proposals/Jarvis/automations/job-automation && /usr/bin/python3 run_pipeline.py >> /home/venu/Proposals/Jarvis/automations/jarvis_cron.log 2>&1" >> $CRON_FILE

crontab $CRON_FILE
rm $CRON_FILE

echo "✅ Ghost Protocol activated!"
echo "   - Inbox Monitor runs every 15 minutes."
echo "   - Job Applier runs daily at 9:00 AM."
echo ""
echo "⚠️  Note: Since you are using WSL, the cron daemon might not start automatically when you boot Windows."
echo "   Run this command once per reboot to ensure the Ghost Protocol is running:"
echo "   sudo service cron start"
