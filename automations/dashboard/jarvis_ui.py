import streamlit as st
import sys
import os
import psycopg2
import json
from datetime import datetime

# Setup paths to import Jarvis core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# We need sentence-transformers to convert chat queries into vectors
try:
    from sentence_transformers import SentenceTransformer
    # We will load this lazily so UI doesn't lag on startup
    @st.cache_resource
    def load_model():
        return SentenceTransformer('all-MiniLM-L6-v2')
except ImportError:
    pass # Will handle gracefully below

# Import the LLM router
try:
    from policy import call_llm
except ImportError:
    st.error("Could not import Jarvis AI Policy router.")
    call_llm = None

# DB Params (falling back to pinterest_db)
DB_PARAMS = {
    "dbname": "pinterest_db",
    "user": "venu",
    "password": "venu",
    "host": "127.0.0.1"
}

# --- UI Setup ---
st.set_page_config(page_title="Jarvis OS", page_icon="🤖", layout="wide")
st.title("🤖 Jarvis Command Center")

# --- Initialize Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello Venu. I am Hermes. I have access to your bots and your long-term memory. How can I help you today?"}
    ]

# --- Sidebar Stats (Live from DB) ---
st.sidebar.title("System Status")
st.sidebar.success("✅ Master Daemon Running")
st.sidebar.success("✅ Event Bus Online")

try:
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    cur.execute("SELECT count(*) FROM events WHERE event_type = 'pinterest.pin_posted'")
    pin_count = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM events WHERE event_type = 'jobs.applied'")
    job_count = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM memory_embeddings")
    memory_count = cur.fetchone()[0]
    
    cur.execute("SELECT payload, created_at FROM events WHERE event_type = 'pinterest.pin_posted' ORDER BY created_at DESC LIMIT 20")
    recent_pins = [f"{row[0].get('product', 'Unknown')} (Posted: {row[1].strftime('%Y-%m-%d')})" if row[1] else row[0].get('product', 'Unknown') for row in cur.fetchall()]
    
    cur.execute("SELECT payload, created_at FROM events WHERE event_type = 'jobs.applied' ORDER BY created_at DESC LIMIT 20")
    recent_jobs = [f"{row[0].get('company', 'Unknown')} (Applied: {row[1].strftime('%Y-%m-%d')})" if row[1] else row[0].get('company', 'Unknown') for row in cur.fetchall()]
    
    cur.execute("SELECT payload FROM events WHERE event_type = 'daily.morning_briefing' ORDER BY created_at DESC LIMIT 1")
    briefing_row = cur.fetchone()
    latest_briefing = briefing_row[0].get("summary", "No briefing available today.") if briefing_row and briefing_row[0] else "No briefing available yet."
    
    # Store these in session state or globally so the chat input can access them
    st.session_state.recent_pins = recent_pins
    st.session_state.recent_jobs = recent_jobs
    st.session_state.pin_count = pin_count
    st.session_state.job_count = job_count
    
    conn.close()
    
    st.sidebar.markdown("---")
    st.sidebar.metric(label="📌 Pinterest Posts", value=pin_count)
    st.sidebar.metric(label="💼 Jobs Applied", value=job_count)
    st.sidebar.metric(label="🧠 Memories Stored", value=memory_count)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🌅 Morning Briefing")
    st.sidebar.info(latest_briefing)
    
except Exception as e:
    st.sidebar.warning(f"Database stats unavailable: {e}")

# --- Layout ---
tab1, tab2 = st.tabs(["💬 Chat", "🧠 Daily Upskill"])

with tab1:
    # --- Render Chat History ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

with tab2:
    st.header("Daily Micro-Learning 🚀")
    lesson_path = os.path.join(os.path.dirname(__file__), "..", "micro-learning", "daily_lesson.md")
    if os.path.exists(lesson_path):
        with open(lesson_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("No lesson generated today. Check back tomorrow!")

# --- Chat Input ---
if prompt := st.chat_input("Ask Jarvis... (e.g. 'What jobs did I apply to today?')"):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Jarvis Thinking
    with st.chat_message("assistant"):
        with st.spinner("Accessing Memory Database..."):
            context = ""
            try:
                import requests
                # 1. Generate Vector for the user's question using Ollama
                r = requests.post("http://localhost:11434/api/embeddings", json={"model": "nomic-embed-text:latest", "prompt": prompt})
                query_vector = r.json()["embedding"]
                
                # 2. Search pgvector for the closest matches (Cosine Similarity)
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                
                # Note: <=> is cosine distance in pgvector
                cur.execute("""
                    SELECT content, 1 - (embedding <=> %s::vector) AS similarity 
                    FROM memory_embeddings 
                    ORDER BY embedding <=> %s::vector 
                    LIMIT 5
                """, (query_vector, query_vector))
                
                results = cur.fetchall()
                conn.close()
                
                if results and results[0][1] > 0.5: # Only include if reasonably relevant
                    context = "Here are my relevant memories regarding this:\n"
                    for row in results:
                        context += f"- {row[0]}\n"
            except Exception as e:
                print(f"Memory Retrieval Error: {e}")
                pass # Fail gracefully if pgvector is down
            
        with st.spinner("Hermes is thinking..."):
            # Construct the RAG prompt
            today_str = datetime.now().strftime("%Y-%m-%d")
            recent_pins_str = ', '.join(st.session_state.recent_pins) if st.session_state.recent_pins else 'None'
            recent_jobs_str = ', '.join(st.session_state.recent_jobs) if st.session_state.recent_jobs else 'None'
            system_stats = f"CURRENT DATE: {today_str}\nSYSTEM CONTEXT:\n- Total Pinterest pins posted: {st.session_state.pin_count}\n- Recent Pins: {recent_pins_str}\n- Total jobs applied to: {st.session_state.job_count}\n- Recent Jobs: {recent_jobs_str}\n"
            
            sys_prompt = "You are Jarvis (Hermes), an advanced AI assistant. You have full real-time access to the system context. The context provided IS the real-time data, so never say you don't have real-time data and never mention training cutoffs."
            if context:
                final_prompt = f"{sys_prompt}\n\n{system_stats}\n{context}\n\nUSER QUESTION: {prompt}\n\nINSTRUCTIONS: Answer directly based on the context. If they ask for counts, use the exact numbers. Be concise and conversational.\n\nHERMES:"
            else:
                final_prompt = f"{sys_prompt}\n\n{system_stats}\nUSER QUESTION: {prompt}\n\nINSTRUCTIONS: Answer directly based on the context. If they ask for counts, use the exact numbers. Be concise and conversational.\n\nHERMES:"
                
            if call_llm:
                try:
                    llm_result = call_llm(prompt=final_prompt, mode="run", force="local")
                    response_text = llm_result.text
                    # Truncate if the model starts generating fake user questions
                    if "USER QUESTION:" in response_text:
                        response_text = response_text.split("USER QUESTION:")[0].strip()
                except Exception as e:
                    response_text = "⚠️ My language model (Ollama/OpenClaw) is currently offline. Please start it on port 11434."
            else:
                response_text = "System error: policy.py could not be loaded."
            
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
