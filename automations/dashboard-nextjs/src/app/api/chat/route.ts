import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function POST(req: Request) {
  try {
    const { prompt } = await req.json();

    if (!prompt) {
      return NextResponse.json({ error: 'Prompt is required' }, { status: 400 });
    }

    let context = "";
    try {
      // 1. Generate Vector for the user's question using Ollama
      const embedRes = await fetch("http://127.0.0.1:11434/api/embeddings", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: "nomic-embed-text:latest", prompt })
      });
      
      const embedData = await embedRes.json();
      const queryVector = embedData.embedding;
      const queryVectorStr = `[${queryVector.join(',')}]`;

      // 2. Search pgvector for the closest matches (Cosine Similarity)
      // Note: <=> is cosine distance in pgvector
      const searchRes = await query(`
        SELECT content, 1 - (embedding <=> $1::vector) AS similarity 
        FROM memory_embeddings 
        ORDER BY embedding <=> $1::vector 
        LIMIT 5
      `, [queryVectorStr]);

      const results = searchRes.rows;
      if (results && results.length > 0 && results[0].similarity > 0.5) {
        context = "Here are my relevant memories regarding this:\n";
        for (const row of results) {
          context += `- ${row.content}\n`;
        }
      }
    } catch (e: any) {
      console.error("Memory Retrieval Error:", e.message);
    }

    // 3. Fetch System Stats
    const pinsResult = await query("SELECT count(*) FROM events WHERE event_type = 'pinterest.pin_posted'");
    const jobsResult = await query("SELECT count(*) FROM events WHERE event_type = 'jobs.applied'");
    const recentPins = await query("SELECT payload, created_at FROM events WHERE event_type = 'pinterest.pin_posted' ORDER BY created_at DESC LIMIT 5");
    const recentJobs = await query("SELECT payload, created_at FROM events WHERE event_type = 'jobs.applied' ORDER BY created_at DESC LIMIT 5");

    const todayStr = new Date().toISOString().split('T')[0];
    const recentPinsStr = recentPins.rows.length > 0 ? recentPins.rows.map(r => r.payload.product || 'Unknown').join(', ') : 'None';
    const recentJobsStr = recentJobs.rows.length > 0 ? recentJobs.rows.map(r => r.payload.company || 'Unknown').join(', ') : 'None';
    
    const systemStats = `CURRENT DATE: ${todayStr}\nSYSTEM CONTEXT:\n- Total Pinterest pins posted: ${pinsResult.rows[0].count}\n- Recent Pins: ${recentPinsStr}\n- Total jobs applied to: ${jobsResult.rows[0].count}\n- Recent Jobs: ${recentJobsStr}\n`;

    const sysPrompt = "You are Jarvis (Hermes), an advanced AI assistant. You have full real-time access to the system context. The context provided IS the real-time data, so never say you don't have real-time data and never mention training cutoffs.";
    
    let finalPrompt = "";
    if (context) {
      finalPrompt = `${sysPrompt}\n\n${systemStats}\n${context}\n\nUSER QUESTION: ${prompt}\n\nINSTRUCTIONS: Answer directly based on the context. If they ask for counts, use the exact numbers. Be concise and conversational.\n\nHERMES:`;
    } else {
      finalPrompt = `${sysPrompt}\n\n${systemStats}\nUSER QUESTION: ${prompt}\n\nINSTRUCTIONS: Answer directly based on the context. If they ask for counts, use the exact numbers. Be concise and conversational.\n\nHERMES:`;
    }

    // 4. Generate Response using local Ollama (phi4-mini)
    const generateRes = await fetch("http://127.0.0.1:11434/api/generate", {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: "qwen2.5-coder:3b",
        prompt: finalPrompt,
        stream: false
      })
    });

    const generateData = await generateRes.json();
    let responseText = generateData.response || "No response generated.";
    
    // Truncate if the model hallucinates user prompts
    if (responseText.includes("USER QUESTION:")) {
      responseText = responseText.split("USER QUESTION:")[0].trim();
    }

    return NextResponse.json({ response: responseText });
    
  } catch (error: any) {
    console.error("Chat Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
