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

# Removed SentenceTransformers import since we are using Ollama API now.

def update_memory_graph():
    print("🧠 [Hermes Memory] Starting Vector DB Sync...")
    
    import requests
    
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
        
        event_ids = tuple(e[0] for e in recent_events)
        if event_ids:
            cur.execute("SELECT event_id FROM memory_embeddings WHERE event_id IN %s", (event_ids,))
            memorized_event_ids = {row[0] for row in cur.fetchall()}
        else:
            memorized_event_ids = set()

        memorized_count = 0
        for event_id, event_type, payload, created_at in recent_events:
            # Check if we already memorized this event (using a simple metadata check)
            # Wait, earlier I recreated the table without the metadata column to make it simpler, but let's check if it has metadata.
            # Actually, the recreate command was: `CREATE TABLE memory_embeddings (id SERIAL PRIMARY KEY, event_id INTEGER REFERENCES events(id), content TEXT, embedding vector(768))`
            if event_id in memorized_event_ids:
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
            
            # 3. Generate 768D Vector Embedding (Locally, zero-leak!) using Ollama
            r = requests.post("http://localhost:11434/api/embeddings", json={"model": "nomic-embed-text:latest", "prompt": memory_text})
            embedding = r.json()["embedding"]
            
            # 4. Insert into pgvector
            cur.execute(
                "INSERT INTO memory_embeddings (content, embedding, event_id) VALUES (%s, %s, %s)",
                (memory_text, embedding, event_id)
            )
            memorized_count += 1
            
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ [Hermes Memory] Sync Complete. Permanently stored {memorized_count} new memories in pgvector.")
        
    except Exception as e:
        print(f"❌ [Hermes Memory] Sync failed: {e}")

if __name__ == "__main__":
    update_memory_graph()
