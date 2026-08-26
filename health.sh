#!/bin/bash
set -e

echo '=== JARVIS SYSTEM HEALTH CHECK ==='
echo "Timestamp: Tue, Aug 25, 2026 01:25:12 AM"
echo ''

# Function to check a TCP port with timeout
check_port() {
    local host=
    local port=
    local timeout=2
    if timeout  bash -c "echo > /dev/tcp//" 2>/dev/null; then
        echo "OPEN"
        return 0
    else
        echo "CLOSED"
        return 1
    fi
}

# Function to check an HTTP endpoint with timeout
check_http() {
    local url=
    local timeout=2
    local status_code
    status_code= || status_code="000"
    if [[ "" =~ ^2 ]]; then
        echo "OK"
        return 0
    else
        echo "FAIL (HTTP )"
        return 1
    fi
}

# Check PostgreSQL (native in WSL)
echo -n 'PostgreSQL connection: '
if PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT 1" > /dev/null 2>&1; then
    echo 'OK'
    PGSQL_OK=1
else
    echo 'FAIL'
    PGSQL_OK=0
fi

# Check Ollama (native in WSL)
echo -n 'Ollama API: '
if timeout 2 curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo 'OK'
    OLLAMA_OK=1
else
    echo 'FAIL'
    OLLAMA_OK=0
fi

echo ''
echo 'Service Checks:'
declare -A service_ports
service_ports["job-automation"]=8001
service_ports["pinterest"]=8002
service_ports["model-router"]=8003
service_ports["prometheus"]=9090
service_ports["grafana"]=3001
service_ports["alertmanager"]=9093

declare -A service_endpoints
service_endpoints["job-automation"]="/healthz"
service_endpoints["pinterest"]="/healthz"
service_endpoints["model-router"]="/healthz"
service_endpoints["prometheus"]="/-/healthy"
service_endpoints["grafana"]="/api/health"
service_endpoints["alertmanager"]="/-/healthy"

for service in ""; do
    port=
    endpoint=
    echo -n "   (port ): "
    port_status=
    if [[ "" == "OPEN" ]]; then
        echo -n "PORT_OPEN, 
