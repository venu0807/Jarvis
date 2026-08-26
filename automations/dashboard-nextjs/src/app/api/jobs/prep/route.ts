import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  try {
    const { company, title, description } = await req.json();

    if (!company) {
      return NextResponse.json({ error: 'Company name is required' }, { status: 400 });
    }

    // 1. Check if a pre-generated prep sheet already exists
    const prepDir = path.resolve(process.cwd(), '../interview_scheduler_prep_bot/prep_sheets');
    const safeName = company.toLowerCase().replace(/[^a-z0-9]/g, '_');
    
    if (fs.existsSync(prepDir)) {
      const files = fs.readdirSync(prepDir);
      const matched = files.find(f => f.toLowerCase().includes(safeName) || safeName.includes(f.toLowerCase().replace('_prep_sheet.md', '')));
      if (matched) {
        const content = fs.readFileSync(path.join(prepDir, matched), 'utf-8');
        return NextResponse.json({ prep: content });
      }
    }

    // 2. Generate on-the-fly via Local Ollama (qwen2.5-coder:3b)
    const prompt = `Act as an expert technical interviewer. I have an upcoming interview at ${company} for the role of "${title || 'Developer'}".

Here is the job description:
${description || 'General Software / Web Developer Role'}

Generate a concise, highly strategic 1-page "Cheat Sheet" for me:
1. **Core Mission**: 1-sentence summary of what this role does.
2. **Top 3 Technical Focus Areas**: Key technical requirements.
3. **Behavioral Strengths**: Key soft skills to emphasize.
4. **Insider Questions to Ask**: 3 brilliant questions to ask the interviewer.

Format using clean Markdown with bold headers and bullet points.`;

    const response = await fetch("http://127.0.0.1:11434/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "qwen2.5-coder:3b",
        prompt: prompt,
        stream: false
      })
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Local LLM returned status ${response.status}` }, { status: 500 });
    }

    const result = await response.json();
    const responseText = result.response || "No content generated.";

    return NextResponse.json({ prep: responseText });
  } catch (error: any) {
    console.error('Prep generator error:', error);
    return NextResponse.json({ error: error.message || 'Failed to generate prep' }, { status: 500 });
  }
}
