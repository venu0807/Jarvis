#!/usr/bin/env python3
"""
browser_pool.py — Browser Context Pool for JARVIS.

Manages a pool of warmed Playwright browser contexts for instant job execution.
"""

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional, Deque, List
from playwright.async_api import BrowserContext, Browser
from browser import AsyncBrowser


@dataclass
class PooledContext:
    """A pooled browser context with metadata."""
    context: BrowserContext
    created_at: float = field(default_factory=lambda: __import__("time").time())
    last_used: float = field(default_factory=lambda: __import__("time").time())
    in_use: bool = False
    portal: Optional[str] = None


class BrowserPool:
    """
    Pool of warmed browser contexts for instant reuse.
    
    Instead of cold-launching a browser for each job (15s),
    we maintain a pool of pre-warmed contexts (~50MB each).
    """
    
    def __init__(
        self, 
        browser: AsyncBrowser, 
        pool_size: int = 5,
        max_idle_time: int = 300  # 5 minutes
    ):
        self.browser = browser
        self.pool_size = pool_size
        self.max_idle_time = max_idle_time
        self._pool: Deque[PooledContext] = deque()
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Pre-warm the pool with contexts."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            for _ in range(self.pool_size):
                context = await self.browser.new_context()
                self._pool.append(PooledContext(context=context))
            
            self._initialized = True
    
    @asynccontextmanager
    async def acquire(self, portal: Optional[str] = None):
        """
        Acquire a context from the pool.
        
        Returns a warmed context instantly. If pool is empty,
        creates a new context (slower but functional).
        """
        await self.initialize()
        
        async with self._lock:
            # Find available context
            context = None
            for pooled in self._pool:
                if not pooled.in_use:
                    context = pooled
                    break
            
            if context is None:
                # Pool exhausted - create new context
                new_context = await self.browser.new_context()
                context = PooledContext(context=new_context)
                self._pool.append(context)
            
            context.in_use = True
            context.last_used = __import__("time").time()
            context.portal = portal
        
        try:
            yield context.context
        finally:
            # Return to pool
            context.in_use = False
            context.last_used = __import__("time").time()
            context.portal = None
            
            # Cleanup old contexts
            await self._cleanup_idle()
    
    async def _cleanup_idle(self):
        """Remove contexts that have been idle too long."""
        import time
        now = time.time()
        
        # Keep at least pool_size contexts
        while len(self._pool) > self.pool_size:
            oldest = self._pool[0]
            if not oldest.in_use and (now - oldest.last_used) > self.max_idle_time:
                try:
                    await oldest.context.close()
                except Exception:
                    pass
                self._pool.popleft()
            else:
                break
    
    async def close_all(self):
        """Close all pooled contexts."""
        async with self._lock:
            for pooled in self._pool:
                try:
                    await pooled.context.close()
                except Exception:
                    pass
            self._pool.clear()
            self._initialized = False
    
    def stats(self) -> dict:
        """Get pool statistics."""
        in_use = sum(1 for c in self._pool if c.in_use)
        return {
            "total": len(self._pool),
            "in_use": in_use,
            "available": len(self._pool) - in_use,
            "pool_size": self.pool_size
        }


class PooledBrowser:
    """AsyncBrowser wrapper with built-in context pooling."""
    
    def __init__(self, headless: bool = True, pool_size: int = 5):
        self.browser = AsyncBrowser(headless=headless)
        self.pool = BrowserPool(self.browser, pool_size=pool_size)
    
    async def __aenter__(self) -> "PooledBrowser":
        await self.browser.start()
        await self.pool.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pool.close_all()
        await self.browser.close()
    
    @asynccontextmanager
    async def acquire_context(self, portal: Optional[str] = None):
        """Acquire a pooled context."""
        async with self.pool.acquire(portal) as context:
            yield context
    
    def new_context(self, **kwargs) -> BrowserContext:
        """Create a new unpooled context (for special cases)."""
        return self.browser.new_context(**kwargs)
    
    async def save_session(self, context: BrowserContext, session_file: str):
        """Save session state."""
        await self.browser.save_session(context, session_file)


# Convenience function for quick scripts
async def run_with_pool(coro, headless: bool = True, pool_size: int = 5):
    """Run a coroutine with a pooled browser."""
    async with PooledBrowser(headless=headless, pool_size=pool_size) as browser:
        return await coro(browser)