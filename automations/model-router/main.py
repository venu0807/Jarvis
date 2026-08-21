#!/usr/bin/env python3
"""
Model Router — FastAPI service for intelligent model selection.

Routes tasks to the best model based on task type, model availability,
and performance characteristics.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Literal

import httpx
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import fastapi-health for health checks
try:
    from fastapi_health import health
    HAS_FASTAPI_HEALTH = True
except ImportError:
    HAS_FASTAPI_HEALTH = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
API_KEY = os.getenv("MODEL_ROUTER_API_KEY", "dev-key-change-in-production")
ROUTER_PORT = int(os.getenv("ROUTER_PORT", "8090"))

TaskType = Literal["coding", "reasoning", "embedding", "general", "lightweight", "job_match"]

# Model capabilities and preferences
MODEL_CAPABILITIES = {
    "llama3.2:3b-instruct-q4_K_M": {
        "task_types": ["reasoning", "general", "job_match"],
        "strengths": ["reasoning", "analysis", "general_chat"],
        "vram_gb": 2.5,
        "speed": "medium",
        "quality": "high",
    },
    "phi4:mini": {
        "task_types": ["general", "job_match", "lightweight", "reasoning"],
        "strengths": ["speed", "efficiency", "general_chat"],
        "vram_gb": 1.8,
        "speed": "fast",
        "quality": "medium",
    },
    "qwen2.5-coder:3b-instruct-q4_K_M": {
        "task_types": ["coding", "general"],
        "strengths": ["code_generation", "code_review", "debugging"],
        "vram_gb": 2.3,
        "speed": "medium",
        "quality": "high",
    },
    "gemma2:2b-instruct-q4_K_M": {
        "task_types": ["lightweight", "general"],
        "strengths": ["speed", "low_resource", "simple_tasks"],
        "vram_gb": 1.5,
        "speed": "very_fast",
        "quality": "medium",
    },
    "nomic-embed-text:latest": {
        "task_types": ["embedding"],
        "strengths": ["embeddings", "semantic_search", "rag"],
        "vram_gb": 0.5,
        "speed": "very_fast",
        "quality": "high",
    },
}

# Preferred model per task type (ordered by preference)
TASK_MODEL_PREFERENCE = {
    "coding": ["qwen2.5-coder:3b-instruct-q4_K_M", "llama3.2:3b-instruct-q4_K_M"],
    "reasoning": ["llama3.2:3b-instruct-q4_K_M", "phi4:mini"],
    "embedding": ["nomic-embed-text:latest"],
    "general": ["phi4:mini", "llama3.2:3b-instruct-q4_K_M"],
    "lightweight": ["gemma2:2b-instruct-q4_K_M", "phi4:mini"],
    "job_match": ["phi4:mini", "llama3.2:3b-instruct-q4_K_M"],
}

# Global state
available_models: Dict[str, Dict] = {}
model_load_times: Dict[str, float] = {}


# Pydantic models
class RouteRequest(BaseModel):
    task_type: TaskType
    prompt: str = Field(..., max_length=10000, description="Prompt preview for routing decision")
    prefer_speed: bool = False
    prefer_quality: bool = False


class RouteResponse(BaseModel):
    model: str
    reason: str
    fallback: Optional[str] = None
    estimated_vram_gb: float
    estimated_latency_ms: int


class HealthResponse(BaseModel):
    healthy: bool
    models_loaded: List[str]
    model_count: int
    ollama_healthy: bool
    uptime_seconds: float


class ModelsResponse(BaseModel):
    models: Dict[str, Dict]


# Ollama health check
async def check_ollama() -> Dict:
    """Check Ollama health and return available models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            return {
                "healthy": True,
                "models": [m["name"] for m in models],
                "model_details": {m["name"]: m for m in models},
            }
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        return {"healthy": False, "models": [], "model_details": {}, "error": str(e)}


async def refresh_available_models():
    """Refresh the list of available models from Ollama."""
    global available_models
    result = await check_ollama()
    if result["healthy"]:
        available_models = {
            name: {**MODEL_CAPABILITIES.get(name, {}), **details}
            for name, details in result["model_details"].items()
            if name in MODEL_CAPABILITIES
        }
        logger.info(f"Refreshed models: {list(available_models.keys())}")
    else:
        available_models = {}


def select_model(task_type: TaskType, prefer_speed: bool = False, prefer_quality: bool = False) -> RouteResponse:
    """Select the best model for a task type."""
    preferred = TASK_MODEL_PREFERENCE.get(task_type, ["phi4:mini"])
    
    # Filter to available models
    available_preferred = [m for m in preferred if m in available_models]
    
    if not available_preferred:
        # Fallback to any available model that supports the task type
        candidates = [
            name for name, caps in available_models.items()
            if task_type in caps.get("task_types", [])
        ]
        if not candidates:
            candidates = list(available_models.keys())
        if not candidates:
            raise HTTPException(status_code=503, detail="No models available")
        available_preferred = candidates
    
    # Select based on preference
    if prefer_speed:
        # Sort by speed (very_fast > fast > medium)
        speed_order = {"very_fast": 0, "fast": 1, "medium": 2, "slow": 3}
        available_preferred.sort(key=lambda m: speed_order.get(available_models[m].get("speed", "medium"), 2))
    elif prefer_quality:
        # Sort by quality (high > medium)
        available_preferred.sort(key=lambda m: 0 if available_models[m].get("quality") == "high" else 1)
    
    selected = available_preferred[0]
    caps = available_models.get(selected, {})
    
    # Determine fallback
    fallback = None
    for m in available_preferred[1:]:
        if m != selected:
            fallback = m
            break
    
    return RouteResponse(
        model=selected,
        reason=f"Selected for {task_type} task (prefer_speed={prefer_speed}, prefer_quality={prefer_quality})",
        fallback=fallback,
        estimated_vram_gb=caps.get("vram_gb", 2.0),
        estimated_latency_ms=estimate_latency(selected, task_type),
    )


def estimate_latency(model: str, task_type: TaskType) -> int:
    """Estimate latency in ms based on model and task."""
    base_latency = {
        "very_fast": 500,
        "fast": 1500,
        "medium": 3000,
        "slow": 8000,
    }
    speed = available_models.get(model, {}).get("speed", "medium")
    return base_latency.get(speed, 3000)


# FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Model Router...")
    await refresh_available_models()
    # Periodic refresh
    async def periodic_refresh():
        while True:
            await asyncio.sleep(60)  # Refresh every minute
            await refresh_available_models()
    
    refresh_task = asyncio.create_task(periodic_refresh())
    yield
    # Shutdown
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass
    logger.info("Model Router stopped")


app = FastAPI(
    title="JARVIS Model Router",
    description="Intelligent model routing for Ollama",
    version="1.0.0",
    lifespan=lifespan,
)


# Auth dependency
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# Health endpoints
if HAS_FASTAPI_HEALTH:
    app.add_api_route("/healthz", health([lambda: {"status": "ok"}]), response_model=HealthResponse)
else:
    @app.get("/healthz", response_model=HealthResponse)
    async def health_check():
        ollama_result = await check_ollama()
        return HealthResponse(
            healthy=ollama_result["healthy"],
            models_loaded=list(available_models.keys()),
            model_count=len(available_models),
            ollama_healthy=ollama_result["healthy"],
            uptime_seconds=time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0,
        )


@app.get("/models", response_model=ModelsResponse)
async def list_models(api_key: str = Depends(verify_api_key)):
    """List all available models with capabilities."""
    return ModelsResponse(models=available_models)


@app.post("/route", response_model=RouteResponse)
async def route_task(
    request: RouteRequest,
    api_key: str = Depends(verify_api_key),
):
    """Route a task to the best model."""
    if not available_models:
        await refresh_available_models()
    
    if not available_models:
        raise HTTPException(status_code=503, detail="No models available")
    
    return select_model(
        request.task_type,
        prefer_speed=request.prefer_speed,
        prefer_quality=request.prefer_quality,
    )


@app.post("/generate")
async def generate_proxy(
    request: RouteRequest,
    api_key: str = Depends(verify_api_key),
):
    """Proxy generate request to Ollama with selected model."""
    route_result = select_model(
        request.task_type,
        prefer_speed=request.prefer_speed,
        prefer_quality=request.prefer_quality,
    )
    
    # Call Ollama
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": route_result.model,
                    "prompt": request.prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()
            return {
                "model": route_result.model,
                "response": result.get("response", ""),
                "route_info": route_result.model_dump(),
            }
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            raise HTTPException(status_code=502, detail=f"Ollama error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=ROUTER_PORT)