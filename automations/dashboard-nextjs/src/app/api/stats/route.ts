import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
import { query } from '@/lib/db';
import Database from 'better-sqlite3';
import path from 'path';

export async function GET() {
  try {
    const pinsResult = await query("SELECT count(*) FROM events WHERE event_type = 'pinterest.pin_posted'");
    const memoryResult = await query("SELECT count(*) FROM memory_embeddings");
    
    // Read directly from SQLite for 100% accuracy
    const dbPath = path.resolve(process.cwd(), '../job-automation/output/jobs.db');
    let totalJobCount = 0;
    let manualJobCount = 0;
    let autoJobCount = 0;
    let recentJobsFromDB: any[] = [];
    try {
      const db = new Database(dbPath, { readonly: true });
      totalJobCount = (db.prepare("SELECT count(*) as count FROM jobs").get() as any).count;
      manualJobCount = (db.prepare("SELECT count(*) as count FROM jobs WHERE status = 'manual'").get() as any).count;
      autoJobCount = (db.prepare("SELECT count(*) as count FROM jobs WHERE status = 'applied'").get() as any).count;
      recentJobsFromDB = db.prepare("SELECT title, company, status, timestamp FROM jobs ORDER BY timestamp DESC LIMIT 5").all();
      db.close();
    } catch (e) {
      console.error("SQLite error:", e);
    }
    
    // Getting recent items
    const recentPins = await query("SELECT payload, created_at FROM events WHERE event_type = 'pinterest.pin_posted' ORDER BY created_at DESC LIMIT 5");
    const briefingResult = await query("SELECT payload FROM events WHERE event_type = 'daily.morning_briefing' ORDER BY created_at DESC LIMIT 1");
    
    let latestBriefing = "No briefing available yet.";
    if (briefingResult.rows.length > 0) {
      latestBriefing = briefingResult.rows[0].payload?.summary || "No briefing available today.";
    }

    return NextResponse.json({
      metrics: {
        pinterest: parseInt(pinsResult.rows[0].count),
        jobsTotal: totalJobCount,
        jobsManual: manualJobCount,
        jobsAuto: autoJobCount,
        memories: parseInt(memoryResult.rows[0].count),
      },
      briefing: latestBriefing,
      recent: {
        pins: recentPins.rows.map(r => ({ ...r.payload, created_at: r.created_at })),
        jobs: recentJobsFromDB.map(r => ({ 
          title: r.title,
          company: r.company,
          status: r.status,
          created_at: r.timestamp 
        }))
      }
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
