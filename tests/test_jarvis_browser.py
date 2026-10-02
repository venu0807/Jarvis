"""
Unit tests for jarvis_browser.py — shared Playwright utility.

Focus areas:
  - BrowserConfig dataclass defaults and helpers
  - build_context_kwargs() standalone function
  - safe_close_async / safe_close_sync error-tolerant close helpers
  - AsyncBrowser / SyncBrowser constructor & config wiring
  - Context manager lifecycle (mocked — no real browser required)

Run:
    pytest tests/test_jarvis_browser.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# Add project root so jarvis_browser is importable
PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_ROOT))

# ── Module under test ─────────────────────────────────────────────────────────
import jarvis_browser as jb


# ==============================================================================
# BrowserConfig unit tests
# ==============================================================================

class TestBrowserConfig:
    """BrowserConfig dataclass — defaults, launch_args(), context_kwargs()."""

    def test_defaults_headless_true(self):
        """Default config is headless."""
        cfg = jb.BrowserConfig()
        assert cfg.headless is True

    def test_default_user_agent(self):
        """Default UA matches the shared constant."""
        cfg = jb.BrowserConfig()
        assert cfg.user_agent == jb.DEFAULT_USER_AGENT

    def test_default_viewport(self):
        """Default viewport matches the shared constant."""
        cfg = jb.BrowserConfig()
        assert cfg.viewport == jb.DEFAULT_VIEWPORT

    def test_default_locale(self):
        """Default locale is en-IN."""
        cfg = jb.BrowserConfig()
        assert cfg.locale == "en-IN"

    def test_custom_headless(self):
        """Can override headless to False."""
        cfg = jb.BrowserConfig(headless=False)
        assert cfg.headless is False

    def test_custom_user_agent(self):
        """Can override user agent."""
        ua = "Custom/1.0"
        cfg = jb.BrowserConfig(user_agent=ua)
        assert cfg.user_agent == ua

    def test_custom_viewport(self):
        """Can override viewport."""
        vp = {"width": 1920, "height": 1080}
        cfg = jb.BrowserConfig(viewport=vp)
        assert cfg.viewport == vp

    def test_custom_locale(self):
        """Can override locale."""
        cfg = jb.BrowserConfig(locale="en-US")
        assert cfg.locale == "en-US"

    def test_extra_args(self):
        """Extra args are stored and included in launch_args()."""
        cfg = jb.BrowserConfig(extra_args=["--foo", "--bar"])
        args = cfg.launch_args()
        assert "--foo" in args
        assert "--bar" in args

    # ── launch_args() ───────────────────────────────────────────────────────

    def test_launch_args_includes_standard(self):
        """launch_args always contains the standard BROWSER_LAUNCH_ARGS."""
        cfg = jb.BrowserConfig()
        args = cfg.launch_args()
        for standard in jb.BROWSER_LAUNCH_ARGS:
            assert standard in args

    def test_launch_args_headless_no_window_position(self):
        """Headless mode does NOT include --window-position."""
        cfg = jb.BrowserConfig(headless=True)
        args = cfg.launch_args()
        assert "--window-position=0,2000" not in args

    def test_launch_args_headful_includes_window_position(self):
        """Headful mode includes --window-position=0,2000 to push off-screen."""
        cfg = jb.BrowserConfig(headless=False)
        args = cfg.launch_args()
        assert "--window-position=0,2000" in args

    def test_launch_args_preserves_order(self):
        """Standard args come first, then extra_args."""
        cfg = jb.BrowserConfig(extra_args=["--custom"])
        args = cfg.launch_args()
        # Standard args should appear before the custom arg
        std_idx = [args.index(a) for a in jb.BROWSER_LAUNCH_ARGS if a in args]
        custom_idx = args.index("--custom")
        assert all(i < custom_idx for i in std_idx)

    # ── context_kwargs() ────────────────────────────────────────────────────

    def test_context_kwargs_basic(self):
        """context_kwargs returns user_agent, viewport, locale."""
        cfg = jb.BrowserConfig()
        kwargs = cfg.context_kwargs()
        assert kwargs["user_agent"] == jb.DEFAULT_USER_AGENT
        assert kwargs["viewport"] == jb.DEFAULT_VIEWPORT
        assert kwargs["locale"] == jb.DEFAULT_LOCALE

    def test_context_kwargs_returns_copy_of_viewport(self):
        """viewport in kwargs is a dict copy, not a reference."""
        cfg = jb.BrowserConfig()
        kwargs = cfg.context_kwargs()
        kwargs["viewport"]["width"] = 9999
        # Original should be unchanged
        assert cfg.viewport["width"] == 1366

    def test_context_kwargs_with_existing_session(self, tmp_path):
        """When session_path exists, storage_state is included."""
        session_file = tmp_path / "session.json"
        session_file.write_text("{}")
        cfg = jb.BrowserConfig()
        kwargs = cfg.context_kwargs(storage_state_path=session_file)
        assert "storage_state" in kwargs
        assert kwargs["storage_state"] == str(session_file)

    def test_context_kwargs_with_missing_session(self, tmp_path):
        """When session_path does not exist, no storage_state in kwargs."""
        missing = tmp_path / "nonexistent.json"
        cfg = jb.BrowserConfig()
        kwargs = cfg.context_kwargs(storage_state_path=missing)
        assert "storage_state" not in kwargs

    def test_context_kwargs_with_none_session(self):
        """When session_path is None, no storage_state in kwargs."""
        cfg = jb.BrowserConfig()
        kwargs = cfg.context_kwargs(storage_state_path=None)
        assert "storage_state" not in kwargs


# ==============================================================================
# build_context_kwargs unit tests
# ==============================================================================

class TestBuildContextKwargs:
    """Standalone build_context_kwargs() helper."""

    def test_defaults(self):
        """Returns default user_agent, viewport, locale."""
        kwargs = jb.build_context_kwargs()
        assert kwargs["user_agent"] == jb.DEFAULT_USER_AGENT
        assert kwargs["viewport"] == jb.DEFAULT_VIEWPORT
        assert kwargs["locale"] == jb.DEFAULT_LOCALE

    def test_custom_ua(self):
        """Accepts custom user_agent."""
        kwargs = jb.build_context_kwargs(user_agent="Custom/2.0")
        assert kwargs["user_agent"] == "Custom/2.0"

    def test_custom_viewport(self):
        """Accepts custom viewport."""
        vp = {"width": 800, "height": 600}
        kwargs = jb.build_context_kwargs(viewport=vp)
        assert kwargs["viewport"] == vp

    def test_custom_locale(self):
        """Accepts custom locale."""
        kwargs = jb.build_context_kwargs(locale="fr-FR")
        assert kwargs["locale"] == "fr-FR"

    def test_with_existing_session(self, tmp_path):
        """Existing session_path adds storage_state."""
        sf = tmp_path / "s.json"
        sf.write_text("{}")
        kwargs = jb.build_context_kwargs(session_path=sf)
        assert kwargs["storage_state"] == str(sf)

    def test_with_missing_session(self, tmp_path):
        """Missing session_path does not add storage_state."""
        sf = tmp_path / "missing.json"
        kwargs = jb.build_context_kwargs(session_path=sf)
        assert "storage_state" not in kwargs

    def test_viewport_default_not_mutated(self):
        """Subsequent calls don't share the same viewport dict."""
        a = jb.build_context_kwargs()
        b = jb.build_context_kwargs()
        a["viewport"]["width"] = 0
        assert b["viewport"]["width"] == 1366


# ==============================================================================
# safe_close_async / safe_close_sync unit tests
# ==============================================================================

class TestSafeCloseAsync:
    """safe_close_async — error-tolerant async close."""

    @pytest.mark.asyncio
    async def test_none_does_nothing(self):
        """Passing None should not raise."""
        await jb.safe_close_async(None)

    @pytest.mark.asyncio
    async def test_closes_valid_object(self):
        """Calls close() on an object that has it."""
        obj = AsyncMock()
        await jb.safe_close_async(obj)
        obj.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_swallows_exception(self):
        """Does not raise if close() raises."""
        obj = AsyncMock()
        obj.close.side_effect = RuntimeError("boom")
        await jb.safe_close_async(obj)  # should not propagate

    @pytest.mark.asyncio
    async def test_no_close_attr(self):
        """Objects without close() are silently ignored."""
        obj = object()
        await jb.safe_close_async(obj)  # should not raise

    @pytest.mark.asyncio
    async def test_non_callable_close(self):
        """Objects with a non-callable close attribute are silently ignored."""
        obj = MagicMock()
        obj.close = "not callable"
        await jb.safe_close_async(obj)  # should not raise

    @pytest.mark.asyncio
    async def test_does_not_swallow_base_exception(self):
        """Does not swallow BaseExceptions like KeyboardInterrupt."""
        obj = AsyncMock()
        obj.close.side_effect = KeyboardInterrupt("Ctrl-C")
        with pytest.raises(KeyboardInterrupt):
            await jb.safe_close_async(obj)


class TestSafeCloseSync:
    """safe_close_sync — error-tolerant sync close."""

    def test_none_does_nothing(self):
        """Passing None should not raise."""
        jb.safe_close_sync(None)

    def test_closes_valid_object(self):
        """Calls close() on an object that has it."""
        obj = MagicMock()
        jb.safe_close_sync(obj)
        obj.close.assert_called_once()

    def test_swallows_exception(self):
        """Does not raise if close() raises."""
        obj = MagicMock()
        obj.close.side_effect = RuntimeError("boom")
        jb.safe_close_sync(obj)  # should not propagate

    def test_no_close_attr(self):
        """Objects without close() are silently ignored."""
        jb.safe_close_sync(object())  # should not raise

    def test_non_callable_close(self):
        """Objects with a non-callable close attribute are silently ignored."""
        obj = MagicMock()
        obj.close = "not callable"
        jb.safe_close_sync(obj)  # should not raise

    def test_does_not_swallow_base_exception(self):
        """Does not swallow BaseExceptions like KeyboardInterrupt."""
        obj = MagicMock()
        obj.close.side_effect = KeyboardInterrupt("Ctrl-C")
        with pytest.raises(KeyboardInterrupt):
            jb.safe_close_sync(obj)


# ==============================================================================
# AsyncBrowser unit tests (mocked Playwright)
# ==============================================================================

@pytest.fixture
def mock_async_playwright():
    """
    Inject fake playwright.async_api into sys.modules before the lazy import
    inside AsyncBrowser.__aenter__ executes.

    The real `async_playwright()` is a REGULAR function that returns an async
    context manager — it is called WITHOUT `await`.  The return value is then
    used with `async with`, which calls `__aenter__()` on it.

    Mock chain:
      async_playwright()                    → context_manager (MagicMock)
      await context_manager.__aenter__()    → mock_playwright (AsyncMock)
      await mock_playwright.chromium.launch() → mock_browser (AsyncMock)
    """
    mock_browser = AsyncMock()

    # The playwright instance returned by `await __aenter__()`
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    # Context manager object returned by `async_playwright()` (no await)
    context_manager = MagicMock()
    context_manager.__aenter__.return_value = mock_playwright
    context_manager.__aexit__.return_value = None

    # `async_playwright` is a regular callable that returns the context manager
    mock_module = MagicMock()
    mock_module.async_playwright = MagicMock(return_value=context_manager)

    with patch.dict("sys.modules") as modules:
        modules["playwright"] = MagicMock()
        modules["playwright.async_api"] = mock_module
        yield {
            "playwright_mock": mock_playwright,
            "browser_mock": mock_browser,
        }


class TestAsyncBrowser:
    """AsyncBrowser — initialization and context manager."""

    @pytest.mark.asyncio
    async def test_constructor_defaults(self):
        """Default config uses headless=True and empty extra_args."""
        browser = jb.AsyncBrowser()
        assert browser._config.headless is True
        assert browser._config.extra_args == []

    @pytest.mark.asyncio
    async def test_constructor_custom_headless(self):
        """Can set headless=False."""
        browser = jb.AsyncBrowser(headless=False)
        assert browser._config.headless is False

    @pytest.mark.asyncio
    async def test_constructor_extra_args(self):
        """Can pass extra args."""
        browser = jb.AsyncBrowser(extra_args=["--foo"])
        assert "--foo" in browser._config.extra_args

    @pytest.mark.asyncio
    async def test_browser_property(self, mock_async_playwright):
        """browser property returns the launched browser."""
        async with jb.AsyncBrowser() as browser_mgr:
            assert browser_mgr.browser is not None

    @pytest.mark.asyncio
    async def test_new_context(self, mock_async_playwright):
        """new_context creates a context via the browser."""
        mock_browser = mock_async_playwright["browser_mock"]
        mock_ctx = AsyncMock()
        mock_browser.new_context.return_value = mock_ctx

        async with jb.AsyncBrowser() as browser_mgr:
            ctx = await browser_mgr.new_context()
            assert ctx is not None
            mock_browser.new_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_context_tracks_for_cleanup(self, mock_async_playwright):
        """new_context adds the context to _contexts list."""
        mock_browser = mock_async_playwright["browser_mock"]
        mock_browser.new_context.return_value = AsyncMock()

        async with jb.AsyncBrowser() as browser_mgr:
            ctx = await browser_mgr.new_context()
            assert ctx in browser_mgr._contexts

    @pytest.mark.asyncio
    async def test_new_context_with_session_logs_when_exists(self, mock_async_playwright, capsys, tmp_path):
        """new_context_with_session prints a log message when session exists."""
        session_file = tmp_path / "test.json"
        session_file.write_text("{}")
        mock_browser = mock_async_playwright["browser_mock"]
        mock_browser.new_context.return_value = AsyncMock()

        async with jb.AsyncBrowser() as browser_mgr:
            await browser_mgr.new_context_with_session(session_file)

        captured = capsys.readouterr()
        assert "Loading saved session" in captured.out

    @pytest.mark.asyncio
    async def test_new_context_with_session_missing(self, mock_async_playwright, capsys, tmp_path):
        """new_context_with_session does not log when session missing."""
        missing = tmp_path / "missing.json"

        async with jb.AsyncBrowser() as browser_mgr:
            await browser_mgr.new_context_with_session(missing)

        captured = capsys.readouterr()
        assert "Loading saved session" not in captured.out

    @pytest.mark.asyncio
    async def test_save_session(self, mock_async_playwright, tmp_path):
        """save_session calls storage_state on the context."""
        mock_ctx = AsyncMock()
        session_file = tmp_path / "saved.json"

        async with jb.AsyncBrowser() as browser_mgr:
            await browser_mgr.save_session(mock_ctx, session_file)

        mock_ctx.storage_state.assert_awaited_once_with(path=str(session_file))

    @pytest.mark.asyncio
    async def test_save_session_handles_error(self, mock_async_playwright, capsys, tmp_path):
        """save_session prints a warning on error, doesn't raise."""
        mock_ctx = AsyncMock()
        mock_ctx.storage_state.side_effect = RuntimeError("permission denied")
        session_file = tmp_path / "saved.json"

        async with jb.AsyncBrowser() as browser_mgr:
            await browser_mgr.save_session(mock_ctx, session_file)

        captured = capsys.readouterr()
        assert "Could not save session" in captured.out

    @pytest.mark.asyncio
    async def test_track_context(self, mock_async_playwright):
        """track_context adds a context to the cleanup list."""
        ctx = AsyncMock()
        async with jb.AsyncBrowser() as browser_mgr:
            browser_mgr.track_context(ctx)
            assert ctx in browser_mgr._contexts

    @pytest.mark.asyncio
    async def test_aexit_closes_contexts(self, mock_async_playwright):
        """__aexit__ closes all tracked contexts."""
        mock_browser = mock_async_playwright["browser_mock"]
        mock_ctx = AsyncMock()
        mock_browser.new_context.return_value = mock_ctx

        async with jb.AsyncBrowser() as browser_mgr:
            await browser_mgr.new_context()

        # After exit, the context should have been closed
        mock_ctx.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_cleanup_on_exception(self, mock_async_playwright):
        """__aexit__ still closes contexts even when an exception occurs."""
        mock_browser = mock_async_playwright["browser_mock"]
        mock_ctx = AsyncMock()
        mock_browser.new_context.return_value = mock_ctx

        with pytest.raises(RuntimeError):
            async with jb.AsyncBrowser() as browser_mgr:
                await browser_mgr.new_context()
                raise RuntimeError("pipeline error")

        # Context should still be closed despite the exception
        mock_ctx.close.assert_awaited_once()


# ==============================================================================
# SyncBrowser unit tests (mocked Playwright)
# ==============================================================================

@pytest.fixture
def mock_sync_playwright():
    """
    Inject fake playwright.sync_api into sys.modules before the lazy import
    inside SyncBrowser.__enter__ executes (same rationale as the async fixture).
    """
    mock_context = MagicMock()
    mock_browser = MagicMock()

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_playwright.chromium.launch_persistent_context.return_value = mock_context
    mock_browser.new_context.return_value = MagicMock()

    # The lazy import resolves to `sync_playwright` — a callable that returns
    # a regular context manager.
    mock_sync_playwright_fn = MagicMock()
    mock_sync_playwright_fn.return_value.__enter__.return_value = mock_playwright

    mock_module = MagicMock()
    mock_module.sync_playwright = mock_sync_playwright_fn

    with patch.dict("sys.modules") as modules:
        modules["playwright"] = MagicMock()
        modules["playwright.sync_api"] = mock_module
        yield {
            "playwright_mock": mock_playwright,
            "browser_mock": mock_browser,
            "context_mock": mock_context,
        }


class TestSyncBrowser:
    """SyncBrowser — initialization and context manager."""

    def test_constructor_defaults(self):
        """Default config uses headless=True and empty extra_args."""
        browser = jb.SyncBrowser()
        assert browser._config.headless is True
        assert browser._config.extra_args == []

    def test_constructor_custom_headless(self):
        """Can set headless=False."""
        browser = jb.SyncBrowser(headless=False)
        assert browser._config.headless is False

    def test_constructor_extra_args(self):
        """Can pass extra args."""
        browser = jb.SyncBrowser(extra_args=["--foo"])
        assert "--foo" in browser._config.extra_args

    def test_launch_persistent(self, mock_sync_playwright):
        """launch_persistent creates a persistent context."""
        mock_pw = mock_sync_playwright["playwright_mock"]
        mock_ctx = mock_sync_playwright["context_mock"]

        with jb.SyncBrowser() as browser_mgr:
            ctx = browser_mgr.launch_persistent("/tmp/test_profile")

            assert ctx is mock_ctx
            mock_pw.chromium.launch_persistent_context.assert_called_once()
            args, kwargs = mock_pw.chromium.launch_persistent_context.call_args
            assert kwargs["user_data_dir"] == "/tmp/test_profile"

    def test_launch_persistent_extra_kwargs(self, mock_sync_playwright):
        """launch_persistent merges extra_kwargs into the launch call."""
        mock_pw = mock_sync_playwright["playwright_mock"]

        with jb.SyncBrowser() as browser_mgr:
            browser_mgr.launch_persistent(
                "/tmp/test_profile",
                extra_kwargs={"viewport": {"width": 800, "height": 600}},
            )

        args, kwargs = mock_pw.chromium.launch_persistent_context.call_args
        assert kwargs["viewport"] == {"width": 800, "height": 600}

    def test_launch_persistent_tracks_context(self, mock_sync_playwright):
        """launch_persistent adds the context to _contexts for cleanup."""
        with jb.SyncBrowser() as browser_mgr:
            ctx = browser_mgr.launch_persistent("/tmp/test_profile")
            assert ctx in browser_mgr._contexts

    def test_new_context_non_persistent(self, mock_sync_playwright):
        """new_context creates a non-persistent context."""
        mock_pw = mock_sync_playwright["playwright_mock"]

        with jb.SyncBrowser() as browser_mgr:
            browser_mgr.new_context()

        mock_pw.chromium.launch.assert_called_once()

    def test_new_context_with_session_path(self, mock_sync_playwright, tmp_path):
        """new_context passes session_path through to context_kwargs."""
        mock_pw = mock_sync_playwright["playwright_mock"]
        mock_browser = mock_sync_playwright["browser_mock"]
        mock_browser.new_context.return_value = MagicMock()

        session_file = tmp_path / "session.json"
        session_file.write_text("{}")

        with jb.SyncBrowser() as browser_mgr:
            ctx = browser_mgr.new_context(session_file)

        # check that launch was called, then new_context with storage_state
        mock_pw.chromium.launch.assert_called_once()
        call_kwargs = mock_browser.new_context.call_args.kwargs
        assert "storage_state" in call_kwargs
        assert call_kwargs["storage_state"] == str(session_file)

    def test_exit_closes_contexts(self, mock_sync_playwright):
        """__exit__ closes all tracked contexts."""
        mock_ctx = mock_sync_playwright["context_mock"]

        with jb.SyncBrowser() as browser_mgr:
            browser_mgr.launch_persistent("/tmp/test_profile")

        # After exit, the context should have been closed
        mock_ctx.close.assert_called_once()

    def test_exit_cleanup_on_exception(self, mock_sync_playwright):
        """__exit__ still closes contexts even when an exception occurs."""
        mock_ctx = mock_sync_playwright["context_mock"]

        with pytest.raises(RuntimeError):
            with jb.SyncBrowser() as browser_mgr:
                browser_mgr.launch_persistent("/tmp/test_profile")
                raise RuntimeError("sync error")

        # Context should still be closed despite the exception
        mock_ctx.close.assert_called_once()

    def test_save_session(self, mock_sync_playwright, tmp_path):
        """save_session calls storage_state on the context (sync)."""
        mock_ctx = mock_sync_playwright["context_mock"]
        session_file = tmp_path / "saved.json"

        with jb.SyncBrowser() as browser_mgr:
            browser_mgr.save_session(mock_ctx, session_file)

        mock_ctx.storage_state.assert_called_once_with(path=str(session_file))

    def test_save_session_handles_error(self, mock_sync_playwright, capsys, tmp_path):
        """save_session prints a warning on error, doesn't raise."""
        mock_ctx = mock_sync_playwright["context_mock"]
        mock_ctx.storage_state.side_effect = RuntimeError("sync error")
        session_file = tmp_path / "saved.json"

        with jb.SyncBrowser() as browser_mgr:
            browser_mgr.save_session(mock_ctx, session_file)

        captured = capsys.readouterr()
        assert "Could not save session" in captured.out


# ==============================================================================
# Constants
# ==============================================================================

class TestConstants:
    """Verify exported constants match expected values."""

    def test_default_user_agent_contains_chrome(self):
        """UA should be a realistic Chrome UA string."""
        assert "Chrome/124" in jb.DEFAULT_USER_AGENT
        assert "Windows NT" in jb.DEFAULT_USER_AGENT

    def test_default_viewport(self):
        """Default viewport should be 1366x768."""
        assert jb.DEFAULT_VIEWPORT == {"width": 1366, "height": 768}

    def test_default_locale(self):
        """Default locale is en-IN."""
        assert jb.DEFAULT_LOCALE == "en-IN"

    def test_browser_launch_args(self):
        """Standard args should contain no-sandbox and disable-dev-shm-usage."""
        assert "--no-sandbox" in jb.BROWSER_LAUNCH_ARGS
        assert "--disable-dev-shm-usage" in jb.BROWSER_LAUNCH_ARGS
        assert "--disable-blink-features=AutomationControlled" in jb.BROWSER_LAUNCH_ARGS
