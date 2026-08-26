import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
import Database from 'better-sqlite3';
import fs from 'fs';

export async function GET() {
  try {
    const dbPath = '/home/venu/Proposals/Jarvis/automations/job-automation/output/jobs.db';
    
    if (!fs.existsSync(dbPath)) {
      return NextResponse.json({ error: 'Jobs database not found.' }, { status: 404 });
    }

    const db = new Database(dbPath, { readonly: true });

    const totalJobs = (db.prepare('SELECT COUNT(*) as count FROM jobs').get() as any).count;
    const seenJobs = (db.prepare('SELECT COUNT(*) as count FROM seen_jobs').get() as any).count;
    const unhandledQuestions = (db.prepare('SELECT COUNT(*) as count FROM unhandled_questions').get() as any).count;
    
    let followupsCount = 0;
    try {
      followupsCount = (db.prepare('SELECT COUNT(*) as count FROM followups').get() as any).count;
    } catch (e) {
      followupsCount = 0;
    }

    const byStatus = db.prepare('SELECT status, COUNT(*) as count FROM jobs GROUP BY status ORDER BY count DESC').all();
    const byPortal = db.prepare('SELECT portal, COUNT(*) as count FROM jobs GROUP BY portal ORDER BY count DESC').all();

    let skipReasons: any[] = [];
    try {
      skipReasons = db.prepare("SELECT COALESCE(skip_reason, 'Unspecified / Filter Mismatch') as reason, COUNT(*) as count FROM jobs WHERE status = 'skipped' GROUP BY reason ORDER BY count DESC LIMIT 10").all();
    } catch (e) {
      skipReasons = [];
    }

    const recentComms = db.prepare(
      'SELECT timestamp, company, email_subject, inferred_status FROM job_communications ORDER BY timestamp DESC LIMIT 20'
    ).all();

    const unhandledList = db.prepare(
      'SELECT portal, question, job_url, timestamp FROM unhandled_questions ORDER BY timestamp DESC LIMIT 20'
    ).all();

    db.close();

    return NextResponse.json({
      stats: { totalJobs, seenJobs, unhandledQuestions, followupsCount },
      byStatus,
      byPortal,
      skipReasons,
      recentComms,
      unhandledList,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
