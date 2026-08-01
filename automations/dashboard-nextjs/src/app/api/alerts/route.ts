import { NextResponse } from 'next/server';
import fs from 'fs';
import { exec } from 'child_process';

const ALERTS_FILE = '/home/venu/Proposals/Jarvis/logs/alerts.json';
const ALERT_MANAGER = '/home/venu/Proposals/Jarvis/alert_manager.py';

export async function GET() {
  try {
    if (!fs.existsSync(ALERTS_FILE)) {
      return NextResponse.json([]);
    }
    const data = fs.readFileSync(ALERTS_FILE, 'utf8');
    const alerts = JSON.parse(data);
    return NextResponse.json(alerts);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to read alerts' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const { action } = await req.json();
    if (action === 'clear') {
      await new Promise((resolve, reject) => {
        exec(`python3 ${ALERT_MANAGER} clear`, (err, stdout, stderr) => {
          if (err) reject(err);
          else resolve(stdout);
        });
      });
      return NextResponse.json({ success: true });
    }
    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to perform action' }, { status: 500 });
  }
}
