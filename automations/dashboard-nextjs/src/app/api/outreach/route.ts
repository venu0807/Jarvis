import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

export async function GET() {
  try {
    const dbPath = '/home/venu/Proposals/Jarvis/automations/linkedin-outreach/sent_tracker.db';
    
    if (!fs.existsSync(dbPath)) {
      return NextResponse.json({ error: 'Outreach database not found.' }, { status: 404 });
    }

    const db = new Database(dbPath, { readonly: true });

    const totalSent = (db.prepare('SELECT COUNT(*) as count FROM sent_emails').get() as any).count;
    const totalReplies = (db.prepare('SELECT COUNT(*) as count FROM replies').get() as any).count;
    const pendingFollowups = (db.prepare("SELECT COUNT(*) as count FROM followups WHERE status = 'pending'").get() as any).count;

    const byTier = db.prepare('SELECT tier, COUNT(*) as count FROM sent_emails GROUP BY tier ORDER BY count DESC').all();

    const perDay = db.prepare(
      "SELECT DATE(sent_at) as day, COUNT(*) as count FROM sent_emails WHERE sent_at >= DATE('now', '-30 days') GROUP BY day ORDER BY day ASC"
    ).all();

    const recentReplies = db.prepare(
      'SELECT recipient, subject, snippet, received_at, sentiment FROM replies ORDER BY received_at DESC LIMIT 10'
    ).all();

    const topCompanies = db.prepare(
      "SELECT company, COUNT(*) as count FROM sent_emails WHERE company != '' GROUP BY company ORDER BY count DESC LIMIT 10"
    ).all();

    db.close();

    return NextResponse.json({
      stats: { totalSent, totalReplies, pendingFollowups },
      byTier,
      perDay,
      recentReplies,
      topCompanies,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
