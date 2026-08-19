"""
Analytics Dashboard Generator
==============================
Generates a beautiful real-time HTML analytics dashboard by reading from
the PostgreSQL database. Shows pin counts, earnings estimates, template
distribution, board performance, and daily posting trends.

Usage:
    python analytics_dashboard.py          # Generate and open dashboard
    python analytics_dashboard.py --serve  # Serve on localhost:8080
"""

import os
import sys
import json
import datetime
import webbrowser
from database import get_products_df

OUT_FILE = "analytics/dashboard.html"

def generate_dashboard():
    os.makedirs("analytics", exist_ok=True)

    print("📊 Loading data from database...")
    df = get_products_df()
    df = df.fillna("")

    total = len(df)
    pinned = len(df[df["Status"].astype(str).str.lower() == "pinned"])
    pending = total - pinned
    progress_pct = round((pinned / total * 100) if total > 0 else 0, 1)

    # Earnings estimate
    est_monthly_views = pinned * 150
    est_clicks = round(est_monthly_views * 0.02)
    est_earnings = round(est_clicks * 0.45, 2)

    # Board breakdown
    board_counts = (
        df[df["Status"].astype(str).str.lower() == "pinned"]
        .groupby("Board")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .to_dict()
    )

    # Category breakdown (all products)
    cat_counts = (
        df.groupby("Category")
        .size()
        .sort_values(ascending=False)
        .to_dict()
    )

    # Pending by category
    pending_by_cat = (
        df[df["Status"].astype(str).str.lower() != "pinned"]
        .groupby("Category")
        .size()
        .sort_values(ascending=False)
        .to_dict()
    )

    board_labels = json.dumps(list(board_counts.keys()))
    board_data = json.dumps(list(board_counts.values()))
    cat_labels = json.dumps(list(cat_counts.keys()))
    cat_data = json.dumps(list(cat_counts.values()))

    now = datetime.datetime.now().strftime("%B %d, %Y — %I:%M %p")

    board_rows = "\n".join([
        f'<tr><td>{b}</td><td><div class="bar-wrap"><div class="bar" style="width:{min(100, round(c/max(board_counts.values(),default=1)*100))}%"></div></div></td><td class="num">{c}</td></tr>'
        for b, c in board_counts.items()
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Jarvis Analytics Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface2: #21253a;
      --accent: #7c6af7;
      --accent2: #f97316;
      --green: #22c55e;
      --red: #ef4444;
      --text: #e2e8f0;
      --muted: #64748b;
      --border: #2d3348;
    }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; padding: 30px; }}
    h1 {{ font-size: 28px; font-weight: 800; margin-bottom: 6px; }}
    .subtitle {{ color: var(--muted); font-size: 14px; margin-bottom: 32px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 28px; }}
    .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; }}
    .card.accent {{ background: linear-gradient(135deg, #7c6af7 0%, #5b4fcd 100%); border-color: transparent; }}
    .card.green {{ background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); border-color: transparent; }}
    .card.orange {{ background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); border-color: transparent; }}
    .card.blue {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-color: transparent; }}
    .card-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.75; margin-bottom: 8px; }}
    .card-value {{ font-size: 42px; font-weight: 800; line-height: 1; }}
    .card-sub {{ font-size: 13px; opacity: 0.8; margin-top: 8px; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px; }}
    .full-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; }}
    h3 {{ font-size: 16px; font-weight: 700; margin-bottom: 20px; }}
    .progress-wrap {{ background: var(--border); border-radius: 99px; height: 12px; margin: 16px 0 8px; overflow: hidden; }}
    .progress-bar {{ height: 100%; background: linear-gradient(90deg, var(--accent), #a78bfa); border-radius: 99px; transition: width 1s ease; }}
    .progress-label {{ display: flex; justify-content: space-between; font-size: 13px; color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th {{ text-align: left; color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }}
    td {{ padding: 12px 0; border-bottom: 1px solid var(--border); vertical-align: middle; }}
    td.num {{ text-align: right; font-weight: 700; color: var(--accent); font-size: 16px; }}
    .bar-wrap {{ background: var(--border); border-radius: 99px; height: 8px; flex: 1; margin: 0 12px; }}
    .bar {{ height: 100%; background: linear-gradient(90deg, var(--accent), #a78bfa); border-radius: 99px; }}
    .badge {{ display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; background: rgba(124,106,247,0.15); color: var(--accent); }}
    .earnings-box {{ background: var(--surface2); border-radius: 12px; padding: 20px; margin-top: 20px; }}
    .earnings-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; }}
    .earnings-row:last-child {{ border-bottom: none; font-weight: 700; color: var(--green); font-size: 16px; }}
    footer {{ text-align: center; color: var(--muted); font-size: 12px; margin-top: 32px; }}
    canvas {{ max-height: 260px; }}
  </style>
</head>
<body>
  <h1>📌 Jarvis Analytics Dashboard</h1>
  <p class="subtitle">Last updated: {now} &nbsp;·&nbsp; Auto-refreshes every 60s</p>

  <div class="grid">
    <div class="card accent">
      <div class="card-label">Total Pins Posted</div>
      <div class="card-value">{pinned}</div>
      <div class="card-sub">out of {total} total products</div>
    </div>
    <div class="card green">
      <div class="card-label">Est. Monthly Views</div>
      <div class="card-value">{est_monthly_views:,}</div>
      <div class="card-sub">at ~150 views/pin avg</div>
    </div>
    <div class="card orange">
      <div class="card-label">Est. Monthly Clicks</div>
      <div class="card-value">{est_clicks:,}</div>
      <div class="card-sub">at 2% CTR</div>
    </div>
    <div class="card blue">
      <div class="card-label">Est. Monthly Earnings</div>
      <div class="card-value">${est_earnings}</div>
      <div class="card-sub">at $0.45/click avg</div>
    </div>
  </div>

  <div class="full-card" style="margin-bottom:28px">
    <h3>📈 Posting Progress</h3>
    <div class="progress-wrap">
      <div class="progress-bar" style="width:{progress_pct}%"></div>
    </div>
    <div class="progress-label">
      <span>✅ {pinned} pinned</span>
      <span style="color:#7c6af7;font-weight:700">{progress_pct}% complete</span>
      <span>⏳ {pending} pending</span>
    </div>
    <div class="earnings-box">
      <div class="earnings-row"><span>💡 At 500+ pins</span><span>Real passive income begins</span></div>
      <div class="earnings-row"><span>📌 Current pins</span><span>{pinned}</span></div>
      <div class="earnings-row"><span>🎯 Pins to milestone</span><span>{max(0, 500-pinned)} more</span></div>
      <div class="earnings-row"><span>💰 Projected monthly (at 500)</span><span>~${round(500*150*0.02*0.45)}</span></div>
    </div>
  </div>

  <div class="two-col">
    <div class="full-card">
      <h3>🎯 Top Performing Boards</h3>
      <table>
        <thead><tr><th>Board</th><th></th><th>Pins</th></tr></thead>
        <tbody>{board_rows}</tbody>
      </table>
    </div>
    <div class="full-card">
      <h3>🏷️ Category Distribution</h3>
      <canvas id="catChart"></canvas>
    </div>
  </div>

  <script>
    // Category donut chart
    const ctx = document.getElementById('catChart').getContext('2d');
    new Chart(ctx, {{
      type: 'doughnut',
      data: {{
        labels: {cat_labels},
        datasets: [{{
          data: {cat_data},
          backgroundColor: ['#7c6af7','#f97316','#22c55e','#3b82f6','#ec4899','#eab308','#14b8a6','#8b5cf6','#f43f5e','#06b6d4'],
          borderWidth: 0,
          hoverOffset: 8
        }}]
      }},
      options: {{
        cutout: '68%',
        plugins: {{
          legend: {{ position: 'right', labels: {{ color: '#e2e8f0', font: {{ size: 12 }}, padding: 14 }} }}
        }}
      }}
    }});

    // Auto-refresh every 60 seconds
    setTimeout(() => location.reload(), 60000);
  </script>
  <footer>Jarvis Pinterest Automation · Amazon Associates · Built with ❤️</footer>
</body>
</html>"""

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  ✅ Dashboard saved: {os.path.abspath(OUT_FILE)}")
    return os.path.abspath(OUT_FILE)


if __name__ == "__main__":
    path = generate_dashboard()
    if "--serve" in sys.argv:
        import http.server, socketserver, threading
        os.chdir("analytics")
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", 8080), handler) as httpd:
            print(f"  🌐 Serving at http://localhost:8080")
            webbrowser.open("http://localhost:8080/dashboard.html")
            httpd.serve_forever()
    else:
        webbrowser.open(f"file://{path}")
