# Runbook: WSL Corruption Recovery

## Overview
WSL (Windows Subsystem for Linux) filesystem corruption or Windows update breaking WSL, resulting in total loss of `/home/venu` environment. Recovery from daily encrypted backups.

## Symptoms
- WSL fails to start: `wsl.exe` hangs or returns error
- "The file or directory is corrupted and unreadable"
- Ubuntu shows "Unexpected error" on launch
- Windows update completed recently
- Cannot access `/home/venu/Proposals/Jarvis` or `~/.jarvis`

## Prerequisites (Must Have Before Disaster)
- ✅ Daily backup running: `backup_jarvis.sh` at 2 AM (cron)
- ✅ Backups stored externally (GitHub releases, S3/GDrive via rclone)
- ✅ Restore script tested monthly: `restore.sh`
- ✅ Age/GPG encryption keys backed up separately
- ✅ This runbook accessible outside WSL (GitHub, printed, OneNote)

## Recovery Options (In Order of Preference)

### Option 1: WSL Repair (Fastest, Try First)
```powershell
# In PowerShell as Administrator
wsl --shutdown
wsl --update
# If that fails:
dism.exe /online /cleanup-image /restorehealth
sfc /scannow
# Then restart PC and try wsl again
```

### Option 2: WSL Reset (Keeps User Data)
```powershell
# In PowerShell as Administrator
wsl --terminate Ubuntu
wsl --unregister Ubuntu  # WARNING: This DELETES the WSL instance!
# Then reinstall from Microsoft Store
```

### Option 3: Full WSL Reinstall + Restore from Backup (Complete Recovery)

#### Step 1: Install Fresh WSL
```powershell
# In PowerShell as Administrator
wsl --install -d Ubuntu
# Or if already installed:
wsl --unregister Ubuntu
wsl --install -d Ubuntu
```
- Complete Ubuntu setup (create user `venu`, password)
- Note: New WSL will have fresh `/home/venu`

#### Step 2: Restore JARVIS from Backup

**A. Get Latest Backup**
```bash
# If backups on GitHub (via rclone/github releases):
# Download latest jarvis_backup_*.tar.gz from GitHub releases
# Or from S3/GDrive if configured

# If backups on Windows side (accessible via /mnt/c):
ls /mnt/c/backups/jarvis/
# Or wherever you configured BACKUP_DIR
```

**B. Run Restore Script**
```bash
# In fresh WSL Ubuntu
cd /home/venu
# Extract backup
tar -xzf /path/to/jarvis_backup_YYYYMMDD_HHMMSS.tar.gz

# Run restore (restores everything by default)
cd /home/venu/Proposals/Jarvis/scripts
chmod +x restore.sh
./restore.sh YYYYMMDD_HHMMSS --secrets --postgres --jobs --configs
```

**C. Manual Restore Steps (If Script Fails)**
```bash
# 1. Restore secrets
tar -xzf /backup/path/secrets.tar.gz -C /home/venu/.jarvis/

# 2. Restore PostgreSQL
# First ensure PostgreSQL is running
sudo systemctl start postgresql
# Create database/user if needed
sudo -u postgres psql -c "CREATE USER jarvis WITH PASSWORD 'jarvis';"
sudo -u postgres psql -c "CREATE DATABASE jarvis OWNER jarvis;"
# Restore dump
gunzip -c /backup/path/postgres_dump.sql.gz | psql -h localhost -U jarvis -d jarvis

# 3. Restore job automation data
tar -xzf /backup/path/job_automation_output.tar.gz -C /home/venu/Proposals/Jarvis/automations/job-automation/
tar -xzf /backup/path/job_automation_sessions.tar.gz -C /home/venu/Proposals/Jarvis/automations/job-automation/

# 4. Restore configs
cp /backup/path/*.yml /home/venu/Proposals/Jarvis/
cp /backup/path/*.json /home/venu/Proposals/Jarvis/
cp /backup/path/*.sh /home/venu/Proposals/Jarvis/
```

#### Step 3: Reinstall Dependencies
```bash
# System packages
sudo apt-get update
sudo apt-get install -y postgresql postgresql-client python3-pip docker.io docker-compose cron

# Python packages (if using conda)
# Restore miniconda or use system python
# If conda was backed up, restore ~/.conda
# Otherwise reinstall miniconda and create env

# Node.js (if needed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Age/GPG for decrypting backups
sudo apt-get install -y age gpg
```

#### Step 4: Restore Cron & Services
```bash
# Restore crontab
crontab /home/venu/Proposals/Jarvis/scripts/crontab_backup
# Or manually add from runbook

# Enable systemd services
sudo systemctl enable postgresql cron docker
sudo systemctl start postgresql cron docker

# If observability stack was running as systemd
sudo systemctl enable loki promtail grafana-server
sudo systemctl start loki promtail grafana-server
```

#### Step 5: Verify Recovery
```bash
# Test database
psql -h localhost -U jarvis -d jarvis -c "SELECT count(*) FROM applied_jobs;"

# Test automation
cd /home/venu/Proposals/Jarvis/automations/job-automation
/home/venu/miniconda3/bin/python3 run_pipeline.py

# Check logs
tail -f /home/venu/Proposals/Jarvis/automations/jarvis_cron.log

# Test alerts
cd /home/venu/Proposals/Jarvis/automations
/home/venu/miniconda3/bin/python3 alert_triggers.py

# Test backup
/home/venu/Proposals/Jarvis/scripts/backup_jarvis.sh
```

## Backup Location Strategy

### Primary: GitHub Releases (Free, Versioned)
```bash
# In backup_jarvis.sh, uncomment and configure:
# gh release create "backup-$(date +%Y%m%d)" jarvis_backup_*.tar.gz --repo youruser/jarvis-backups
```

### Secondary: S3 / GDrive via rclone
```bash
# Configure rclone
rclone config
# Then in backup_jarvis.sh:
# rclone copy ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz remote:jarvis-backups/
```

### Tertiary: Windows Side (Accessible Even If WSL Dead)
```bash
# BACKUP_DIR="/mnt/c/backups/jarvis"  # In backup_jarvis.sh
# This survives WSL corruption!
```

## Monthly Restore Test (Critical!)
```bash
# Run on 1st of every month (add to cron)
# 0 4 1 * * /home/venu/Proposals/Jarvis/scripts/test_restore.sh

# test_restore.sh content:
#!/bin/bash
set -e
BACKUP_DIR="/home/venu/backups/jarvis"
LATEST=$(ls -t $BACKUP_DIR/jarvis_backup_*.tar.gz | head -1)
TEST_DIR="/tmp/jarvis_restore_test_$(date +%s)"
mkdir -p $TEST_DIR
cd $TEST_DIR
tar -xzf $LATEST
# Verify manifest exists
test -f jarvis_backup_*/manifest.json && echo "✅ Backup valid" || echo "❌ Backup corrupt"
# Cleanup
rm -rf $TEST_DIR
```

## Key Files to Backup Separately (Not in Automated Backup)
- Age private key: `~/.age/key.txt` (for decrypting backups)
- GPG private key: `~/.gnupg/` (if using GPG)
- SSH keys: `~/.ssh/`
- This runbook (store in GitHub, OneNote, printed)

## Timeline Expectations
- WSL Repair: 5-15 minutes
- WSL Reset + Restore: 30-60 minutes
- Full Reinstall + Restore: 60-90 minutes

## Post-Recovery Checklist
- [ ] All 13 automations running
- [ ] Cron jobs executing (check jarvis_cron.log)
- [ ] Alerts firing (test with `python3 alert_triggers.py`)
- [ ] Telegram bot responding (/status, /health)
- [ ] Grafana dashboard showing data (http://localhost:3000)
- [ ] Backup script working (run manually)
- [ ] Secret rotation cron scheduled
- [ ] PostgreSQL data intact (check applied_jobs count)

## Escalation
If all recovery options fail:
1. Check Windows Event Viewer for WSL errors
2. Try `wsl --mount` to access VHDX directly
3. Contact Microsoft Support (WSL is a Windows component)
4. Last resort: Rebuild from scratch using GitHub repo + this runbook

## Related Files
- `/home/venu/Proposals/Jarvis/scripts/backup_jarvis.sh`
- `/home/venu/Proposals/Jarvis/scripts/restore.sh`
- `/home/venu/Proposals/Jarvis/scripts/crontab_reference`
- `/home/venu/Proposals/Jarvis/automations/alert_triggers.py`
- GitHub repo: `https://github.com/youruser/Jarvis`