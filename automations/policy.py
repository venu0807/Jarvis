#!/usr/bin/env python3
"""
policy.py — JARVIS LLM Policy Engine

Centralizes all LLM interactions with:
- Multi-model routing (via Model Router service or direct Ollama)
- Circuit breaker for Ollama resilience
- Prompt sanitization for security
- Retry logic with CPU offload fallback
- Structured logging with correlation IDs
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal
from pathlib import Path

import httpx
import pybreaker
from prometheus_client import Histogram, Counter, Gauge

from prompt_sanitizer import sanitize_prompt, SanitizationResult

logger = logging.getLogger(__name__)

# Task types for model routing
TaskType = Literal["coding", "reasoning", "embedding", "general", "lightweight", "job_match"]

# Model mapping for direct Ollama fallback (when router is unavailable)
FALLBACK_MODELS: Dict[TaskType, str] = {
    "coding": "qwen2.5-coder:3b-instruct-q4_K_M",
    "reasoning": "llama3.2:3b-instruct-q4_K_M",
    "embedding": "nomic-embed-text:latest",
    "general": "phi4:mini",
    "lightweight": "gemma2:2b-instruct-q4_K_M",
    "job_match": "phi4:mini",  # Fast, good enough for job matching
}

# Metrics
OLLAMA_REQUEST_DURATION = Histogram(
    "ollama_request_duration_seconds",
    "Time spent calling Ollama",
    ["model", "task_type", "fallback"]
)
OLLAMA_REQUESTS_TOTAL = Counter(
    "ollama_requests_total",
    "Total Ollama requests",
    ["model", "task_type", "status"]
)
OLLAMA_FALLBACK_TOTAL = Counter(
    "ollama_fallback_total",
    "Total fallback activations",
    ["reason"]
)
ROUTER_REQUEST_DURATION = Histogram(
    "router_request_duration_seconds",
    "Time spent calling Model Router",
    ["task_type", "status"]
)
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["name"]
)


@dataclass
class LLMResponse:
    """Structured LLM response."""
    content: str
    model: str
    task_type: TaskType
    latency_ms: float
    fallback_used: bool
    fallback_reason: Optional[str] = None
    sanitized: bool = False
    sanitization_result: Optional[SanitizationResult] = None


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class OllamaClient:
    """Ollama API client with circuit breaker and fallback support."""
    
    def __init__(
        self,
        base_url: str = "http://host.docker.internal:11434",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Circuit breaker for Ollama connection
        self.circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
            exclude=[asyncio.TimeoutError],  # Timeouts don't trip breaker
            listeners=[self._cb_listener],
        )
    
    def _cb_listener(self, cb: pybreaker.CircuitBreaker, old_state: str, new_state: str):
        """Log circuit breaker state changes."""
        state_map = {"closed": 0, "open": 1, "half_open": 2}
        CIRCUIT_BREAKER_STATE.labels(name="ollama").set(state_map.get(new_state, 0))
        logger.warning(f"Ollama circuit breaker: {old_state} -> {new_state}")
        OLLAMA_FALLBACK_TOTAL.labels(reason=f"circuit_breaker_{new_state}").inc()
    
    @pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)
    async def _generate_with_breaker(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Internal method wrapped by circuit breaker."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": options or {},
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def generate(
        self,
        model: str,
        prompt: str,
        task_type: TaskType = "general",
        options: Optional[Dict[str, Any]] = None,
        use_cpu_offload: bool = False,
    ) -> LLMResponse:
        """
        Generate with retry, CPU offload fallback, and circuit breaker.
        
        Args:
            model: Model name to use
            prompt: Prompt text
            task_type: Task type for metrics
            options: Ollama options (temperature, etc.)
            use_cpu_offload: Force CPU offload (num_gpu=-1)
        
        Returns:
            LLMResponse with content and metadata
        """
        start_time = time.time()
        fallback_used = False
        fallback_reason = None
        current_model = model
        current_options = options or {}
        
        if use_cpu_offload:
            current_options = {**current_options, "num_gpu": -1}
            fallback_used = True
            fallback_reason = "forced_cpu_offload"
        
        for attempt in range(self.max_retries):
            try:
                result = await self._generate_with_breaker(
                    current_model, prompt, current_options
                )
                latency_ms = (time.time() - start_time) * 1000
                
                OLLAMA_REQUEST_DURATION.labels(
                    model=current_model, task_type=task_type, fallback=str(fallback_used)
                ).observe(latency_ms / 1000)
                OLLAMA_REQUESTS_TOTAL.labels(
                    model=current_model, task_type=task_type, status="success"
                ).inc()
                
                return LLMResponse(
                    content=result.get("response", ""),
                    model=current_model,
                    task_type=task_type,
                    latency_ms=latency_ms,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                )
                
            except pybreaker.CircuitBreakerError:
                # Circuit breaker open - immediate fallback
                if not fallback_used:
                    fallback_used = True
                    fallback_reason = "circuit_breaker_open"
                    current_model = FALLBACK_MODELS.get(task_type, "phi4:mini")
                    current_options = {**current_options, "num_gpu": -1}
                    logger.warning(f"Circuit breaker open, falling back to {current_model} on CPU")
                    continue
                else:
                    raise CircuitBreakerOpen("Circuit breaker open and fallback exhausted")
                    
            except httpx.TimeoutException:
                latency_ms = (time.time() - start_time) * 1000
                OLLAMA_REQUESTS_TOTAL.labels(
                    model=current_model, task_type=task_type, status="timeout"
                ).inc()
                
                if attempt < self.max_retries - 1 and not fallback_used:
                    # Retry with CPU offload
                    fallback_used = True
                    fallback_reason = "timeout_cpu_offload"
                    current_model = FALLBACK_MODELS.get(task_type, "phi4:mini")
                    current_options = {**current_options, "num_gpu": -1}
                    logger.warning(f"Ollama timeout, retrying with CPU offload: {current_model}")
                    await asyncio.sleep(1 * (attempt + 1))  # Backoff
                    continue
                else:
                    raise
                    
            except httpx.ConnectError:
                latency_ms = (time.time() - start_time) * 1000
                OLLAMA_REQUESTS_TOTAL.labels(
                    model=current_model, task_type=task_type, status="connection_error"
                ).inc()
                
                if not fallback_used:
                    fallback_used = True
                    fallback_reason = "connection_error_cpu_offload"
                    current_model = FALLBACK_MODELS.get(task_type, "phi4:mini")
                    current_options = {**current_options, "num_gpu": -1}
                    logger.warning(f"Ollama connection error, falling back to CPU: {current_model}")
                    continue
                else:
                    raise
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Model not found - try to pull or fallback
                    if not fallback_used:
                        fallback_used = True
                        fallback_reason = "model_not_found_fallback"
                        current_model = FALLBACK_MODELS.get(task_type, "phi4:mini")
                        current_options = {**current_options, "num_gpu": -1}
                        logger.warning(f"Model {model} not found (404), falling back to {current_model}")
                        continue
                OLLAMA_REQUESTS_TOTAL.labels(
                    model=current_model, task_type=task_type, status=f"http_{e.response.status_code}"
                ).inc()
                raise
                
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                OLLAMA_REQUESTS_TOTAL.labels(
                    model=current_model, task_type=task_type, status="error"
                ).inc()
                logger.error(f"Ollama error: {type(e).__name__}: {e}")
                raise
        
        # Should not reach here
        raise RuntimeError("Max retries exceeded")


class ModelRouterClient:
    """Client for the Model Router service (FastAPI)."""
    
    def __init__(
        self,
        base_url: str = "http://model-router:8090",
        timeout: float = 5.0,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or os.getenv("MODEL_ROUTER_API_KEY")
    
    async def route(self, task_type: TaskType, prompt: str) -> Dict[str, Any]:
        """Route a task to the best model."""
        start_time = time.time()
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/route",
                    json={"task_type": task_type, "prompt": prompt[:500]},  # Send preview
                    headers=headers,
                )
                response.raise_for_status()
                latency_ms = (time.time() - start_time) * 1000
                ROUTER_REQUEST_DURATION.labels(task_type=task_type, status="success").observe(latency_ms / 1000)
                return response.json()
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            ROUTER_REQUEST_DURATION.labels(task_type=task_type, status="error").observe(latency_ms / 1000)
            logger.warning(f"Model Router error: {e}")
            raise


class LLMPolicy:
    """
    Main policy engine for LLM interactions.
    
    Flow:
    1. Sanitize prompt
    2. Try Model Router (if available)
    3. Fallback to direct Ollama with circuit breaker
    4. Return structured response
    """
    
    def __init__(
        self,
        ollama_url: str = "http://host.docker.internal:11434",
        router_url: Optional[str] = "http://model-router:8090",
        router_api_key: Optional[str] = None,
        enable_router: bool = True,
    ):
        self.ollama = OllamaClient(base_url=ollama_url)
        self.router = ModelRouterClient(base_url=router_url, api_key=router_api_key) if router_url else None
        self.enable_router = enable_router and self.router is not None
        
        # Sanitize all prompts by default
        self.sanitize_prompts = True
    
    async def generate(
        self,
        prompt: str,
        task_type: TaskType = "general",
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        sanitize: bool = True,
    ) -> LLMResponse:
        """
        Generate using the policy engine.
        
        Args:
            prompt: Input prompt
            task_type: Type of task (affects model selection)
            model: Explicit model override (bypasses router)
            options: Ollama options
            sanitize: Whether to sanitize the prompt
        
        Returns:
            LLMResponse with content and metadata
        """
        # Step 1: Sanitize prompt
        sanitization_result = None
        if sanitize and self.sanitize_prompts:
            sanitization_result = sanitize_prompt(prompt)
            prompt = sanitization_result.sanitized
        
        # Step 2: Determine model
        if model is None and self.enable_router and self.router:
            try:
                route_result = await self.router.route(task_type, prompt)
                model = route_result.get("model", FALLBACK_MODELS.get(task_type, "phi4:mini"))
                logger.info(f"Router selected model: {model} for task_type={task_type}")
            except Exception as e:
                logger.warning(f"Router failed, using fallback: {e}")
                model = FALLBACK_MODELS.get(task_type, "phi4:mini")
        elif model is None:
            model = FALLBACK_MODELS.get(task_type, "phi4:mini")
        
        # Step 3: Generate with Ollama (includes fallback logic)
        response = await self.ollama.generate(
            model=model,
            prompt=prompt,
            task_type=task_type,
            options=options,
        )
        
        # Attach sanitization info
        response.sanitized = sanitize and self.sanitize_prompts
        response.sanitization_result = sanitization_result
        
        return response
    
    async def generate_simple(self, prompt: str, task_type: TaskType = "general") -> str:
        """Simple interface returning just the content string."""
        response = await self.generate(prompt, task_type)
        return response.content


# Global policy instance (lazy initialization)
_policy_instance: Optional[LLMPolicy] = None


def get_policy() -> LLMPolicy:
    """Get or create the global policy instance."""
    global _policy_instance
    if _policy_instance is None:
        _policy_instance = LLMPolicy(
            ollama_url=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
            router_url=os.getenv("MODEL_ROUTER_URL"),
            router_api_key=os.getenv("MODEL_ROUTER_API_KEY"),
            enable_router=os.getenv("ENABLE_MODEL_ROUTER", "true").lower() == "true",
        )
    return _policy_instance


async def generate_with_policy(
    prompt: str,
    task_type: TaskType = "general",
    **kwargs,
) -> str:
    """Convenience function for simple generation."""
    policy = get_policy()
    return await policy.generate_simple(prompt, task_type)


# Health check
async def check_ollama_health(ollama_url: str = "http://host.docker.internal:11434") -> Dict[str, Any]:
    """Check Ollama health and return status."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            return {
                "healthy": True,
                "models": [m["name"] for m in models],
                "model_count": len(models),
            }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "models": [],
            "model_count": 0,
        }


async def check_router_health(router_url: str = "http://model-router:8090") -> Dict[str, Any]:
    """Check Model Router health."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{router_url}/healthz")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"healthy": False, "error": str(e)}