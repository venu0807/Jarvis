import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';

export async function GET() {
  try {
    const prepDir = path.resolve(process.cwd(), '../interview_scheduler_prep_bot/prep_sheets');
    const icsDir = path.resolve(process.cwd(), '../job-automation/output/interviews');
    const dbPath = path.resolve(process.cwd(), '../job-automation/output/jobs.db');

    const interviews: any[] = [];
    const seenCompanies = new Set<string>();

    if (fs.existsSync(prepDir)) {
      const files = fs.readdirSync(prepDir).filter(f => f.endsWith('.md'));
      
      let db: any = null;
      try {
        if (fs.existsSync(dbPath)) {
          db = new Database(dbPath, { readonly: true });
        }
      } catch (e) {
        console.error("DB open error:", e);
      }

      for (const file of files) {
        const filePath = path.join(prepDir, file);
        const stats = fs.statSync(filePath);
        const content = fs.readFileSync(filePath, 'utf-8');

        const rawComp = file.replace(/_prep_sheet\.md$/i, '').replace(/_/g, ' ');
        const companyName = rawComp.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        
        seenCompanies.add(companyName.toLowerCase());

        let jobInfo: any = {
          title: 'Software Tester & Developer',
          location: 'Noida / Remote',
          portal: 'Naukri / Direct',
          url: '',
          applied_at: stats.mtime.toISOString().split('T')[0]
        };

        if (db) {
          try {
            const firstWord = companyName.split(' ')[0];
            const row = db.prepare("SELECT title, location, portal, url, timestamp FROM jobs WHERE company LIKE ? OR company LIKE ? ORDER BY id DESC LIMIT 1").get(`%${companyName}%`, `%${firstWord}%`);
            if (row) {
              jobInfo = {
                title: row.title || jobInfo.title,
                location: row.location || jobInfo.location,
                portal: row.portal || jobInfo.portal,
                url: row.url || '',
                applied_at: row.timestamp ? row.timestamp.split('T')[0] : jobInfo.applied_at
              };
            }
          } catch (err) {
            console.error("DB match error:", err);
          }
        }

        let icsFile = '';
        if (fs.existsSync(icsDir)) {
          const icsFiles = fs.readdirSync(icsDir).filter(f => f.endsWith('.ics'));
          const matchIcs = icsFiles.find(f => f.toLowerCase().includes(companyName.toLowerCase()) || f.toLowerCase().includes(rawComp.toLowerCase()));
          if (matchIcs) {
            icsFile = matchIcs;
          }
        }

        interviews.push({
          id: file.replace('.md', ''),
          company: companyName,
          title: jobInfo.title,
          location: jobInfo.location,
          portal: jobInfo.portal,
          url: jobInfo.url,
          applied_at: jobInfo.applied_at,
          updated_at: stats.mtime.toISOString(),
          content: content,
          has_calendar: !!icsFile,
          calendar_file: icsFile
        });
      }

      if (db) {
        db.close();
      }
    }

    interviews.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

    return NextResponse.json({ interviews });
  } catch (error: any) {
    console.error("Interviews API error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const { company, title, description } = await req.json();
    if (!company) {
      return NextResponse.json({ error: 'Company name required' }, { status: 400 });
    }

    const prepDir = path.resolve(process.cwd(), '../interview_scheduler_prep_bot/prep_sheets');
    if (!fs.existsSync(prepDir)) {
      fs.mkdirSync(prepDir, { recursive: true });
    }

    const prompt = `You are an elite Silicon Valley technical interview coach and QA/Engineering Lead.
I have an interview with ${company} for the role of "${title || 'Software Tester & QA Developer'}".

Job Description / Notes:
${description || 'Software Tester / QA Automation Engineer & Python Developer (Manual testing, Playwright, PyTest, REST API testing, SQL queries, Python DSA, Bug Life Cycle, SDLC/STLC).'}

Generate an exhaustive, comprehensive, 360-degree Master Interview Preparation Guide in clean Markdown:
1. **🏢 Company & Domain Context**: 1-sentence mission, core business products, and key architecture components.
2. **🧪 Core Technical Competencies & Deep Dives**: Detailed explanation and talking points for:
   - SDLC vs STLC, Test Design Techniques (BVA, ECP, Decision Tables), Bug Life Cycle (Severity vs Priority).
   - Test Automation (Playwright/Selenium, PyTest fixtures, POM architecture).
   - REST API Testing (HTTP methods, status codes, payload validation).
   - SQL & DB verification queries (Joins, Aggregations, Data integrity checks).
3. **💻 Real-World Domain Test Scenarios & Edge Cases**: 3 specific complex test scenarios relevant to this company's platform.
4. **🐍 High-Frequency Technical & Coding Challenges**: 3 Python coding/logic questions with concise solutions.
5. **🗣️ Behavioral & Situational Questions (STAR Method)**: "Tell me about yourself", handling developer disagreements on bugs, and tight deadline prioritization.
6. **💡 Strategic Reverse Questions**: 3 high-impact questions to ask the interviewer.

Format with clear markdown tables, code snippets, bold highlights, and clean typography.`;

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
      return NextResponse.json({ error: 'Failed to generate prep with local LLM' }, { status: 500 });
    }

    const json = await response.json();
    const mdContent = json.response || "No content generated.";

    const safeName = company.toLowerCase().replace(/[^a-z0-9]/g, '_');
    const filePath = path.join(prepDir, `${safeName}_prep_sheet.md`);
    fs.writeFileSync(filePath, mdContent, 'utf-8');

    return NextResponse.json({
      success: true,
      company,
      content: mdContent,
      file: `${safeName}_prep_sheet.md`
    });
  } catch (error: any) {
    console.error("Save prep error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
