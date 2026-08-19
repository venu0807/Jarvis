#!/usr/bin/env bash
# backup_jarvis.sh — Daily backup script for JARVIS
# Run via cron: 0 2 * * * /home/venu/Proposals/Jarvis/scripts/backup_jarvis.sh

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/venu/backups/jarvis}"
JARVIS_DIR="${JARVIS_DIR:-/home/venu/Proposals/Jarvis}"
SECRETS_DIR="${SECRETS_DIR:-/home/venu/.jarvis/.secrets}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Encryption (age preferred, fallback to gpg)
ENCRYPT_METHOD="${ENCRYPT_METHOD:-age}"
AGE_KEY_FILE="${AGE_KEY_FILE:-/home/venu/.age/key.txt}"
GPG_KEY_ID="${GPG_KEY_ID:-}"

# Remote upload (rclone)
RCLONE_REMOTE="${RCLONE_REMOTE:-}"
RCLONE_ENABLED="${RCLONE_ENABLED:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $*"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $*"; }

mkdir -p "$BACKUP_DIR"

BACKUP_NAME="jarvis_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
mkdir -p "$BACKUP_PATH"

log "Starting JARVIS backup: $BACKUP_NAME"

log "Backing up secrets..."
if [[ -d "$SECRETS_DIR" ]]; then
    tar -czf "${BACKUP_PATH}/secrets.tar.gz" -C "$(dirname "$SECRETS_DIR")" "$(basename "$SECRETS_DIR")" 2>/dev/null
    log "  ✓ Secrets backed up"
else
    warn "  Secrets directory not found: $SECRETS_DIR"
fi

log "Backing up PostgreSQL database..."
if command -v pg_dump >/dev/null 2>&1; then
    DB_NAME="${JARVIS_DB_NAME:-jarvis}"
    DB_USER="${JARVIS_DB_USER:-jarvis}"
    DB_HOST="${JARVIS_DB_HOST:-localhost}"
    DB_PORT="${JARVIS_DB_PORT:-5432}"

    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "${BACKUP_PATH}/postgres_dump.sql" 2>/dev/null; then
        gzip "${BACKUP_PATH}/postgres_dump.sql"
        log "  ✓ PostgreSQL dumped and compressed"
    else
        warn "  PostgreSQL dump failed"
    fi
else
    warn "  pg_dump not found, skipping database backup"
fi

log "Backing up applied jobs and sessions..."
JOB_AUTO_DIR="${JARVIS_DIR}/automations/job-automation"
if [[ -d "$JOB_AUTO_DIR/output" ]]; then
    tar -czf "${BACKUP_PATH}/job_automation_output.tar.gz" -C "$JOB_AUTO_DIR" output/ 2>/dev/null
    log "  ✓ Job automation output backed up"
fi

if [[ -d "$JOB_AUTO_DIR/.sessions" ]]; then
    tar -czf "${BACKUP_PATH}/job_automation_sessions.tar.gz" -C "$JOB_AUTO_DIR" .sessions/ 2>/dev/null
    log "  ✓ Job automation sessions backed up"
fi

log "Backing up configuration files..."
CONFIG_FILES=(
    "docker-compose.yml"
    "docker-compose.observability.yml"
    "jarvis_scheduler.sh"
    "policy.py"
    "policy.json"
    "pyproject.toml"
    "alert_config.json"
    "loki-config.yml"
    "promtail-config.yml"
    "grafana-dashboard.json"
    "scripts/backup_jarvis.sh"
    "scripts/restore.sh"
)
for file in "${CONFIG_FILES[@]}"; do
    if [[ -f "${JARVIS_DIR}/${file}" ]]; then
        mkdir -p "${BACKUP_PATH}/$(dirname "$file")"
        cp "${JARVIS_DIR}/${file}" "${BACKUP_PATH}/${file}"
    fi
done
log "  ✓ Configuration files backed up"

log "Backing up automation configs..."
for automation in "${JARVIS_DIR}/automations"/*/; do
    if [[ -d "$automation" && ! -d "$automation/__pycache__" ]]; then
        name=$(basename "$automation")
        for file in run.py cron.yaml requirements.txt Dockerfile .env.example README.md; do
            if [[ -f "${automation}/${file}" ]]; then
                mkdir -p "${BACKUP_PATH}/automations/${name}"
                cp "${automation}/${file}" "${BACKUP_PATH}/automations/${name}/"
            fi
        done
    fi
done
log "  ✓ Automation configs backed up"

log "Creating backup manifest..."
cat > "${BACKUP_PATH}/manifest.json" << MANIFEST
{
  "backup_name": "${BACKUP_NAME}",
  "timestamp": "$(date -Iseconds)",
  "jarvis_dir": "${JARVIS_DIR}",
  "secrets_dir": "${SECRETS_DIR}",
  "retention_days": ${RETENTION_DAYS},
  "contents": {
    "secrets": $([ -f "${BACKUP_PATH}/secrets.tar.gz" ] && echo true || echo false),
    "postgres": $([ -f "${BACKUP_PATH}/postgres_dump.sql.gz" ] && echo true || echo false),
    "job_automation_output": $([ -f "${BACKUP_PATH}/job_automation_output.tar.gz" ] && echo true || echo false),
    "job_automation_sessions": $([ -f "${BACKUP_PATH}/job_automation_sessions.tar.gz" ] && echo true || echo false),
    "config_files": true,
    "automation_configs": true
  }
}
MANIFEST

log "Creating final archive..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
rm -rf "${BACKUP_NAME}"
log "  ✓ Final archive created: ${BACKUP_NAME}.tar.gz"

log "Encrypting backup..."
ENCRYPTED_FILE=""
if [[ "$ENCRYPT_METHOD" == "age" ]] && command -v age >/dev/null 2>&1 && [[ -f "$AGE_KEY_FILE" ]]; then
    age -r "$(cat "$AGE_KEY_FILE" | grep -v '^#' | head -1 | cut -d' ' -f1)" \
        -o "${BACKUP_NAME}.tar.gz.age" "${BACKUP_NAME}.tar.gz"
    ENCRYPTED_FILE="${BACKUP_NAME}.tar.gz.age"
    rm "${BACKUP_NAME}.tar.gz"
    log "  ✓ Encrypted with age"
elif [[ "$ENCRYPT_METHOD" == "gpg" ]] && command -v gpg >/dev/null 2>&1 && [[ -n "$GPG_KEY_ID" ]]; then
    gpg --encrypt --recipient "$GPG_KEY_ID" --output "${BACKUP_NAME}.tar.gz.gpg" "${BACKUP_NAME}.tar.gz"
    ENCRYPTED_FILE="${BACKUP_NAME}.tar.gz.gpg"
    rm "${BACKUP_NAME}.tar.gz"
    log "  ✓ Encrypted with GPG"
else
    warn "  Encryption skipped (no age key or GPG key configured)"
    ENCRYPTED_FILE="${BACKUP_NAME}.tar.gz"
fi

log "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "jarvis_backup_*.tar.gz*" -mtime +${RETENTION_DAYS} -delete
log "  ✓ Cleanup complete"

if [[ "$RCLONE_ENABLED" == "true" && -n "$RCLONE_REMOTE" ]] && command -v rclone >/dev/null 2>&1; then
    log "Uploading to remote storage ($RCLONE_REMOTE)..."
    if rclone copy "${BACKUP_DIR}/${ENCRYPTED_FILE}" "$RCLONE_REMOTE" 2>&1; then
        log "  ✓ Upload complete"
    else
        error "  Upload failed"
    fi
else
    log "Remote upload skipped (not configured)"
fi

SIZE=$(du -h "${BACKUP_DIR}/${ENCRYPTED_FILE}" | cut -f1)
log "Backup complete: ${ENCRYPTED_FILE} (${SIZE})"

log "=== BACKUP COMPLETE ==="