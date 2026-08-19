#!/usr/bin/env bash
# backup.sh — Daily encrypted backup for JARVIS
# Run via cron: 0 3 * * * /home/venu/Proposals/Jarvis/scripts/backup.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/home/venu/Proposals/Jarvis/backups"
JARVIS_HOME="/home/venu/Proposals/Jarvis"
JARVIS_SECRETS="/home/venu/.jarvis/.secrets"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Encryption (uses age - modern encryption)
AGE_RECIPIENT="${BACKUP_AGE_RECIPIENT:-}"  # Set in environment

# Logging
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "$BACKUP_DIR"

log "Starting JARVIS backup: $DATE"

# 1. Backup secrets (encrypted)
log "Backing up secrets..."
SECRETS_BACKUP="$BACKUP_DIR/secrets_$DATE.tar.gz"
tar -czf - -C "$JARVIS_SECRETS" . | \
    age -r "$AGE_RECIPIENT" > "$SECRETS_BACKUP.age" 2>/dev/null || \
    gpg --symmetric --cipher-algo AES256 --output "$SECRETS_BACKUP.gpg" "$SECRETS_BACKUP"
rm -f "$SECRETS_BACKUP"

# 2. Backup PostgreSQL (applied_jobs, events, metrics)
log "Backing up PostgreSQL..."
PG_BACKUP="$BACKUP_DIR/postgres_$DATE.sql"
PGPASSWORD="${JARVIS_DB_PASS}" pg_dump -h localhost -U jarvis -d jarvis \
    --no-owner --no-acl --clean --if-exists > "$PG_BACKUP"
age -r "$AGE_RECIPIENT" -o "$PG_BACKUP.age" "$PG_BACKUP" 2>/dev/null || \
    gpg --symmetric --cipher-algo AES256 --output "$PG_BACKUP.gpg" "$PG_BACKUP"
rm -f "$PG_BACKUP"

# 3. Backup applied_jobs.json + session files
log "Backing up applied jobs and sessions..."
JOBS_BACKUP="$BACKUP_DIR/jobs_sessions_$DATE.tar.gz"
tar -czf - \
    -C /home/venu/Proposals/Jarvis/automations/job-automation/output/logs applied_jobs.json \
    -C /home/venu/Proposals/Jarvis/automations/job-automation .sessions \
    2>/dev/null | age -r "$AGE_RECIPIENT" > "$JOBS_BACKUP.age"

# 4. Backup configs (docker-compose, configs, scripts)
log "Backing up configs..."
CONFIG_BACKUP="$BACKUP_DIR/configs_$DATE.tar.gz"
tar -czf - \
    -C "$JARVIS_HOME" \
    docker-compose.yml docker-compose.observability.yml \
    jarvis_scheduler.sh \
    automations/alert_config.json \
    automations/alert.env.example \
    .github/workflows/ci.yml \
    2>/dev/null | age -r "$AGE_RECIPIENT" > "$CONFIG_BACKUP.age"

# 5. Encrypt all with age (if recipient set) or gpg fallback
log "Encrypting backups..."
for f in "$BACKUP_DIR"/*_"$DATE".tar.gz; do
    if [ -f "$f" ]; then
        if [ -n "$AGE_RECIPIENT" ]; then
            age -r "$AGE_RECIPIENT" -o "$f.age" "$f" && rm "$f"
        else
            gpg --symmetric --cipher-algo AES256 --output "$f.gpg" "$f" && rm "$f"
        fi
    fi
done

# 6. Cleanup old backups
log "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -name "*.age" -o -name "*.gpg" -mtime +$RETENTION_DAYS -delete

# 7. Verify backup integrity
log "Verifying backup..."
if [ -n "$AGE_RECIPIENT" ]; then
    age --decrypt -i ~/.age/key.txt -o /dev/null "$BACKUP_DIR/secrets_$DATE.tar.gz.age" 2>/dev/null && log "✅ Secrets backup verified"
else
    gpg --decrypt --output /dev/null "$BACKUP_DIR/secrets_$DATE.tar.gz.gpg" 2>/dev/null && log "✅ Secrets backup verified"
fi

log "Backup complete: $DATE"
log "Backup location: $BACKUP_DIR"

# Optional: Upload to cloud (uncomment and configure)
# rclone copy "$BACKUP_DIR" remote:jarvis-backups/$(hostname)/ --max-age 24h

exit 0