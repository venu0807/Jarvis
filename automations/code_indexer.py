import os
import sys
import argparse
import requests
import psycopg2
from pathlib import Path
from datetime import datetime

# DB Params (matching jarvis_ui.py)
DB_PARAMS = {
    "dbname": "pinterest_db",
    "user": "venu",
    "password": "venu",
    "host": "127.0.0.1"
}

def get_embedding(text):
    """Get vector embedding from local Ollama model."""
    try:
        r = requests.post(
            "http://localhost:11434/api/embeddings", 
            json={"model": "nomic-embed-text:latest", "prompt": text},
            timeout=10
        )
        return r.json().get("embedding")
    except Exception as e:
        print(f"❌ Failed to get embedding: {e}")
        return None

def chunk_text(text, chunk_size=1000, overlap=200):
    """Splits text into overlapping chunks."""
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+chunk_size])
        i += chunk_size - overlap
    return chunks

def index_project(project_path: str):
    path = Path(project_path).resolve()
    if not path.exists() or not path.is_dir():
        print(f"❌ Error: {path} is not a valid directory.")
        return

    project_name = path.name
    print(f"📂 Indexing project: {project_name} into pgvector...")

    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Could not connect to PostgreSQL: {e}")
        return

    files_indexed = 0
    chunks_indexed = 0

    for root, dirs, files in os.walk(path):
        # Ignore clutter
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', 'venv', 'env', '.vscode', 'output', 'drafts', 'logs', 'prep_sheets')]
        
        for f in files:
            if f.endswith(('.py', '.js', '.md', '.json', '.yaml', '.yml', '.txt')):
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, path)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        
                    chunks = chunk_text(content)
                    
                    for chunk in chunks:
                        # Contextualize the chunk for the LLM
                        context_text = f"Project: {project_name}\nFile: {rel_path}\nContent:\n{chunk}"
                        
                        embedding = get_embedding(context_text)
                        if embedding:
                            cur.execute("""
                                INSERT INTO memory_embeddings (content, embedding)
                                VALUES (%s, %s::vector)
                            """, (context_text, embedding))
                            chunks_indexed += 1
                            
                    files_indexed += 1
                    print(f"  ✅ Indexed {rel_path} ({len(chunks)} chunks)")
                    
                except UnicodeDecodeError:
                    pass # Skip binary or weirdly encoded files
                except Exception as e:
                    print(f"  ❌ Failed to index {rel_path}: {e}")

    conn.commit()
    conn.close()
    
    print(f"🎉 Success! Indexed {project_name}. Embedded {files_indexed} files across {chunks_indexed} vector chunks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code Indexer: Embed your codebase into the Vector Database.")
    parser.add_argument("project_path", help="Path to the project directory to index.")
    args = parser.parse_args()
    
    index_project(args.project_path)
