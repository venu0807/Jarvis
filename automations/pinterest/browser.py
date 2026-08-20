"""
Pinterest-specific browser module - re-exports from shared automations browser module.
This exists to satisfy imports that expect browser.py in the pinterest directory.
"""

import sys
import os
import importlib.util
from typing import Any

# Get the path to the shared browser module (parent directory)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
shared_browser_path = os.path.join(parent_dir, "browser.py")

# Load the shared browser module directly from file path to avoid circular import
spec = importlib.util.spec_from_file_location("shared_browser", shared_browser_path)
shared_browser = importlib.util.module_from_spec(spec)
sys.modules["shared_browser"] = shared_browser
spec.loader.exec_module(shared_browser)

# Re-export all symbols from shared browser
AsyncBrowser = shared_browser.AsyncBrowser
SyncBrowser = shared_browser.SyncBrowser
BrowserConfig = shared_browser.BrowserConfig
build_context_kwargs = shared_browser.build_context_kwargs
safe_close_sync = shared_browser.safe_close_sync
safe_close_async = shared_browser.safe_close_async
DEFAULT_USER_AGENT = shared_browser.DEFAULT_USER_AGENT
DEFAULT_VIEWPORT = shared_browser.DEFAULT_VIEWPORT
DEFAULT_LOCALE = shared_browser.DEFAULT_LOCALE
BROWSER_LAUNCH_ARGS = shared_browser.BROWSER_LAUNCH_ARGS

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