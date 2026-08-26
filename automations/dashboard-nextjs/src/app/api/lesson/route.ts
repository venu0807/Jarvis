import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const primaryPath = '/home/venu/Proposals/Jarvis/automations/micro-learning/daily_lesson.md';
    const fallbackPath = path.resolve(process.cwd(), '../micro-learning/daily_lesson.md');
    
    const target = fs.existsSync(primaryPath) ? primaryPath : fallbackPath;

    if (fs.existsSync(target)) {
      const content = fs.readFileSync(target, 'utf-8');
      return NextResponse.json({ content });
    } else {
      return NextResponse.json({ content: "No lesson generated today. Check back tomorrow!" });
    }
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
