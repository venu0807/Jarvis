import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const lessonPath = path.resolve(process.cwd(), '../micro-learning/daily_lesson.md');
    
    if (fs.existsSync(lessonPath)) {
      const content = fs.readFileSync(lessonPath, 'utf-8');
      return NextResponse.json({ content });
    } else {
      return NextResponse.json({ content: "No lesson generated today. Check back tomorrow!" });
    }
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
