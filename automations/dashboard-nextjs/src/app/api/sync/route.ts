import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';

import { GET as getStats } from '../stats/route';
import { GET as getAnalytics } from '../analytics/route';
import { GET as getLesson } from '../lesson/route';
import { GET as getAlerts } from '../alerts/route';
import { GET as getAutomations } from '../automations/route';

export async function GET(req: Request) {
  try {
    // Run all internal route handlers concurrently on the server
    const [statsRes, analyticsRes, lessonRes, alertsRes, autoRes] = await Promise.all([
      getStats(),
      getAnalytics(),
      getLesson(),
      getAlerts(),
      getAutomations()
    ]);

    // Parse the JSON responses from each handler
    const stats = await statsRes.json();
    const analytics = await analyticsRes.json();
    const lesson = await lessonRes.json();
    const alerts = await alertsRes.json();
    const auto = await autoRes.json();

    // Return the aggregated payload
    return NextResponse.json({
      stats,
      analytics,
      lesson,
      alerts,
      auto
    });
  } catch (error: any) {
    console.error("Sync API Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
