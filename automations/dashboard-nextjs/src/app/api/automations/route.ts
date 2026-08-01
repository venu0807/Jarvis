import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
import { query } from '@/lib/db';

export async function GET() {
  try {
    const result = await query("SELECT id, task_description, status, proposed_code, created_at FROM automation_tasks ORDER BY created_at DESC");
    return NextResponse.json({ tasks: result.rows });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { task_description } = body;
    
    if (!task_description) {
      return NextResponse.json({ error: 'Missing task_description' }, { status: 400 });
    }

    const result = await query(
      "INSERT INTO automation_tasks (task_description) VALUES ($1) RETURNING *",
      [task_description]
    );

    return NextResponse.json({ task: result.rows[0] });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
