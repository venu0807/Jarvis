"""
jarvis_browser.py — Shared Playwright browser utility for all automations.

This is now a compatibility wrapper that re-exports from the new shared browser layer.
All new code should import from `automations.browser` directly.

Provides unified:
- Browser launch (async + sync, headless/headful)
- Context creation with optional storage_state loading
- Session saving (storage_state persistence)
- Safe teardown (context/page/browser close with error swallowing)
- Common constants (user_agent, viewport, locale, launch args)

Usage (async — job-automation):
    from jarvis_browser import AsyncBrowser

    async def main():
        jobs = []
        async with AsyncBrowser(headless=True) as browser:
            for name, session_path in portals:
                context = await browser.new_context_with_session(session_path)
                try:
                    jobs = await do_work(context)
                    await browser.save_session(context, session_path)
                finally:
                    await browser.safe_close(context)

Usage (sync — pinterest/linkedin/workday):
    from jarvis_browser import SyncBrowser

    def main():
        with SyncBrowser(headless=False) as browser:
            context = browser.launch_persistent(user_data_dir)
            page = context.pages[0] if context.pages else context.new_page()
            # do work
            # context auto-closed on exit
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Force Playwright to use the native Google Chrome instead of the broken Snap Chromium
if os.path.exists("/usr/bin/google-chrome"):
    os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = "/usr/bin/google-chrome"

# Re-export from the new shared browser layer
sys.path.append(str(Path(__file__).parent / "automations"))
from browser import (
    AsyncBrowser,
    SyncBrowser,
    safe_close_async,
    safe_close_sync,
    DEFAULT_USER_AGENT,
    DEFAULT_VIEWPORT,
    DEFAULT_LOCALE,
    BROWSER_LAUNCH_ARGS,
    BrowserConfig,
    build_context_kwargs,
)

# Also re-export vision fallback functions if available
try:
    from automations.shared_vision import solve_with_vision, solve_with_vision_async
except ImportError:
    solve_with_vision = None
    solve_with_vision_async = None

# Monkey-patch Playwright Page objects with .fallback()
try:
    from playwright.sync_api import Page as SyncPage
    if solve_with_vision:
        def _sync_fallback(self, instruction: str):
            return solve_with_vision(self, instruction)
        SyncPage.fallback = _sync_fallback
except ImportError:
    pass

try:
    from playwright.async_api import Page as AsyncPage
    if solve_with_vision_async:
        async def _async_fallback(self, instruction: str):
            return await solve_with_vision_async(self, instruction)
        AsyncPage.fallback = _async_fallback
except ImportError:
    pass

# Legacy function names for backward compatibility
__all__ = [
    "AsyncBrowser",
    "SyncBrowser",
    "safe_close_async",
    "safe_close_sync",
    "DEFAULT_USER_AGENT",
    "DEFAULT_VIEWPORT",
    "DEFAULT_LOCALE",
    "BROWSER_LAUNCH_ARGS",
    "BrowserConfig",
    "build_context_kwargs",
    "solve_with_vision",
    "solve_with_vision_async",
]