"""
jarvis_browser.py — Shared Playwright browser utility for all automations.

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add parent directory to path to import shared_vision
sys.path.append(str(Path(__file__) / "automations"))
try:
    from automations.shared_vision import solve_with_vision, solve_with_vision_async
except ImportError:
    # Fallback if shared_vision isn't available
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


# ── Browser defaults ──────────────────────────────────────────────────────────

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_VIEWPORT = {"width": 1366, "height": 768}

DEFAULT_LOCALE = "en-IN"

BROWSER_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class BrowserConfig:
    """Holds all parameters for launching a browser and creating contexts."""
    headless: bool = True
    user_agent: str = DEFAULT_USER_AGENT
    viewport: dict = field(default_factory=lambda: dict(DEFAULT_VIEWPORT))
    locale: str = DEFAULT_LOCALE
    extra_args: list = field(default_factory=list)

    def launch_args(self) -> list:
        """Combine standard args with mode-specific args and any extras."""
        args = list(BROWSER_LAUNCH_ARGS)
        if not self.headless:
            # Headful but unobtrusive: start minimized so the automation
            # browser sits in the taskbar instead of stealing the screen.
            args.append("--start-minimized")
        args.extend(self.extra_args)
        return args

    def context_kwargs(self, storage_state_path: Optional[Path] = None) -> dict:
        """Build the dict passed to browser.new_context()."""
        kwargs: dict = {
            "user_agent": self.user_agent,
            "viewport": dict(self.viewport),
            "locale": self.locale,
        }
        if storage_state_path and storage_state_path.exists():
            kwargs["storage_state"] = str(storage_state_path)
        return kwargs


# ── Context kwargs builder (for callers that don't want the full class) ───────

def build_context_kwargs(
    session_path: Optional[Path] = None,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    viewport: Optional[dict] = None,
    locale: str = DEFAULT_LOCALE,
) -> dict:
    """Build a context args dict, optionally loading a saved session."""
    kwargs: dict = {
        "user_agent": user_agent,
        "viewport": viewport or dict(DEFAULT_VIEWPORT),
        "locale": locale,
    }
    if session_path and session_path.exists():
        kwargs["storage_state"] = str(session_path)
    return kwargs


# ── Safe close helpers ────────────────────────────────────────────────────────

async def safe_close_async(obj) -> None:
    """Close an async Playwright object (page / context / browser) silently."""
    if obj is None:
        return
    try:
        if hasattr(obj, "close"):
            await obj.close()
    except Exception:
        pass


def safe_close_sync(obj) -> None:
    """Close a sync Playwright object (page / context / browser) silently."""
    if obj is None:
        return
    try:
        if hasattr(obj, "close"):
            obj.close()
    except Exception:
        pass


# ── Async browser helper (auto_applier, validate_sessions, headful_reauth) ─────

class AsyncBrowser:
    """Context manager wrapping async Playwright browser lifecycle.

    Usage:
        async with AsyncBrowser(headless=True) as browser:
            context = await browser.new_context_with_session(session_path)
            ...

    On exit: all tracked contexts are closed, then the browser is closed.
    """

    def __init__(
        self,
        headless: bool = True,
        *,
        config: Optional[BrowserConfig] = None,
        extra_args: Optional[list] = None,
    ):
        self._config = config or BrowserConfig(
            headless=headless,
            extra_args=extra_args or [],
        )
        self._playwright = None
        self._browser = None
        self._contexts: list = []

    async def __aenter__(self):
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().__aenter__()
        
        # Connect to Windows Edge via CDP to avoid captchas
        cdp_url = "http://127.0.0.1:9222"
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url, timeout=5000)
        except Exception:
            print(f"  ⚠ Connection refused. Auto-launching Jarvis Edge on Windows...")
            import asyncio
            try:
                # Kill existing Edge processes before starting a new debugging session
                kill_cmd = '/mnt/c/Windows/System32/taskkill.exe /F /IM msedge.exe'
                proc1 = await asyncio.create_subprocess_shell(kill_cmd, stderr=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL)
                await proc1.communicate()
                await asyncio.sleep(2)
                
                cmd = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -WindowStyle Normal -Command "Start-Process \'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe\' -ArgumentList \'--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\\JarvisEdgeProfile\'"'
                proc2 = await asyncio.create_subprocess_shell(cmd)
                await proc2.communicate()
                await asyncio.sleep(6) # Wait for Edge to fully open and start CDP server
                
                self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url, timeout=10000)
                print("  ✅ Successfully auto-launched and connected!")
            except Exception as ex:
                print(f"  ❌ Auto-launch failed: {ex}")
                raise

        return self

    async def __aexit__(self, *exc_info):
        for ctx in self._contexts:
            await safe_close_async(ctx)
        self._contexts.clear()
        await safe_close_async(self._browser)
        if self._playwright:
            await self._playwright.stop()

    @property
    def browser(self):
        return self._browser

    async def new_context(self, session_path: Optional[Path] = None) -> object:
        """Create a new context, optionally loading a saved session."""
        ctx = await self._browser.new_context(
            **self._config.context_kwargs(session_path)
        )
        self._contexts.append(ctx)

        # Inject stealth.min.js to bypass Akamai/Cloudflare bot protection
        stealth_path = Path(__file__).parent / "automations" / "job-automation" / "stealth.min.js"
        if stealth_path.exists():
            await ctx.add_init_script(path=str(stealth_path))

        return ctx

    async def new_context_with_session(
        self, session_path: Path
    ) -> object:
        """Alias: create context and log session loading."""
        if session_path.exists():
            print(f"\n💾 Loading saved session from {session_path.name}")
        return await self.new_context(session_path)

    async def save_session(self, context, session_path: Path) -> None:
        """Persist the context's storage_state to disk."""
        try:
            await context.storage_state(path=str(session_path))
            print(f"  💾 Session saved → {session_path.name}")
        except Exception as e:
            print(f"  ⚠️  Could not save session: {e}")

    def track_context(self, context) -> object:
        """Manually track a context for cleanup in __aexit__."""
        self._contexts.append(context)
        return context


# ── Sync browser helper (pinterest, linkedin, workday) ───────────────────────

class SyncBrowser:
    """Context manager wrapping sync Playwright lifecycle.

    Usage:
        with SyncBrowser(headless=False) as browser:
            context = browser.launch_persistent(user_data_dir)
            page = context.pages[0] or context.new_page()
            ...

    On exit: all tracked contexts are closed.
    """

    def __init__(
        self,
        headless: bool = True,
        *,
        config: Optional[BrowserConfig] = None,
        extra_args: Optional[list] = None,
    ):
        self._config = config or BrowserConfig(
            headless=headless,
            extra_args=extra_args or [],
        )
        self._playwright = None
        self._contexts: list = []

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw_manager = sync_playwright()
        self._playwright = self._pw_manager.__enter__()
        return self

    def __exit__(self, *exc_info):
        for ctx in self._contexts:
            safe_close_sync(ctx)
        self._contexts.clear()
        if self._pw_manager:
            self._pw_manager.__exit__(*exc_info)

    def new_context(self, session_path: Optional[Path] = None):
        """Create a new non-persistent context."""
        cdp_url = "http://127.0.0.1:9222"
        try:
            browser = self._playwright.chromium.connect_over_cdp(cdp_url, timeout=5000)
        except Exception:
            print(f"  ⚠ Connection refused. Auto-launching Jarvis Edge on Windows...")
            import subprocess
            import time
            try:
                # Kill existing Edge processes before starting a new debugging session
                kill_cmd = ['/mnt/c/Windows/System32/taskkill.exe', '/F', '/IM', 'msedge.exe']
                subprocess.run(kill_cmd, shell=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                time.sleep(2)
                
                cmd = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-WindowStyle', 'Normal', '-Command', "Start-Process 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' -ArgumentList '--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\\JarvisEdgeProfile'"]
                subprocess.run(cmd, shell=False)
                time.sleep(6) # Wait for Edge to fully open and start CDP server
                
                browser = self._playwright.chromium.connect_over_cdp(cdp_url, timeout=10000)
                print("  ✅ Successfully auto-launched and connected!")
            except Exception as ex:
                print(f"  ❌ Auto-launch failed: {ex}")
                raise
        ctx = browser.new_context(
            **self._config.context_kwargs(session_path)
        )

        # Inject stealth.min.js
        stealth_path = Path(__file__).parent / "automations" / "job-automation" / "stealth.min.js"
        if stealth_path.exists():
            ctx.add_init_script(path=str(stealth_path))

        # Track both browser and context for cleanup
        self._contexts.append(ctx)
        # We store the browser so we can close it when the context is done
        ctx._jarvis_browser = browser
        return ctx

    def launch_persistent(
        self,
        user_data_dir: str | os.PathLike,
        extra_kwargs: Optional[dict] = None,
    ):
        """Launch a persistent context (cookies/cache survive between runs)."""
        cdp_url = "http://127.0.0.1:9222"
        try:
            self._browser = self._playwright.chromium.connect_over_cdp(cdp_url, timeout=5000)
        except Exception:
            print(f"  ⚠ Connection refused. Auto-launching Jarvis Edge on Windows...")
            import subprocess
            import time
            try:
                # Kill existing Edge processes before starting a new debugging session
                kill_cmd = ['/mnt/c/Windows/System32/taskkill.exe', '/F', '/IM', 'msedge.exe']
                subprocess.run(kill_cmd, shell=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                time.sleep(2)
                
                cmd = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-WindowStyle', 'Normal', '-Command', "Start-Process 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' -ArgumentList '--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\\JarvisEdgeProfile'"]
                subprocess.run(cmd, shell=False)
                time.sleep(6) # Wait for Edge to fully open and start CDP server
                
                self._browser = self._playwright.chromium.connect_over_cdp(cdp_url, timeout=10000)
                print("  ✅ Successfully auto-launched and connected!")
            except Exception as ex:
                print(f"  ❌ Auto-launch failed: {ex}")
                raise
                
        ctx = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        self._contexts.append(ctx)
        return ctx

    def save_session(self, context, session_path: Path) -> None:
        """Persist the context's storage_state to disk (sync version)."""
        try:
            context.storage_state(path=str(session_path))
            print(f"  💾 Session saved → {session_path.name}")
        except Exception as e:
            print(f"  ⚠️  Could not save session: {e}")
