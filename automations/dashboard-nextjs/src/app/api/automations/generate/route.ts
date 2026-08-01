import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function POST(req: Request) {
  try {
    const { id, task_description } = await req.json();

    if (!id || !task_description) {
      return NextResponse.json({ error: 'Missing id or task_description' }, { status: 400 });
    }

    const promptText = `You are Hermes, the lead automation engineer. The user wants to automate: '${task_description}'. Generate a python script to automate this. ONLY output the python code inside \`\`\`python blocks. Do not include extra conversational text.`;

    const response = await fetch('http://127.0.0.1:11434/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'llama3.1', // or whatever their default Ollama model is, I'll use llama3.1
        prompt: promptText,
        stream: false
      })
    });

    if (!response.ok) {
      throw new Error(`Ollama API error: ${response.statusText}`);
    }

    const data = await response.json();
    let proposedCode = data.response;

    const codeMatch = proposedCode.match(/```python\n([\s\S]*?)```/);
    if (codeMatch) {
      proposedCode = codeMatch[1].trim();
    } else {
      const genericMatch = proposedCode.match(/```([\s\S]*?)```/);
      if (genericMatch) {
          proposedCode = genericMatch[1].trim();
      }
    }

    await query(
      "UPDATE automation_tasks SET status='draft', proposed_code=$1 WHERE id=$2",
      [proposedCode, id]
    );

    return NextResponse.json({ success: true, proposedCode });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
