"""
Shared Browser Layer - Canonical browser management for all JARVIS automations.

This module provides a unified AsyncBrowser class that handles:
- Playwright browser lifecycle
- Session persistence via storage_state
- Context creation with session restore
- Proper cleanup

Usage:
    from browser import AsyncBrowser, safe_close_async

    async with AsyncBrowser(headless=True) as browser:
        context = await browser.new_context_with_session(session_file)
        page = await context.new_page()
        # ... use page
        await browser.save_session(context, session_file)
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Shared constants
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
DEFAULT_LOCALE = "en-US"
BROWSER_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-setuid-sandbox",
]

class BrowserConfig:
    """Simple configuration holder for browser launch options."""
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        self.headless = headless
        self.slow_mo = slow_mo

def build_context_kwargs(config: BrowserConfig, session_file: Optional[Path | str] = None, **extra) -> Dict[str, Any]:
    """
    Build keyword arguments for browser.new_context or new_context_with_session.
    If session_file is provided, the caller should pass it to new_context_with_session
    (which will handle storage_state). This function returns the base kwargs.
    """
    kwargs = {
        "headless": config.headless,
        "slow_mo": config.slow_mo,
    }
    # Update with any extra overrides
    kwargs.update(extra)
    return kwargs

class AsyncBrowser:
    """Manages a Playwright browser instance with session persistence."""

    def __init__(self, headless: bool = True, slow_mo: int = 0):
        self.headless = headless
        self.slow_mo = slow_mo
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._contexts: list[BrowserContext] = []

    async def __aenter__(self) -> "AsyncBrowser":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Start the Playwright browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=BROWSER_LAUNCH_ARGS
        )

    async def close(self):
        """Close all contexts and browser."""
        for ctx in self._contexts:
            try:
                await ctx.close()
            except:
                pass
        self._contexts.clear()

        if self._browser:
            try:
                await self._browser.close()
            except:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except:
                pass
            self._playwright = None

    async def new_context(self, **kwargs) -> BrowserContext:
        """Create a new browser context."""
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first or use async context manager.")

        # Default viewport and user agent
        defaults = {
            "viewport": DEFAULT_VIEWPORT,
            "user_agent": DEFAULT_USER_AGENT,
        }
        if "locale" not in kwargs:
            defaults["locale"] = DEFAULT_LOCALE
        defaults.update(kwargs)

        context = await self._browser.new_context(**defaults)
        self._contexts.append(context)
        return context

    async def new_context_with_session(self, session_file: Path | str, **kwargs) -> BrowserContext:
        """Create a new context, loading storage_state from session_file if it exists."""
        session_path = Path(session_file)
        if session_path.exists():
            kwargs.setdefault("storage_state", str(session_path))
            print(f"  💾 Loading session from {session_path.name}")
        return await self.new_context(**kwargs)

    async def save_session(self, context: BrowserContext, session_file: Path | str):
        """Save context storage_state to session_file."""
        session_path = Path(session_file)
        session_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(session_path))
        print(f"  💾 Session saved to {session_path.name}")


class SyncBrowser:
    """Synchronous wrapper for simple scripts that don't need async."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def new_context(self, **kwargs):
        defaults = {
            "viewport": DEFAULT_VIEWPORT,
            "user_agent": DEFAULT_USER_AGENT,
        }
        if "locale" not in kwargs:
            defaults["locale"] = DEFAULT_LOCALE
        defaults.update(kwargs)
        return self._browser.new_context(**defaults)

    def new_context_with_session(self, session_file: Path | str, **kwargs):
        session_path = Path(session_file)
        if session_path.exists():
            kwargs.setdefault("storage_state", str(session_path))
        return self.new_context(**kwargs)

    def save_session(self, context, session_file: Path | str):
        session_path = Path(session_file)
        session_path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(session_path))


async def safe_close_async(browser_mgr: AsyncBrowser):
    """Safely close the browser manager, handling any exceptions."""
    try:
        await browser_mgr.close()
    except Exception as e:
        print(f"⚠️ Error during browser cleanup: {e}")


def safe_close_sync(browser_mgr: 'SyncBrowser'):
    """Safely close the browser manager (sync version), handling any exceptions."""
    try:
        browser_mgr.__exit__(None, None, None)
    except Exception as e:
        print(f"⚠️ Error during browser cleanup: {e}")