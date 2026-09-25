#!/usr/bin/env python3
import socket
import subprocess
import sys
import urllib.request
import urllib.error
import json

def check_port(host, port, timeout=5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_http(url, timeout=5):
    try:
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.getcode() == 200
    except Exception as e:
        return False

def check_postgres(host, port, dbname, user, password):
    # Try to use psycopg2 if available
    try:
        import psycopg2
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        conn.close()
        return True, "Connection successful"
    except ImportError:
        # If psycopg2 not installed, just check port
        if check_port(host, port):
            return True, "Port open (psycopg2 not installed for auth test)"
        else:
            return False, "Port closed"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def check_docker_containers():
    try:
        output = subprocess.check_output(["wsl", "-d", "Ubuntu", "-e", "bash", "-c", "cd /home/venu/Proposals/Jarvis && docker compose ps --format 'json'"], stderr=subprocess.STDOUT, timeout=10)
        data = json.loads(output.decode('utf-8'))
        # If the output is a list of objects
        if isinstance(data, list):
            return data
        else:
            # If it's a single object, wrap in list
            return [data] if data else []
    except Exception as e:
        return [{"error": str(e)}]

def check_native_processes():
    # Check for postgres, ollama, and python processes that might be our services
    try:
        output = subprocess.check_output(["wsl", "-d", "Ubuntu", "-e", "bash", "-c", "ps aux"], stderr=subprocess.STDOUT, timeout=10)
        lines = output.decode('utf-8').split('\n')
        processes = []
        for line in lines:
            if any(name in line for name in ['postgres', 'ollama', 'python']) and 'grep' not in line:
                processes.append(line.strip())
        return processes
    except Exception as e:
        return [f"Error checking processes: {str(e)}"]

def check_core_databases(results):
    # Check PostgreSQL (native)
    pg_host = "localhost"
    pg_port = 5432
    pg_db = "jarvis"
    pg_user = "jarvis"
    pg_pass = "jarvis"  # default from docker-compose
    pg_ok, pg_msg = check_postgres(pg_host, pg_port, pg_db, pg_user, pg_pass)
    results["postgresql"] = {"status": "OK" if pg_ok else "FAIL", "message": pg_msg}

def check_ollama_service(results):
    # Check Ollama (native)
    ollama_port = 11434
    ollama_ok = check_port("localhost", ollama_port)
    results["ollama"] = {"status": "OK" if ollama_ok else "FAIL", "message": f"Port {ollama_port} {'open' if ollama_ok else 'closed'}"}

def check_docker_services(results):
    # Define services from docker-compose
    services = [
        ("job-automation", 8001, "http://localhost:8001/healthz"),
        ("pinterest", 8002, "http://localhost:8002/healthz"),
        ("model-router", 8003, "http://localhost:8003/healthz"),
        ("prometheus", 9090, "http://localhost:9090/-/healthy"),
        ("grafana", 3001, "http://localhost:3001/api/health"),
        ("alertmanager", 9093, "http://localhost:9093/-/healthy"),
    ]
    
    for name, port, health_endpoint in services:
        port_ok = check_port("localhost", port)
        http_ok = False
        http_msg = "Not checked"
        if port_ok and health_endpoint:
            http_ok = check_http(health_endpoint)
            http_msg = "Health endpoint OK" if http_ok else "Health endpoint failed"
        else:
            http_msg = "Port closed" if not port_ok else "No health endpoint defined"
        
        overall_ok = port_ok and (http_ok if health_endpoint else True)
        results[name] = {
            "status": "OK" if overall_ok else "FAIL",
            "port_open": port_ok,
            "http_check": http_msg if health_endpoint else "N/A",
            "message": f"Port {port}: {'open' if port_ok else 'closed'}, {http_msg}"
        }

def check_system_environment(results):
    # Check Docker containers
    containers = check_docker_containers()
    results["docker_containers"] = {
        "status": "INFO",
        "data": containers
    }
    
    # Check native processes
    processes = check_native_processes()
    results["native_processes"] = {
        "status": "INFO",
        "data": processes[:10]  # Limit output
    }

def evaluate_overall_status(results):
    # Overall status
    critical_services = ["postgresql", "ollama", "job-automation", "pinterest", "model-router"]
    overall_ok = all(results.get(s, {}).get("status") == "OK" for s in critical_services if s in results)
    results["overall"] = {"status": "OK" if overall_ok else "FAIL", "message": "All critical services healthy" if overall_ok else "Some critical services unhealthy"}
    return overall_ok

def print_health_report(results):
    # Print report
    print("=== JARVIS SYSTEM HEALTH CHECK ===")
    for key, val in results.items():
        if key == "overall":
            continue
        print(f"\n{key.upper()}:")
        if isinstance(val, dict):
            for k, v in val.items():
                if k not in ["data", "message"]:  # We'll print message separately
                    print(f"  {k}: {v}")
            if "message" in val:
                print(f"  message: {val['message']}")
            if "data" in val and isinstance(val["data"], list):
                print("  data:")
                for item in val["data"][:5]:  # Limit to 5 items
                    print(f"    - {item}")
                if len(val["data"]) > 5:
                    print(f"    ... and {len(val['data']) - 5} more")
        else:
            print(f"  {val}")
    
    print(f"\nOVERALL: {results['overall']['status']} - {results['overall']['message']}")

def main():
    results = {}
    check_core_databases(results)
    check_ollama_service(results)
    check_docker_services(results)
    check_system_environment(results)
    overall_ok = evaluate_overall_status(results)
    print_health_report(results)
    sys.exit(0 if overall_ok else 1)

if __name__ == "__main__":
    main()
