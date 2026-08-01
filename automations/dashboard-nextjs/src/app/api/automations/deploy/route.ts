import { NextResponse } from 'next/server';
import { query } from '@/lib/db';
import fs from 'fs/promises';
import path from 'path';

export async function POST(req: Request) {
  try {
    const { id, proposed_code } = await req.json();

    if (!id || !proposed_code) {
      return NextResponse.json({ error: 'Missing id or proposed_code' }, { status: 400 });
    }

    // Write file to hermes-scripts
    const scriptId = Math.random().toString(36).substring(2, 10);
    const scriptPath = path.resolve(process.cwd(), `../hermes-scripts/auto_${scriptId}.py`);
    
    // Ensure directory exists
    await fs.mkdir(path.dirname(scriptPath), { recursive: true });
    
    await fs.writeFile(scriptPath, proposed_code);

    // Update DB status
    await query(
      "UPDATE automation_tasks SET status='deployed' WHERE id=$1",
      [id]
    );

    return NextResponse.json({ success: true, scriptPath });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
