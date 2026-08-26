#!/bin/bash
set -e

echo "=== JARVIS SYSTEM HEALTH CHECK ==="
echo "Timestamp: $(date)"
echo ""

# Function to check a TCP port
check_port() {
    local host=$1
    local port=$2
    local timeout=${3:-5}
    if (echo > /dev/tcp/$host/$port) >/dev/null 2>&1; then
        echo "OK"
        return 0
    else
        echo "FAIL"
        return 1
    fi
}

# Function to check an HTTP endpoint
check_http() {
    local url=$1
    local timeout=${2:-5}
    if curl -s --max-time $timeout -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
        echo "OK"
        return 0
    else
        echo "FAIL"
        return 1
    fi
}

# Check PostgreSQL (native in WSL)
echo -n "Checking PostgreSQL (port 5432): "
pg_status=$(check_port localhost 5432)
echo $pg_status

# Check Ollama (native in WSL)
echo -n "Checking Ollama (port 11434): "
ollama_status=$(check_port localhost 11434)
echo $ollama_status

# Define services from docker-compose (if running in Docker)
declare -A services
services["job-automation"]="8001 http://localhost:8001/healthz"
services["pinterest"]="8002 http://localhost:8002/healthz"
services["model-router"]="8003 http://localhost:8003/healthz"
services["prometheus"]="9090 http://localhost:9090/-/healthy"
services["grafana"]="3001 http://localhost:3001/api/health"
services["alertmanager"]="9093 http://localhost:9093/-/healthy"

# Check if Docker is running
if docker info >/dev/null 2>&1; then
    echo ""
    echo "Docker daemon is accessible."
    echo "Checking container statuses:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(jarvis-|NAMES)"
else
    echo ""
    echo "Docker daemon is not accessible. Checking native services only."
fi

# Check each service (whether via Docker or native, we check the port and health endpoint)
echo ""
echo "=== Service Health Checks ==="
for service in "${!services[@]}"; do
    IFS=' ' read -r port endpoint <<< "${services[$service]}"
    echo -n "Checking $service (port $port): "
    port_status=$(check_port localhost $port)
    if [ "$port_status" = "OK" ] && [ -n "$endpoint" ]; then
        echo -n "Port OK, "
        http_status=$(check_http $endpoint)
        echo -n "HTTP: $http_status"
        if [ "$port_status" = "OK" ] && [ "$http_status" = "OK" ]; then
            echo " -> OVERALL: OK"
        else
            echo " -> OVERALL: FAIL"
        fi
    else
        if [ "$port_status" = "FAIL" ]; then
            echo "Port FAIL -> OVERALL: FAIL"
        else
            echo -n "Port OK, but no endpoint defined -> OVERALL: "
            if [ -z "$endpoint" ]; then
                echo "OK (no endpoint)"
            else
                echo "FAIL (endpoint check skipped)"
            fi
        fi
    fi
done

# Check native processes for key services (as a fallback)
echo ""
echo "=== Native Process Checks ==="
echo -n "Checking native postgres process: "
if pgrep -x "postgres" > /dev/null; then
    echo "OK"
else
    echo "FAIL (no postgres process)"
fi

echo -n "Checking native ollama process: "
if pgrep -x "ollama" > /dev/null; then
    echo "OK"
else
    echo "FAIL (no ollama process)"
fi

echo ""
echo "=== HEALTH CHECK COMPLETE ==="