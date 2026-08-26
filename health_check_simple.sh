#!/bin/bash
set -e
echo "=== JARVIS SYSTEM HEALTH CHECK ==="
date
echo ""
check_port() {
  local host=$1
  local port=$2
  local timeout=${3:-2}
  if timeout $timeout bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
    echo "OPEN"
    return 0
  else
    echo "CLOSED"
    return 1
  fi
}
check_process() {
  local name=$1
  if pgrep -f "$name" > /dev/null 2>&1; then
    echo "RUNNING"
    return 0
  else
    echo "NOT RUNNING"
    return 1
  fi
}
echo "--- Critical Services ---"
echo -n "PostgreSQL (5432): "
pg_port=$(check_port localhost 5432)
echo -n "$pg_port, "
pg_proc=$(check_process postgres)
echo "Process: $pg_proc"
echo -n "Ollama (11434): "
ollama_port=$(check_port localhost 11434)
echo -n "$ollama_port, "
ollama_proc=$(check_process ollama)
echo "Process: $ollama_proc"
echo ""
echo "--- JARVIS Services ---"
declare -A services
services["job-automation"]=8001
services["pinterest"]=8002
services["model-router"]=8003
services["prometheus"]=9090
services["grafana"]=3001
services["alertmanager"]=9093
for service in "${!services[@]}"; do
  port=${services[$service]}
  echo -n "$service ($port): "
  port_status=$(check_port localhost $port)
  echo -n "$port_status, "
  proc_status=$(check_process $service)
  echo "Process: $proc_status"
done
echo ""
echo "=== HEALTH CHECK COMPLETE ==="
