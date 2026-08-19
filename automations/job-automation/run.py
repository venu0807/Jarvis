#!/usr/bin/env python3
"""
run.py — Canonical entry point for Job Automation Pipeline.

This is the single entrypoint that routes via JARVIS policy for all LLM calls.
Usage: python run.py [--portal PORTAL] [--headful] [--limit N]
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure we can import from jarvis root
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))
sys.path.append(str(BASE_DIR.parent.parent))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

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
        db_url = os.getenv("DATABASE_URL", "postgresql://jarvis:jarvis@postgres:5432/jarvis")
        conn = await asyncpg.connect(db_url, timeout=3.0)
        await conn.close()
        db_healthy = True
    except Exception:
        db_healthy = False
    
    # Check model router
    try:
        router_url = os.getenv("MODEL_ROUTER_URL", "http://model-router:8090")
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
    parser = argparse.ArgumentParser(description="Job Automation Pipeline")
    parser.add_argument(
        "--portal", 
        help="Run one portal only: naukri|internshala|indeed|foundit",
        choices=["naukri", "internshala", "indeed", "foundit"]
    )
    parser.add_argument("--headful", action="store_true", help="Run with visible browser")
    parser.add_argument("--limit", type=int, help="Override daily apply limit per portal")
    parser.add_argument("--health-only", action="store_true", help="Only run health server")
    args = parser.parse_args()

    # Set env vars for auto_applier to pick up
    if args.headful:
        os.environ["HEADLESS"] = "false"
    if args.limit:
        os.environ["DAILY_LIMIT"] = str(args.limit)
    if args.portal:
        os.environ["SINGLE_PORTAL"] = args.portal

    if args.health_only:
        asyncio.run(start_health_server())
        # Keep running
        asyncio.get_event_loop().run_forever()
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