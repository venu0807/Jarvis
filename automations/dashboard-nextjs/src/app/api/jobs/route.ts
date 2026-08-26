import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
import Database from 'better-sqlite3';
import path from 'path';

export async function GET() {
  try {
    const dbPath = path.resolve(process.cwd(), '../job-automation/output/jobs.db');
    let jobs = [];
    
    try {
      const db = new Database(dbPath, { readonly: true });
      // Fetch applied jobs
      jobs = db.prepare("SELECT id, title, company, location, portal, url, description, status, timestamp FROM jobs WHERE status = 'applied' ORDER BY timestamp DESC LIMIT 500").all();
      
      // Fetch communications
      const comms = db.prepare("SELECT job_id, email_subject, email_snippet, inferred_status, timestamp FROM job_communications").all();
      db.close();

      // Merge communications into jobs
      const commsByJob: any = {};
      comms.forEach((c: any) => {
        if (!commsByJob[c.job_id]) commsByJob[c.job_id] = [];
        commsByJob[c.job_id].push(c);
      });

      jobs = jobs.map((job: any) => {
        const jobComms = commsByJob[job.id] || [];
        
        // Find if there is an overarching status update (e.g. rejected or interview)
        // Prefer rejected > interview > action_required > update_received > applied
        let finalStatus = job.status;
        for (const c of jobComms) {
          if (c.inferred_status === 'rejected') finalStatus = 'rejected';
          else if (c.inferred_status === 'interview' && finalStatus !== 'rejected') finalStatus = 'interview';
          else if (c.inferred_status === 'action_required' && finalStatus === 'applied') finalStatus = 'action_required';
        }

        return {
          ...job,
          status: finalStatus,
          communications: jobComms
        };
      });

    } catch (e) {
      console.error("SQLite error reading jobs:", e);
      return NextResponse.json({ error: "Failed to read database" }, { status: 500 });
    }
    
    return NextResponse.json({ jobs });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
