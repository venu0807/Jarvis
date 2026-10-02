import asyncio
import time
import httpx
import requests

async def check_ollama_health_sync(ollama_url: str = "https://httpbin.org") -> dict:
    try:
        start_time = time.time()
        # Blocking I/O in async function
        resp = requests.get(f"{ollama_url}/get", timeout=3.0)
        latency_ms = (time.time() - start_time) * 1000
        return {"healthy": True, "latency_ms": latency_ms}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

async def check_ollama_health_async(ollama_url: str = "https://httpbin.org") -> dict:
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{ollama_url}/get")
            response.raise_for_status()
            latency_ms = (time.time() - start_time) * 1000
            return {"healthy": True, "latency_ms": latency_ms}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

async def main():
    print("Benchmarking synchronous vs asynchronous health checks...")

    # Warm up
    await check_ollama_health_sync()
    await check_ollama_health_async()

    # Measure sync
    start_sync = time.time()
    res_sync = await asyncio.gather(*(check_ollama_health_sync() for _ in range(10)))
    time_sync = time.time() - start_sync
    print(f"Sync version (10 concurrent calls) took: {time_sync:.4f} seconds")

    # Measure async
    start_async = time.time()
    res_async = await asyncio.gather(*(check_ollama_health_async() for _ in range(10)))
    time_async = time.time() - start_async
    print(f"Async version (10 concurrent calls) took: {time_async:.4f} seconds")

    improvement = (time_sync - time_async) / time_sync * 100
    print(f"Performance improvement: {improvement:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
