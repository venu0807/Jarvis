"""
Pinterest-specific browser module - re-exports from shared automations browser module.
This exists to satisfy imports that expect browser.py in the pinterest directory.
"""

import sys
import os
from typing import Any

# Add parent directory to path for shared browser module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import from shared browser module
try:
    from browser import (
        AsyncBrowser,
        SyncBrowser,
        BrowserConfig,
        build_context_kwargs,
        safe_close_sync,
        safe_close_async,
        DEFAULT_USER_AGENT,
        DEFAULT_VIEWPORT,
        DEFAULT_LOCALE,
        BROWSER_LAUNCH_ARGS,
    )
except ImportError:
    # Fallback definitions if shared module not available
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from playwright.sync_api import sync_playwright
    from pathlib import Path
    from typing import Optional, List, Dict
    
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
        def __init__(self, headless: bool = True, slow_mo: int = 0):
            self.headless = headless
            self.slow_mo = slow_mo
    
    def build_context_kwargs(config: BrowserConfig, session_file: Optional[Path | str] = None, **extra) -> Dict[str, Any]:
        kwargs = {"headless": config.headless, "slow_mo": config.slow_mo}
        kwargs.update(extra)
        return kwargs
    
    class AsyncBrowser:
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
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=BROWSER_LAUNCH_ARGS
            )
        
        async def close(self):
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
            if not self._browser:
                raise RuntimeError("Browser not started.")
            defaults = {"viewport": DEFAULT_VIEWPORT, "user_agent": DEFAULT_USER_AGENT}
            if "locale" not in kwargs:
                defaults["locale"] = DEFAULT_LOCALE
            defaults.update(kwargs)
            context = await self._browser.new_context(**defaults)
            self._contexts.append(context)
            return context
        
        async def new_context_with_session(self, session_file: Path | str, **kwargs) -> BrowserContext:
            session_path = Path(session_file)
            if session_path.exists():
                kwargs.setdefault("storage_state", str(session_path))
            return await self.new_context(**kwargs)
        
        async def save_session(self, context: BrowserContext, session_file: Path | str):
            session_path = Path(session_file)
            session_path.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(session_path))
    
    class SyncBrowser:
        def __init__(self, headless: bool = True):
            self.headless = headless
            self._playwright = None
            self._browser = None
        
        def __enter__(self):
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
            defaults = {"viewport": DEFAULT_VIEWPORT, "user_agent": DEFAULT_USER_AGENT}
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
    
    def safe_close_sync(browser_mgr: 'SyncBrowser'):
        """Safely close the browser manager (sync version), handling any exceptions."""
        try:
            browser_mgr.__exit__(None, None, None)
        except Exception as e:
            print(f"⚠️ Error during browser cleanup: {e}")
    
    async def safe_close_async(browser_mgr: AsyncBrowser):
        """Safely close the browser manager, handling any exceptions."""
        try:
            await browser_mgr.close()
        except Exception as e:
            print(f"⚠️ Error during browser cleanup: {e}")

__all__ = [
    "AsyncBrowser",
    "SyncBrowser",
    "BrowserConfig",
    "build_context_kwargs",
    "safe_close_sync",
    "safe_close_async",
    "DEFAULT_USER_AGENT",
    "DEFAULT_VIEWPORT",
    "DEFAULT_LOCALE",
    "BROWSER_LAUNCH_ARGS",
]