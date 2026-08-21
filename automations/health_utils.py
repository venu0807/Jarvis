"""
health_utils.py — Health check and PostgreSQL connection pooling utilities.
"""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# Global connection pool (lazy initialization)
_pg_pool: Optional["ThreadedConnectionPool"] = None
_pool_lock = threading.Lock()


# ---------------------------------------------------------------------------
# PostgreSQL Connection Pooling (Thread-safe, lazy init)
# ---------------------------------------------------------------------------

def get_pg_pool(
    minconn: int = 2,
    maxconn: int = 10,
    dsn: str | None = None,
) -> Optional["ThreadedConnectionPool"]:
    """Get or create the global PostgreSQL connection pool.
    
    Args:
        minconn: Minimum connections in pool.
        maxconn: Maximum connections in pool.
        dsn: PostgreSQL DSN string. If None, reads from DATABASE_URL env var.
    
    Returns:
        ThreadedConnectionPool or None if psycopg2 not available.
    """
    global _pg_pool
    
    if not PSYCOPG2_AVAILABLE:
        return None
    
    if _pg_pool is not None:
        return _pg_pool
    
    with _pool_lock:
        if _pg_pool is not None:
            return _pg_pool
        
        dsn = dsn or os.getenv("DATABASE_URL")
        if not dsn:
            from shared_utils import setup_logging
            log = setup_logging("health_utils")
            log.warning("DATABASE_URL not set, PostgreSQL pool not initialized")
            return None
        
        try:
            _pg_pool = ThreadedConnectionPool(minconn, maxconn, dsn)
            from shared_utils import setup_logging
            log = setup_logging("health_utils")
            log.info(f"PostgreSQL pool initialized (min={minconn}, max={maxconn})")
        except Exception as e:
            from shared_utils import setup_logging
            log = setup_logging("health_utils")
            log.error(f"Failed to create PostgreSQL pool: {e}")
            return None
    
    return _pg_pool


@contextmanager
def pg_connection():
    """Context manager for acquiring a PostgreSQL connection from the pool.
    
    Usage:
        with pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM events WHERE portal = %s", (portal,))
    
    Yields:
        psycopg2 connection (automatically returned to pool on exit).
    """
    pool = get_pg_pool()
    if pool is None:
        raise RuntimeError("PostgreSQL pool not initialized. Call get_pg_pool() first.")
    
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def close_pg_pool() -> None:
    """Close all connections in the PostgreSQL pool. Call on shutdown."""
    global _pg_pool
    with _pool_lock:
        if _pg_pool is not None:
            _pg_pool.closeall()
            _pg_pool = None
            from shared_utils import setup_logging
            log = setup_logging("health_utils")
            log.info("PostgreSQL pool closed")


# ---------------------------------------------------------------------------
# Health Check Endpoint Helpers
# ---------------------------------------------------------------------------

class HealthCheck:
    """Simple health check aggregator for long-running bots.
    
    Usage:
        health = HealthCheck("auto_applier")
        health.check("database", lambda: test_db_connection())
        health.check("session", lambda: validate_session("naukri"))
        
        # In HTTP handler or status endpoint:
        status = health.get_status()
        # Returns: {"status": "healthy|degraded|unhealthy", "checks": {...}, "ts": "..."}
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._checks: dict[str, Callable[[], tuple[bool, str]]] = {}
        self._last_results: dict[str, tuple[bool, str, float]] = {}
    
    def check(self, name: str, func: Callable[[], tuple[bool, str]]) -> None:
        """Register a health check.
        
        Args:
            name: Check identifier (e.g., "database", "session", "ollama").
            func: Callable returning (is_healthy: bool, message: str).
        """
        self._checks[name] = func
    
    def run_checks(self) -> dict[str, tuple[bool, str, float]]:
        """Run all registered checks and cache results."""
        self._last_results = {}
        for name, func in self._checks.items():
            start = time.time()
            try:
                healthy, msg = func()
                elapsed = time.time() - start
            except Exception as e:
                healthy, msg = False, f"Check failed: {e}"
                elapsed = time.time() - start
            self._last_results[name] = (healthy, msg, elapsed)
        return self._last_results
    
    def get_status(self) -> dict[str, Any]:
        """Get aggregated health status."""
        if not self._last_results:
            self.run_checks()
        
        healthy_count = sum(1 for h, _, _ in self._last_results.values() if h)
        total_count = len(self._last_results)
        
        if total_count == 0:
            overall = "unknown"
        elif healthy_count == total_count:
            overall = "healthy"
        elif healthy_count > 0:
            overall = "degraded"
        else:
            overall = "unhealthy"
        
        from shared_utils import ist_now
        return {
            "service": self.service_name,
            "status": overall,
            "checks": {
                name: {"healthy": h, "message": msg, "latency_ms": round(lt * 1000, 1)}
                for name, (h, msg, lt) in self._last_results.items()
            },
            "ts": ist_now(),
        }


def create_health_endpoint(
    service_name: str,
    port: int = 8080,
    path: str = "/healthz",
) -> Callable[[], None]:
    """Create a simple HTTP health endpoint for a long-running bot.
    
    Returns a function that starts the HTTP server in a background thread.
    Call the returned function to start serving.
    
    Usage:
        health = HealthCheck("linkedin_bot")
        health.check("ollama", lambda: (test_ollama(), "OLLAMA OK"))
        start_health_server = create_health_endpoint("linkedin_bot", port=8081)
        start_health_server()  # Runs in background thread
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    
    health = HealthCheck(service_name)
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == path:
                status = health.get_status()
                self.send_response(200 if status["status"] != "unhealthy" else 503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(status).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # Suppress default logging
    
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    
    def run_server():
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    return thread


# ---------------------------------------------------------------------------
# Example health checks (can be imported and used directly)
# ---------------------------------------------------------------------------

def check_ollama(host: str | None = None) -> tuple[bool, str]:
    """Check if Ollama is reachable."""
    import urllib.request
    host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as resp:
            return resp.status == 200, f"Ollama OK at {host}"
    except Exception as e:
        return False, f"Ollama unreachable: {e}"


def check_database(dsn: str | None = None) -> tuple[bool, str]:
    """Check PostgreSQL connectivity."""
    dsn = dsn or os.getenv("DATABASE_URL")
    if not dsn:
        return False, "DATABASE_URL not set"
    try:
        import psycopg2
        with psycopg2.connect(dsn, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True, "Database OK"
    except Exception as e:
        return False, f"Database error: {e}"


def check_session(session_dir: str | Path, portal: str, max_age_days: int = 25) -> tuple[bool, str]:
    """Check if a portal session file exists and is fresh."""
    session_dir = Path(session_dir)
    sess_file = session_dir / f"{portal}.json"
    if not sess_file.exists():
        return False, f"Session file missing: {portal}.json"
    
    age_days = (datetime.now(timezone.utc).timestamp() - sess_file.stat().st_mtime) / 86400
    if age_days > max_age_days:
        return False, f"Session stale ({age_days:.1f} days)"
    
    return True, f"Session fresh ({age_days:.1f} days)"