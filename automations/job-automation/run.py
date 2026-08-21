#!/usr/bin/env python3
"""
run.py — Canonical entry point for Job Automation Pipeline.

This is the single entrypoint that routes via JARVIS policy for all LLM calls.
Usage: python run.py [--portal PORTAL] [--headless=false/true] [--limit N] [--health-only]
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path

# Ensure we can import from jarvis root
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))
sys.path.append(str(BASE_DIR.parent.parent))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

# Parse ALL arguments manually - NO argparse at all

# Default values
portal = None
limit = None
health_only = False
headless = True  # default

# Parse ALL arguments manually
i = 1
while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == "--portal" and i + 1 < len(sys.argv):
        portal = sys.argv[i + 1]
        i += 2
    elif arg == "--limit" and i + 1 < len(sys.argv):
        limit = int(sys.argv[i + 1])
        i += 2
    elif arg == "--health-only":
        health_only = True
        i += 1
    elif arg.startswith("--headless="):
        val = arg.split("=", 1)[1].lower()
        if val == "false":
            headless = False
        elif val == "true":
            headless = True
        i += 1
    elif arg == "--headless":
        if i + 1 < len(sys.argv) and sys.argv[i + 1].lower() in ("true", "false"):
            headless = sys.argv[i + 1].lower() == "true"
            i += 2
        else:
            headless = True
            i += 1
    elif arg.startswith("--headful="):
        val = arg.split("=", 1)[1].lower()
        headless = val != "true"
        i += 1
    elif arg == "--headful":
        headless = False
        i += 1
    else:
        i += 1

# Set env vars BEFORE importing auto_applier so module-level HEADLESS reads correct value
os.environ["HEADLESS"] = "true" if headless else "false"
if limit:
    os.environ["DAILY_LIMIT"] = str(limit)
if portal:
    os.environ["SINGLE_PORTAL"] = portal

from auto_applier import main as run_auto_applier
from aiohttp import web
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def health_check(request):
    """Health check endpoint."""
    try:
        # Check Ollama connectivity
        import httpx
        ollama_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            ollama_healthy = resp.status_code == 200
            models = resp.json().get("models", []) if ollama_healthy else []
    except Exception:
        ollama_healthy = False
        models = []

    # Check database
    try:
        import asyncpg
        db_url = os.getenv("DATABASE_URL", "postgresql://jarvis:***@localhost:5432/jarvis")
        conn = await asyncpg.connect(db_url, timeout=3.0)
        await conn.close()
        db_healthy = True
    except Exception:
        db_healthy = False

    # Check model router
    try:
        router_url = os.getenv("MODEL_ROUTER_URL", "http://localhost:8090")
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{router_url}/healthz")
            router_healthy = resp.status_code == 200
    except Exception:
        router_healthy = False

    healthy = ollama_healthy and db_healthy
    status = "healthy" if healthy else "degraded"

    return web.json_response({
        "status": status,
        "service": "job-automation",
        "ollama_healthy": ollama_healthy,
        "models_loaded": len(models),
        "db_healthy": db_healthy,
        "router_healthy": router_healthy,
    }, status=200 if healthy else 503)


async def start_health_server():
    """Start the health check HTTP server."""
    app = web.Application()
    app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("health_server_started", port=8080)
    return runner


def main() -> None:
    # Strip headless/headful/limit args from sys.argv before calling auto_applier
    # (auto_applier has its own argparse that doesn't know --headless/--headful/--limit)
    new_argv = [sys.argv[0]]
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--headless") or arg.startswith("--headful") or arg.startswith("--limit"):
            # Skip this arg and its value if it has one
            if arg.startswith("--headless=") or arg.startswith("--headful=") or arg.startswith("--limit="):
                i += 1
            elif arg in ("--headless", "--headful"):
                if i + 1 < len(sys.argv) and sys.argv[i + 1].lower() in ("true", "false"):
                    i += 2
                else:
                    i += 1
            elif arg == "--limit":
                i += 2  # skip --limit and its value
            else:
                i += 1
        else:
            new_argv.append(arg)
            i += 1
    sys.argv = new_argv

    # Use argparse for remaining known args
    parser = argparse.ArgumentParser(description="Job Automation Pipeline")
    parser.add_argument(
        "--portal",
        help="Run one portal only: naukri|internshala|indeed|foundit",
        choices=["naukri", "internshala", "indeed", "foundit"]
    )
    parser.add_argument("--limit", type=int, help="Override daily apply limit per portal")
    parser.add_argument("--health-only", action="store_true", help="Only run health server")
    args, _ = parser.parse_known_args()

    # Override env vars from argparse if provided (for backwards compatibility)
    if args.limit:
        os.environ["DAILY_LIMIT"] = str(args.limit)
    if args.portal:
        os.environ["SINGLE_PORTAL"] = args.portal

    # Run the automation
    if health_only:
        async def run_health():
            runner = await start_health_server()
            try:
                await asyncio.Event().wait()  # Run forever
            finally:
                await runner.cleanup()
        asyncio.run(run_health())
    else:
        # Start health server in background
        loop = asyncio.get_event_loop()
        runner = loop.run_until_complete(start_health_server())
        try:
            asyncio.run(run_auto_applier())
        finally:
            loop.run_until_complete(runner.cleanup())


if __name__ == "__main__":
    main()