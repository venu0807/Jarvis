import asyncio
import json
import httpx
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

# Allow CORS for the Next.js dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: List[WebSocket] = []
transcript_buffer = ""

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi4-mini" # Your local model

async def query_ai(question: str):
    prompt = f"You are an expert technical interviewer assistant. The interviewer just asked this question: '{question}'. Provide a concise, highly technical, and impressive answer in 3 bullet points that the candidate can easily read."
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            })
            if response.status_code == 200:
                answer = response.json().get("response", "")
                await broadcast_to_clients({"type": "ai_answer", "question": question, "answer": answer})
    except Exception as e:
        print(f"Error querying Ollama: {e}")

async def broadcast_to_clients(message: dict):
    for client in connected_clients:
        try:
            await client.send_text(json.dumps(message))
        except:
            connected_clients.remove(client)

@app.post("/api/transcript")
async def receive_transcript(request: Request):
    global transcript_buffer
    data = await request.json()
    text = data.get("text", "")
    is_final = data.get("is_final", False)
    
    # Broadcast raw text to UI immediately so you can read along
    await broadcast_to_clients({"type": "transcript", "text": text, "is_final": is_final})
    
    if is_final and len(text.strip()) > 10:
        transcript_buffer += " " + text
        
        # Simple heuristic: if it looks like a technical question
        lower_text = text.lower()
        if "?" in text or "how would you" in lower_text or "what is" in lower_text or "explain" in lower_text:
            print(f"Detecting Question: {text}")
            asyncio.create_task(query_ai(text))
            
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    # Running on port 8005 so it doesn't conflict with other services
    uvicorn.run(app, host="0.0.0.0", port=8005)
