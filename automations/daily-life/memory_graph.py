"""
memory_graph.py — Personal Knowledge Graph

1. Long-term memory storage for Jarvis using pgvector in PostgreSQL.
2. Generates vector embeddings locally using sentence-transformers (zero-leak).
3. Reads recent events from the 'events' table and permanently memorizes them.
"""

import sys
import os
import json
import psycopg2
import asyncio
import aiohttp

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from automations.pinterest.config import DB_PARAMS
except ImportError:
    DB_PARAMS = {
        "dbname": "pinterest_db",
        "user": "venu",
        "password": "venu",
        "host": "127.0.0.1"
    }

async def fetch_embedding(session, memory_text, semaphore):
    async with semaphore:
        async with session.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text:latest", "prompt": memory_text}
        ) as response:
            data = await response.json()
            return data["embedding"]

async def fetch_all_embeddings(memory_texts):
    # Limit concurrency to 5 requests at a time to not overload Ollama
    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_embedding(session, text, semaphore) for text in memory_texts]
        return await asyncio.gather(*tasks)

def update_memory_graph():
    print("🧠 [Hermes Memory] Starting Vector DB Sync...")
    
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # 1. Fetch recent events that haven't been vectorized yet
        # For simplicity in this implementation, we just fetch the last 10 events
        cur.execute("SELECT id, event_type, payload, created_at FROM events ORDER BY created_at DESC LIMIT 10")
        recent_events = cur.fetchall()
        
        if not recent_events:
            print("  ℹ️  No new events found.")
            return

        print(f"  📥 Found {len(recent_events)} recent events. Generating embeddings...")
        
        # Collect items to memorize
        items_to_memorize = []
        for event_id, event_type, payload, created_at in recent_events:
            cur.execute("SELECT id FROM memory_embeddings WHERE event_id = %s", (event_id,))
            if cur.fetchone():
                continue # Already memorized
                
            # 2. Format the event into a human-readable memory sentence
            memory_text = f"At {created_at}, a {event_type} event occurred."
            if payload:
                if isinstance(payload, dict):
                    if "company" in payload:
                        memory_text += f" Applied to {payload.get('company')} for {payload.get('position', payload.get('title'))}."
                    elif "product" in payload:
                        memory_text += f" Pinned product: {payload.get('product')}."
                    else:
                        memory_text += f" Details: {json.dumps(payload)}"
                else:
                    memory_text += f" Details: {payload}"
                    
            print(f"  💭 Memorizing: '{memory_text}'")
            items_to_memorize.append({
                "event_id": event_id,
                "memory_text": memory_text
            })
            
        if items_to_memorize:
            # 3. Generate 768D Vector Embedding (Locally, zero-leak!) using Ollama concurrently
            memory_texts = [item["memory_text"] for item in items_to_memorize]
            embeddings = asyncio.run(fetch_all_embeddings(memory_texts))
            
            # 4. Insert into pgvector
            memorized_count = 0
            for item, embedding in zip(items_to_memorize, embeddings):
                cur.execute(
                    "INSERT INTO memory_embeddings (content, embedding, event_id) VALUES (%s, %s, %s)",
                    (item["memory_text"], embedding, item["event_id"])
                )
                memorized_count += 1

            conn.commit()
            print(f"✅ [Hermes Memory] Sync Complete. Permanently stored {memorized_count} new memories in pgvector.")
        else:
            print("  ℹ️  No new events to memorize.")
            
    except Exception as e:
        print(f"❌ [Hermes Memory] Sync failed: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    update_memory_graph()
