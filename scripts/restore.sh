#!/usr/bin/env bash
# restore.sh — Restore JARVIS from backup
# Usage: ./restore.sh <backup_date> [--secrets] [--postgres] [--jobs] [--configs]

set -euo pipefail

BACKUP_DIR="/home/venu/backups/jarvis"
JARVIS_HOME="/home/venu/Proposals/Jarvis"
JARVIS_SECRETS="/home/venu/.jarvis/.secrets"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_date> [--secrets] [--postgres] [--jobs] [--configs]"
    echo "Example: $0 20260813_030000 --secrets --postgres"
    echo ""
    echo "Available backups:"
    ls -1 "$BACKUP_DIR" 2>/dev/null | grep -E 'jarvis_backup_.*\.(tar\.gz|age|gpg)$' | sed 's/jarvis_backup_\(.*\)\..*/\1/' | sort -u
    exit 1
fi

BACKUP_DATE="$1"
shift

RESTORE_SECRETS=false
RESTORE_POSTGRES=false
RESTORE_JOBS=false
RESTORE_CONFIGS=false

for arg in "$@"; do
    case $arg in
        --secrets) RESTORE_SECRETS=true ;;
        --postgres) RESTORE_POSTGRES=true ;;
        --jobs) RESTORE_JOBS=true ;;
        --configs) RESTORE_CONFIGS=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

# If no specific flags, restore everything
if [ "$RESTORE_SECRETS" = false ] && [ "$RESTORE_POSTGRES" = false ] && \
   [ "$RESTORE_JOBS" = false ] && [ "$RESTORE_CONFIGS" = false ]; then
    RESTORE_SECRETS=true
    RESTORE_POSTGRES=true
    RESTORE_JOBS=true
    RESTORE_CONFIGS=true
fi

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Find backup file (handles .tar.gz, .tar.gz.age, .tar.gz.gpg)
BACKUP_FILE=$(ls "$BACKUP_DIR"/jarvis_backup_"$BACKUP_DATE".* 2>/dev/null | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: No backup found for date: $BACKUP_DATE"
    exit 1
fi

log "Found backup: $(basename "$BACKUP_FILE")"

# Decrypt helper
decrypt() {
    local infile="$1"
    local outfile="$2"
    if [[ "$infile" == *.age ]]; then
        if ! command -v age >/dev/null 2>&1; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: age not installed"
            return 1
        fi
        age --decrypt -i ~/.age/key.txt -o "$outfile" "$infile"
    elif [[ "$infile" == *.gpg ]]; then
        if ! command -v gpg >/dev/null 2>&1; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: gpg not installed"
            return 1
        fi
        gpg --decrypt --output "$outfile" "$infile"
    else
        cp "$infile" "$outfile"
    fi
}

# Extract backup to temp directory
TEMP_ROOT=$(mktemp -d)
log "Extracting backup to $TEMP_ROOT..."

if ! decrypt "$BACKUP_FILE" "$TEMP_ROOT/backup.tar.gz"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Decryption failed"
    rm -rf "$TEMP_ROOT"
    exit 1
fi

if ! tar -xzf "$TEMP_ROOT/backup.tar.gz" -C "$TEMP_ROOT"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Archive extraction failed"
    rm -rf "$TEMP_ROOT"
    exit 1
fi

BACKUP_EXTRACTED="$TEMP_ROOT/$(basename "$BACKUP_FILE" | sed 's/\.tar\.gz.*$//')"

if [ ! -d "$BACKUP_EXTRACTED" ]; then
    # Try finding the extracted directory
    BACKUP_EXTRACTED=$(find "$TEMP_ROOT" -maxdepth 1 -type d -name "jarvis_backup_*" | head -1)
fi

if [ ! -d "$BACKUP_EXTRACTED" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Could not find extracted backup directory"
    rm -rf "$TEMP_ROOT"
    exit 1
fi

log "Backup extracted to: $BACKUP_EXTRACTED"

# Verify manifest
if [ -f "$BACKUP_EXTRACTED/manifest.json" ]; then
    log "Manifest found:"
    cat "$BACKUP_EXTRACTED/manifest.json"
else
    log "WARNING: No manifest.json found"
fi

# 1. Restore secrets
if [ "$RESTORE_SECRETS" = true ] && [ -f "$BACKUP_EXTRACTED/secrets.tar.gz" ]; then
    log "Restoring secrets..."
    TEMP_DIR=$(mktemp -d)
    tar -xzf "$BACKUP_EXTRACTED/secrets.tar.gz" -C "$TEMP_DIR"
    # The archive contains .secrets/ directory
    if [ -d "$TEMP_DIR/.secrets" ]; then
        rsync -a "$TEMP_DIR/.secrets/" "$JARVIS_SECRETS/"
        log "✅ Secrets restored"
    else
        log "WARNING: No .secrets directory in archive"
    fi
    rm -rf "$TEMP_DIR"
fi

# 2. Restore PostgreSQL
if [ "$RESTORE_POSTGRES" = true ] && [ -f "$BACKUP_EXTRACTED/postgres_dump.sql.gz" ]; then
    log "Restoring PostgreSQL..."
    TEMP_DIR=$(mktemp -d)
    gunzip -c "$BACKUP_EXTRACTED/postgres_dump.sql.gz" > "$TEMP_DIR/postgres.sql"
    
    # Ensure database exists
    PGPASSWORD="${JARVIS_DB_PASS:-jarvis}" psql -h localhost -U jarvis -d jarvis < "$TEMP_DIR/postgres.sql" 2>/dev/null || {
        # Try creating database first
        sudo -u postgres psql -c "CREATE USER jarvis WITH PASSWORD 'jarvis';" 2>/dev/null || true
        sudo -u postgres psql -c "CREATE DATABASE jarvis OWNER jarvis;" 2>/dev/null || true
        PGPASSWORD="${JARVIS_DB_PASS:-jarvis}" psql -h localhost -U jarvis -d jarvis < "$TEMP_DIR/postgres.sql"
    }
    rm -rf "$TEMP_DIR"
    log "✅ PostgreSQL restored"
fi

# 3. Restore jobs and sessions
if [ "$RESTORE_JOBS" = true ]; then
    if [ -f "$BACKUP_EXTRACTED/job_automation_output.tar.gz" ]; then
        log "Restoring job automation output..."
        tar -xzf "$BACKUP_EXTRACTED/job_automation_output.tar.gz" -C /home/venu/Proposals/Jarvis/automations/job-automation/
        log "✅ Job automation output restored"
    fi
    if [ -f "$BACKUP_EXTRACTED/job_automation_sessions.tar.gz" ]; then
        log "Restoring job automation sessions..."
        tar -xzf "$BACKUP_EXTRACTED/job_automation_sessions.tar.gz" -C /home/venu/Proposals/Jarvis/automations/job-automation/
        log "✅ Job automation sessions restored"
    fi
fi

# 4. Restore configs
if [ "$RESTORE_CONFIGS" = true ]; then
    log "Restoring configs..."
    # Root level configs
    for file in docker-compose.yml docker-compose.observability.yml jarvis_scheduler.sh policy.py policy.json pyproject.toml alert_config.json loki-config.yml promtail-config.yml grafana-dashboard.json; do
        if [ -f "$BACKUP_EXTRACTED/$file" ]; then
            cp "$BACKUP_EXTRACTED/$file" "$JARVIS_HOME/"
        fi
    done
    # Scripts
    if [ -d "$BACKUP_EXTRACTED/scripts" ]; then
        mkdir -p "$JARVIS_HOME/scripts"
        cp "$BACKUP_EXTRACTED/scripts/"* "$JARVIS_HOME/scripts/" 2>/dev/null || true
    fi
    # Automation configs
    if [ -d "$BACKUP_EXTRACTED/automations" ]; then
        for automation in "$BACKUP_EXTRACTED/automations"/*/; do
            if [ -d "$automation" ]; then
                name=$(basename "$automation")
                mkdir -p "$JARVIS_HOME/automations/$name"
                cp "$automation"/* "$JARVIS_HOME/automations/$name/" 2>/dev/null || true
            fi
        done
    fi
    log "✅ Configs restored"
fi

# Cleanup
rm -rf "$TEMP_ROOT"

log "✅ Restore complete from $BACKUP_DATE"