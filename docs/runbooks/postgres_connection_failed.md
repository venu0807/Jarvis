# Runbook: PostgreSQL Connection Failed

## Overview
PostgreSQL database becomes unreachable, affecting all automations that depend on it (job tracking, metrics, event bus).

## Symptoms
- "could not connect to server: Connection refused" errors in logs
- Automation jobs fail to start or crash during execution
- Metrics dashboard shows no new data
- Event bus stops processing events
- Alert triggered: "PostgreSQL connection failures"
- `/health` endpoint shows database unhealthy

## Impact
- Job application tracking ceases (applied_jobs table not updated)
- Metrics collection stops (no new events stored)
- Event-driven automations fail to trigger
- Historical data remains accessible but no new data can be written
- Potential data loss if automations retry without persistence

## Immediate Actions
1. **Verify PostgreSQL service status**:
   ```bash
   sudo systemctl status postgresql
   ```

2. **Check if PostgreSQL is listening on port 5432**:
   ```bash
   sudo ss -tlnp | grep 5432
   # or
   sudo netstat -tlnp | grep 5432
   ```

3. **Attempt manual connection**:
   ```bash
   PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT version();"
   ```

4. **Check PostgreSQL logs for errors**:
   ```bash
   sudo journalctl -u postgresql --since "1 hour ago"
   # or
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```

5. **Restart PostgreSQL service**:
   ```bash
   sudo systemctl restart postgresql
   ```

6. **Verify connection after restart**:
   ```bash
   PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT 1;"
   ```

## Common Causes & Solutions

### 1. PostgreSQL Service Not Running
**Symptoms**: `Connection refused` on port 5432
**Solution**:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Ensure it starts on boot
```

### 2. Authentication Failure
**Symptoms**: `password authentication failed for user "jarvis"`
**Solution**:
- Check password in `~/.jarvis/.secrets/`
- Reset password if needed:
  ```bash
  sudo -u postgres psql -c "ALTER USER jarvis WITH PASSWORD 'new_password';"
  ```
- Update secrets: `python3 -c "from automations.secrets_manager import SecretsManager; s=SecretsManager('local'); s.set_secret('jarvis_db_password', 'new_password')"`

### 3. Database Corruption
**Symptoms**: Service starts but queries fail with segmentation faults or disk full errors
**Solution**:
- Check disk space: `df -h`
- Check PostgreSQL logs for specific error messages
- May require `pg_resetwal` or restore from backup

### 4. Connection Limit Exceeded
**Symptoms**: `too many connections for role "jarvis"`
**Solution**:
- Check current connections: `SELECT * FROM pg_stat_activity;`
- Increase max_connections in `/etc/postgresql/*/main/postgresql.conf`
- Restart service after change

### 5. Network/Firewall Issues
**Symptoms**: Connection timeout or refused from specific interfaces
**Solution**:
- Check firewall: `sudo ufw status` or `sudo iptables -L`
- Ensure localhost connections are allowed
- Verify `listen_addresses` in postgresql.conf includes localhost

## Verification
1. PostgreSQL service is active: `sudo systemctl is-active postgresql`
2. Accepting connections: `PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT 1;"` returns `1`
3. Automation jobs can run and write to database
4. Metrics dashboard shows updating data
5. Alert triggers clear (no more database connection alerts)

## Prevention
- Monitor disk usage on database partition
- Set up database connection pooling if needed
- Regular vacuum and analyze maintenance
- Monitor connection counts and query performance
- Set up database alerts for slow queries or high utilization
- Consider implementing read replicas for heavy read workloads

## Backup & Recovery
If database corruption occurs:
1. Stop PostgreSQL: `sudo systemctl stop postgresql`
2. Backup current data directory: `sudo cp -r /var/lib/postgresql/* /tmp/pg_backup_$(date +%s)`
3. Attempt recovery using pg_walreplay or restore from base backup
4. If recovery fails, restore from latest backup:
   ```bash
   # Stop service
   sudo systemctl stop postgresql
   
   # Clear data directory
   sudo rm -rf /var/lib/postgresql/*/main/*
   
   # Restore from backup (adjust path as needed)
   sudo cp -r /home/venu/backups/jarvis/*/postgres_dump.sql.gz /tmp/
   sudo gunzip /tmp/postgres_dump.sql.gz
   
   # Create fresh database
   sudo -u postgres initdb -D /var/lib/postgresql/*/main
   
   # Start and restore
   sudo systemctl start postgresql
   PGPASSWORD=jarvis psql -h localhost -U jarvis -d postgres < /tmp/postgres_dump.sql
   ```
   
   Then recreate the jarvis database and user if needed.

## References
- PostgreSQL documentation: https://www.postgresql.org/docs/
- JARVIS database schema: See migration scripts in `/home/venu/Proposals/Jarvis/`
- Connection settings: Check `~/.jarvis/.secrets/` for database credentials
- Health check script: `/home/venu/Proposals/Jarvis/automations/health_dashboard.py`