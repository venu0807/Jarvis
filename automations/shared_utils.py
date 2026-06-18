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

Usage:
    from shared_utils import setup_logging, retry, sleep_with_jitter

    log = setup_logging("my_bot")
    log.info("Pipeline started")

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def fetch_page(url):
        ...
"""

from __future__ import annotations

import functools
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T", bound=Callable[..., Any])


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
