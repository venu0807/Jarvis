"""
shared_utils.py — Shared utilities for JARVIS automations.

Provides:
  - setup_logging for consistent structured logging
  - retry decorator with exponential backoff for transient failures
  - StructuredLogWriter for persistent JSONL event logs
  - sleep_with_jitter for humanized pacing
  - safe_path_resolve for cross-script path resolution
  - atomic_write_text for safe file writes
  - ist_now / today_ist for IST time helpers
  - load_jarvis_env for centralized .env loading
  - log_metric for SQLite metrics
  - PostgreSQL connection pooling (ThreadedConnectionPool)
  - Health check endpoints for long-running bots

Usage:
    from shared_utils import setup_logging, retry, sleep_with_jitter, load_jarvis_env
    from shared_utils import HealthCheck, pg_connection, check_ollama, check_database

    load_jarvis_env()  # Call once at startup
    log = setup_logging("my_bot")
    log.info("Pipeline started")

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def fetch_page(url):
        ...

    # Health check
    health = HealthCheck("auto_applier")
    health.check("database", check_database)
    health.check("ollama", check_ollama)
    status = health.get_status()
"""

from __future__ import annotations

import functools
import json
import logging
import os
import random
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

T = TypeVar("T", bound=Callable[..., Any])

# Global connection pool (lazy initialization)
_pg_pool: Optional["ThreadedConnectionPool"] = None
_pool_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Centralized .env loading — call this once at startup in each automation
# ---------------------------------------------------------------------------

def load_jarvis_env() -> None:
    """
    Load .env from multiple possible locations in priority order.
    Call this once at the start of each automation script.
    
    Priority order:
    1. Project-specific .env (e.g., automations/pinterest/.env)
    2. Job-automation shared .env (common credentials)
    3. Central secrets at ~/.jarvis/.secrets/.env
    4. Current working directory .env
    5. Default load_dotenv() behavior
    """
    from dotenv import load_dotenv
    
    base_dir = Path(__file__).parent
    candidates = [
        base_dir / "pinterest" / ".env",                    # Pinterest-specific
        base_dir / "job-automation" / ".env",               # Shared job automation creds
        base_dir.parent / ".jarvis" / ".secrets" / ".env",  # Central secrets (project root)
        Path.home() / ".jarvis" / ".secrets" / ".env",      # Central secrets (user home)
        Path.cwd() / ".env",                                # CWD fallback
    ]
    
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return
    
    # Fallback - try default load_dotenv()
    load_dotenv()


# ---------------------------------------------------------------------------
# Setup logging — single source of truth for all automations
# ---------------------------------------------------------------------------

def setup_logging(
    name: str,
    log_dir: str | Path | None = None,
    level: int = logging.INFO,
    console: bool = True,
    file: bool = True,
) -> logging.Logger:
    """Return a configured logger for the given automation name.

    Creates a logger with:
      - A file handler writing to ``{log_dir}/{name}_{date}.log``
      - A console handler with timestamp and level (if console=True)
      - Structured format: ``[HH:MM:SS] LEVEL  message``

    Args:
        name: Short bot/script name (e.g. "auto_applier", "linkedin_bot").
        log_dir: Directory for log files. If None, auto-detects based on
            the calling script's location (looks for ``output/logs/`` under
            each automation's directory).
        level: Logging level (default: logging.INFO).
        console: Whether to emit logs to stderr (default: True).
        file: Whether to write logs to a daily file (default: True).

    Returns:
        A ``logging.Logger`` instance. Use ``log.info(...)``, ``log.error(...)``, etc.

    Example::
        log = setup_logging("auto_applier")
        log.info("Session loaded for portal=%s", portal_name)
        log.warning("Rate limit hit, backing off %ds", wait)
        log.error("Login failed: %s", exc_info=True)
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)
    logger.propagate = False

    fmt = logging.Formatter("[%(asctime)s] %(levelname)-5s  %(message)s", datefmt="%H:%M:%S")

    # ── Console handler ────────────────────────────────────────────────────
    if console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(level)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    # ── File handler ───────────────────────────────────────────────────────
    if file:
        if log_dir is None:
            log_dir = _detect_log_dir(name)
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_path = log_dir / f"{name}_{today_str}.log"
        fh = logging.FileHandler(str(log_path), encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def _detect_log_dir(name: str) -> Path:
    """Walk up from the caller's frame to find an ``output/logs/`` directory."""
    try:
        frame = sys._getframe(2)
        caller = Path(frame.f_globals.get("__file__", "") or ".")
        for parent in [caller.parent] + list(caller.parents):
            candidate = parent / "output" / "logs"
            if candidate.exists():
                return candidate
        # Fallback: project-root/logs/automation_name/
        return Path("logs") / name
    except Exception:
        return Path("logs") / name


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[T], T]:
    """Retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including first).
        delay: Initial delay in seconds before first retry.
        backoff: Multiplier for delay after each attempt (2.0 = double).
        exceptions: Tuple of exception types to catch and retry.
        on_retry: Optional callback(e, attempt) called before each retry.

    Example:
        @retry(max_attempts=5, delay=1.0, backoff=2.0)
        def unstable_api_call():
            ...
    """
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts:
                        raise
                    if on_retry:
                        on_retry(e, attempt)
                    sleep_time = delay * (backoff ** (attempt - 1))
                    # Add jitter: ±25%
                    jitter = random.uniform(-sleep_time * 0.25, sleep_time * 0.25)
                    time.sleep(sleep_time + jitter)
            # Should not reach here, but satisfy type checker
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator


# ---------------------------------------------------------------------------
# Structured JSONL logging
# ---------------------------------------------------------------------------

class StructuredLogWriter:
    """Write structured JSONL log entries to a file.

    Each line is a JSON object with a standard 'ts' (ISO timestamp) field
    plus caller-provided fields. Thread-safe for append-only usage.

    Example:
        log = StructuredLogWriter("output/logs/bot.jsonl")
        log.write(event="scrape_complete", portal="naukri", count=42)
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **fields: Any) -> None:
        entry = {"ts": datetime.now(timezone.utc).isoformat(), **fields}
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")


# ---------------------------------------------------------------------------
# Humanized pacing
# ---------------------------------------------------------------------------

def sleep_with_jitter(
    base: float,
    jitter_pct: float = 0.4,
    min_sleep: float = 0.5,
    reason: str = "",
) -> None:
    """Sleep for `base` seconds ±jitter_pct%, with a floor.

    Example:
        sleep_with_jitter(30, jitter_pct=0.3, reason="between portals")
    """
    jitter_range = base * jitter_pct
    actual = max(min_sleep, base + random.uniform(-jitter_range, jitter_range))
    if reason:
        print(f"  ⏸  sleeping {actual:.0f}s ({reason})")
    time.sleep(actual)


# ---------------------------------------------------------------------------
# Safe path resolution (cross-script compat)
# ---------------------------------------------------------------------------

def safe_path_resolve(*segments: str | Path) -> Path:
    """Resolve a path relative to the project root (D:\\Proposals\\Jarvis).

    Falls back to the first segment's parent directory if the canonical
    root doesn't exist. Handles both relative and absolute inputs.
    """
    # Canonical project root
    root = Path("D:/Proposals/Jarvis")
    if root.exists():
        return root.joinpath(*segments)

    # Fallback: resolve from the calling script location
    caller = Path(__file__).resolve()
    for parent in caller.parents:
        marker = parent / "policy.py"
        if marker.exists():
            return parent.joinpath(*segments)

    # Last resort: relative to CWD
    return Path(".").resolve().joinpath(*segments)


# ---------------------------------------------------------------------------
# Atomic file write (avoid partial reads)
# ---------------------------------------------------------------------------

def atomic_write_text(path: str | Path, content: str, encoding: str = "utf-8") -> None:
    """Write text to a file atomically using a temp file + rename.

    Prevents other processes from reading a half-written file.
    """
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Session age checker — alert when portal sessions are about to expire
# ---------------------------------------------------------------------------

def check_session_ages(
    session_dir: str | Path,
    max_age_days: int = 25,
    warn_threshold_days: int = 20,
) -> list[dict]:
    """Scan a session directory and report session file ages.

    Returns a list of dicts with keys:
        portal: session file stem (e.g. "naukri")
        path: absolute path to session file
        age_days: how old the session is
        status: "fresh" | "warn" (near expiry) | "stale" (expired, >max_age_days)

    Example:
        alerts = check_session_ages(".sessions")
        for a in alerts:
            if a["status"] != "fresh":
                log.warning("Session %s is %s (%d days old)",
                            a["portal"], a["status"], a["age_days"])
    """
    session_dir = Path(session_dir)
    if not session_dir.exists():
        return []

    now = datetime.now(timezone.utc).timestamp()
    results: list[dict] = []

    for sess_file in sorted(session_dir.glob("*.json")):
        age_seconds = now - sess_file.stat().st_mtime
        age_days = age_seconds / 86400

        if age_days > max_age_days:
            status = "stale"
        elif age_days > warn_threshold_days:
            status = "warn"
        else:
            status = "fresh"

        results.append({
            "portal": sess_file.stem,
            "path": str(sess_file),
            "age_days": round(age_days, 1),
            "status": status,
        })

    return results


# ---------------------------------------------------------------------------
# Time helpers (IST = UTC+5:30)
# ---------------------------------------------------------------------------

_IST_OFFSET = timedelta(hours=5, minutes=30)


def _ist_now_dt() -> datetime:
    return datetime.now(timezone.utc) + _IST_OFFSET


def ist_now() -> str:
    """Return current IST time as ISO string (UTC+5:30)."""
    return _ist_now_dt().isoformat()


def today_ist() -> str:
    """Return today's date in YYYY-MM-DD format (IST)."""
    return _ist_now_dt().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Metrics Logging
# ---------------------------------------------------------------------------

def log_metric(category: str, subcategory: str, count: int = 1) -> None:
    """Logs an operational metric to the central SQLite metrics database.
    
    Args:
        category: High-level metric category (e.g., 'emails_sent', 'skills_learned').
        subcategory: Granular detail (e.g., 'Django Developer', 'Docker').
        count: The value to increment.
    """
    db_path = Path(__file__).parent / "metrics.db"
    
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                category TEXT,
                subcategory TEXT,
                count INTEGER
            )
        ''')
        cursor.execute('''
            INSERT INTO metrics (timestamp, category, subcategory, count) 
            VALUES (?, ?, ?, ?)
        ''', (ist_now(), category, subcategory, count))
        
        conn.commit()
        conn.close()
    except Exception as e:
        log = setup_logging("shared_utils")
        log.error(f"Failed to log metric: {e}")


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
            log = setup_logging("shared_utils")
            log.warning("DATABASE_URL not set, PostgreSQL pool not initialized")
            return None
        
        try:
            _pg_pool = ThreadedConnectionPool(minconn, maxconn, dsn)
            log = setup_logging("shared_utils")
            log.info(f"PostgreSQL pool initialized (min={minconn}, max={maxconn})")
        except Exception as e:
            log = setup_logging("shared_utils")
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
            log = setup_logging("shared_utils")
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
        import time
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
    import json
    
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