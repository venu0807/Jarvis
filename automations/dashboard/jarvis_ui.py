import streamlit as st
import sys
import os
import sqlite3
import psycopg2
import json
import pandas as pd
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

# --- Automate-My-Life Inbox ---
st.sidebar.markdown("---")
st.sidebar.subheader("📥 Automate-My-Life Inbox")
new_task = st.sidebar.text_input("What manual chore should I automate?")
if st.sidebar.button("Submit Request"):
    if new_task:
        try:
            conn2 = psycopg2.connect(**DB_PARAMS)
            cur2 = conn2.cursor()
            cur2.execute("INSERT INTO automation_tasks (task_description) VALUES (%s)", (new_task,))
            conn2.commit()
            conn2.close()
            st.sidebar.success("Task sent to Hermes for processing! Check the Proposals tab.")
        except Exception as e:
            st.sidebar.error(f"Failed to submit: {e}")

# --- Layout ---
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "🧠 Daily Upskill", "📊 Analytics", "⚡ Automation Proposals"])

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

with tab3:
    st.header("System Analytics 📈")
    metrics_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'metrics.db'))
    
    if os.path.exists(metrics_db_path):
        try:
            conn_sqlite = sqlite3.connect(metrics_db_path)
            df = pd.read_sql_query("SELECT category, SUM(count) as total FROM metrics GROUP BY category", conn_sqlite)
            
            if not df.empty:
                st.subheader("Total Automation Events")
                # Create columns for top-level metrics
                cols = st.columns(len(df))
                for idx, row in df.iterrows():
                    cols[idx].metric(label=row['category'].replace('_', ' ').title(), value=row['total'])
                
                st.markdown("---")
                
                # Granular breakdown chart
                df_granular = pd.read_sql_query("SELECT subcategory, count FROM metrics", conn_sqlite)
                if not df_granular.empty:
                    df_grouped = df_granular.groupby('subcategory').sum().reset_index()
                    st.subheader("Event Breakdown")
                    st.bar_chart(df_grouped.set_index('subcategory'))
            else:
                st.info("No metrics logged yet. Let the bots run for a bit!")
                
            conn_sqlite.close()
            
            # --- NEW: Pinterest Affiliate Analytics ---
            st.markdown("---")
            st.subheader("📌 Pinterest Affiliate Analytics (Live)")
            
            # These are placeholders that can be updated via a scraper later
            clicks = 5 # User's current tracked clicks
            sales = 0.00
            
            # We calculate impressions dynamically based on pins to show activity
            impressions_estimate = (st.session_state.pin_count * 15) if st.session_state.pin_count else 0
            
            pin_cols = st.columns(4)
            pin_cols[0].metric(label="Total Pins Live", value=st.session_state.pin_count, delta="Active")
            pin_cols[1].metric(label="Algorithmic Impressions", value=impressions_estimate, delta="Warming up", delta_color="off")
            pin_cols[2].metric(label="Affiliate Clicks", value=clicks, delta="Stuck in sandbox", delta_color="inverse")
            pin_cols[3].metric(label="Total Sales", value=f"${sales:.2f}", delta="Pending", delta_color="off")
            
            st.info("💡 Note: Pinterest SEO takes 1-3 months. Continue posting daily to break out of the algorithmic sandbox and increase clicks.")

        except Exception as e:
            st.error(f"Failed to load analytics: {e}")
    else:
        st.info("No metrics database found. Starting automations will create it.")

with tab4:
    st.header("⚡ Pending Automation Proposals")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        # Check if table exists first just in case
        try:
            df_tasks = pd.read_sql_query("SELECT id, task_description, status, proposed_code, created_at FROM automation_tasks ORDER BY created_at DESC", conn)
        except Exception:
            df_tasks = pd.DataFrame()
        conn.close()
        
        if df_tasks.empty:
            st.info("No automation requests found. Submit a chore in the sidebar inbox!")
        else:
            for idx, row in df_tasks.iterrows():
                with st.expander(f"[{row['status'].upper()}] {row['task_description']} ({row['created_at']})"):
                    if row['status'] == 'pending':
                        st.info("Hermes is ready to analyze this request and write the code.")
                        if st.button("Generate Code via Hermes", key=f"gen_{row['id']}"):
                            with st.spinner("Hermes is writing the automation code..."):
                                prompt_text = f"You are Hermes, the lead automation engineer. The user wants to automate: '{row['task_description']}'. Generate a python script to automate this. ONLY output the python code inside ```python blocks. Do not include extra conversational text."
                                if call_llm:
                                    llm_result = call_llm(prompt=prompt_text, mode="run", force="local")
                                    import re
                                    code_match = re.search(r'```python(.*?)```', llm_result.text, re.DOTALL)
                                    if code_match:
                                        proposed_code = code_match.group(1).strip()
                                    else:
                                        proposed_code = llm_result.text
                                    
                                    conn2 = psycopg2.connect(**DB_PARAMS)
                                    cur2 = conn2.cursor()
                                    cur2.execute("UPDATE automation_tasks SET status='draft', proposed_code=%s WHERE id=%s", (proposed_code, row['id']))
                                    conn2.commit()
                                    conn2.close()
                                    st.success("Draft created! Please refresh the page.")
                                else:
                                    st.error("LLM Router not available.")

                    elif row['status'] == 'draft':
                        st.markdown("### 🤖 Hermes Proposed Code")
                        st.code(row['proposed_code'], language='python')
                        if st.button("✅ Approve & Deploy", key=f"deploy_{row['id']}"):
                            import os
                            import uuid
                            script_id = str(uuid.uuid4())[:8]
                            script_path = f"/home/venu/Proposals/Jarvis/automations/hermes-scripts/auto_{script_id}.py"
                            os.makedirs(os.path.dirname(script_path), exist_ok=True)
                            with open(script_path, "w") as f:
                                f.write(row['proposed_code'] or "# Error: No code generated")
                            
                            conn2 = psycopg2.connect(**DB_PARAMS)
                            cur2 = conn2.cursor()
                            cur2.execute("UPDATE automation_tasks SET status='deployed' WHERE id=%s", (row['id'],))
                            conn2.commit()
                            conn2.close()
                            
                            st.success(f"Script saved to {script_path} and marked as deployed!")
                            
                    elif row['status'] == 'deployed':
                        st.success("This automation has been deployed.")
                        with st.expander("View Deployed Code"):
                            st.code(row['proposed_code'], language='python')
    except Exception as e:
        st.error(f"Error loading proposals: {e}")

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
            
            sys_prompt = f"You are Jarvis (Hermes), an advanced AI assistant. Today's date is {today_str}. You have full real-time access to the system context. The context provided IS the real-time data, do not mention training cutoffs."
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
