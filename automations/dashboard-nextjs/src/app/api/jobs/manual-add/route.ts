import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
import Database from 'better-sqlite3';
import path from 'path';

function detectPortal(url: string): string {
  try {
    const host = new URL(url).hostname.toLowerCase();
    if (host.includes('naukri')) return 'Naukri (Manual)';
    if (host.includes('indeed')) return 'Indeed (Manual)';
    if (host.includes('internshala')) return 'Internshala (Manual)';
    if (host.includes('foundit') || host.includes('monster')) return 'Foundit (Manual)';
    if (host.includes('linkedin')) return 'LinkedIn (Manual)';
    if (host.includes('cuvette')) return 'Cuvette (Manual)';
    if (host.includes('unstop')) return 'Unstop (Manual)';
    return `${host.replace('www.', '')} (Direct)`;
  } catch {
    return 'Manual Apply';
  }
}

// Smart URL Slug Deconstructor & AI Parser
async function parseJobUrlSmart(url: string) {
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(url);
  } catch {
    return null;
  }

  const host = parsedUrl.hostname.toLowerCase();
  const pathname = parsedUrl.pathname;
  const portal = detectPortal(url);

  let company = '';
  let title = '';
  let location = 'Remote / India';
  let desc = '';

  // 1. NAUKRI URL PARSER
  if (host.includes('naukri.com')) {
    const m = pathname.match(/\/job-listings-(.+)-([0-9]{10,})/);
    if (m) {
      const slug = m[1];
      const expMatch = slug.match(/([0-9]+-to-[0-9]+-years?)/);
      const expStr = expMatch ? expMatch[1].replace(/-/g, ' ') : 'Fresher (0-2 Yrs)';
      const slugClean = expMatch ? slug.slice(0, expMatch.index).replace(/-+$/, '') : slug;

      const tokens = slugClean.split('-').filter(Boolean);
      const cities = ['visakhapatnam', 'vizag', 'hyderabad', 'bengaluru', 'bangalore', 'chennai', 'mumbai', 'pune', 'delhi', 'noida', 'gurgaon', 'gurugram', 'kolkata'];
      let foundCity = (tokens.includes('visakhapatnam') || tokens.includes('vizag')) ? 'Visakhapatnam' : 'India';

      for (const c of cities) {
        if (tokens.includes(c)) {
          foundCity = c.charAt(0).toUpperCase() + c.slice(1);
          const idx = tokens.indexOf(c);
          if (idx !== -1) tokens.splice(idx, 1);
          break;
        }
      }
      location = foundCity;

      // Ask local Ollama to cleanly separate Title & Company
      const prompt = `Given this job slug from Naukri: "${tokens.join(' ')}"
Extract strictly JSON:
{
  "title": "Job Title (e.g. Software Tester)",
  "company": "Company or Recruiter Name (e.g. Harish Terli)"
}
Output only JSON:`;

      try {
        const llmRes = await fetch('http://127.0.0.1:11434/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: 'qwen2.5-coder:3b', prompt: prompt, stream: false })
        });
        if (llmRes.ok) {
          const resJson = await llmRes.json();
          let txt = (resJson.response || '').trim();
          if (txt.includes('```')) {
            txt = txt.split('```')[1];
            if (txt.startsWith('json')) txt = txt.slice(4);
            txt = txt.trim();
          }
          const parsed = JSON.parse(txt);
          title = parsed.title || title;
          company = parsed.company || company;
        }
      } catch (e) {
        console.warn('Ollama parse error:', e);
      }

      if (!title) title = tokens.slice(0, 2).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
      if (!company) company = tokens.slice(2).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') || 'Direct Recruiter';

      desc = `Role: ${title}\nCompany: ${company}\nLocation: ${location}\nExperience: ${expStr}\nJob Portal: Naukri\nJob URL: ${url}\n\nKey Responsibilities:\n- Software Quality Assurance, Testing, defect reporting, and verification.\n- Knowledge of SDLC, STLC, Bug Life Cycle, and test management tools.`;
    }
  }

  // 2. INTERNSHALA URL PARSER
  else if (host.includes('internshala.com')) {
    const m = pathname.match(/\/internship\/detail\/(.+)-internship-at-(.+?)(?:-\d+|$)/);
    if (m) {
      title = m[1].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      company = m[2].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      desc = `Internship Role: ${title} at ${company}\nSource: Internshala\nJob URL: ${url}`;
    }
  }

  // 3. INDEED URL PARSER
  else if (host.includes('indeed.com')) {
    const qMatch = parsedUrl.searchParams.get('q');
    const lMatch = parsedUrl.searchParams.get('l');
    if (qMatch) title = qMatch;
    if (lMatch) location = lMatch;
    desc = `Job application from Indeed: ${url}`;
  }

  return {
    company: company || 'Direct Recruiter',
    title: title || 'Software Developer',
    location: location,
    portal: portal,
    description: desc || `Application link: ${url}`
  };
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { action, url, title, company, location, description, portal } = body;

    const dbPath = path.resolve(process.cwd(), '../job-automation/output/jobs.db');

    // ACTION 1: SMART FETCH DETAILS
    if (action === 'fetch') {
      if (!url) {
        return NextResponse.json({ error: 'URL is required to fetch details' }, { status: 400 });
      }

      // 1. Try Smart URL Slug Deconstruction first
      const smartResult = await parseJobUrlSmart(url);

      // 2. Also attempt HTML scrape if possible
      let pageText = '';
      try {
        const pageRes = await fetch(url, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
          },
          signal: AbortSignal.timeout(6000)
        });

        if (pageRes.ok) {
          const html = await pageRes.text();
          let clean = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ' ');
          clean = clean.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, ' ');
          clean = clean.replace(/<[^>]+>/g, ' ');
          clean = clean.replace(/\s+/g, ' ').trim();
          pageText = clean.slice(0, 3000);
        }
      } catch (e) {
        // Fetch failed due to bot firewall, smartResult will be used!
      }

      if (smartResult && smartResult.company && smartResult.company !== 'Direct Recruiter') {
        return NextResponse.json({
          success: true,
          company: smartResult.company,
          title: smartResult.title,
          location: smartResult.location,
          portal: smartResult.portal,
          description: smartResult.description,
          url: url
        });
      }

      // If smartResult was generic but pageText was fetched:
      if (pageText.length > 100) {
        try {
          const prompt = `Extract JSON from job text:
${pageText}
Output only JSON: {"company": "...", "title": "...", "location": "...", "description": "..."}`;

          const llmRes = await fetch('http://127.0.0.1:11434/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: 'qwen2.5-coder:3b', prompt: prompt, stream: false })
          });

          if (llmRes.ok) {
            const llmData = await llmRes.json();
            let text = (llmData.response || '').trim();
            if (text.includes('```')) {
              text = text.split('```')[1];
              if (text.startsWith('json')) text = text.slice(4);
              text = text.trim();
            }
            const parsed = JSON.parse(text);
            return NextResponse.json({
              success: true,
              company: parsed.company || smartResult?.company || 'Direct Recruiter',
              title: parsed.title || smartResult?.title || 'Software Developer',
              location: parsed.location || smartResult?.location || 'Remote / India',
              portal: smartResult?.portal || detectPortal(url),
              description: parsed.description || smartResult?.description || pageText.slice(0, 400),
              url: url
            });
          }
        } catch (llmErr) {
          console.warn(llmErr);
        }
      }

      return NextResponse.json({
        success: true,
        company: smartResult?.company || 'Direct Recruiter',
        title: smartResult?.title || 'Software Developer',
        location: smartResult?.location || 'Remote / India',
        portal: smartResult?.portal || detectPortal(url),
        description: smartResult?.description || `Application URL: ${url}`,
        url: url
      });
    }

    // ACTION 2: SAVE JOB TO DATABASE
    if (action === 'save') {
      if (!company || !title) {
        return NextResponse.json({ error: 'Company and Title are required' }, { status: 400 });
      }

      const jobId = `manual_${Date.now()}`;
      const now = new Date().toISOString();
      const jobPortal = portal || detectPortal(url || '');

      const db = new Database(dbPath);
      db.prepare(`
        INSERT INTO jobs (id, title, company, location, portal, url, description, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'applied', ?)
      `).run(
        jobId,
        title.trim(),
        company.trim(),
        (location || 'Remote / India').trim(),
        jobPortal,
        url || '',
        (description || '').trim(),
        now
      );
      db.close();

      return NextResponse.json({
        success: true,
        job: {
          id: jobId,
          title: title.trim(),
          company: company.trim(),
          location: (location || 'Remote / India').trim(),
          portal: jobPortal,
          url: url || '',
          description: (description || '').trim(),
          status: 'applied',
          timestamp: now
        }
      });
    }

    return NextResponse.json({ error: 'Invalid action specified' }, { status: 400 });

  } catch (error: any) {
    console.error('Manual add error:', error);
    return NextResponse.json({ error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}
