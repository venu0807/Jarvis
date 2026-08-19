import os
import json
from database import get_products_df

def generate_dashboard():
    df = get_products_df().fillna("")
    
    if df.empty:
        print("Database is empty. Run refill first.")
        return
        
    total_products = len(df)
    
    # Clean up status strings
    df["Status"] = df["Status"].astype(str).str.strip().str.lower()
    pinned = len(df[df["Status"] == "pinned"])
    pending = total_products - pinned
    
    # Category Breakdown
    category_counts = df["Category"].value_counts().to_dict()
    
    # Template Breakdown
    template_counts = df["Pin_Template"].replace("", "auto").value_counts().to_dict()
    
    # Earnings potential
    estimated_views = pinned * 5
    estimated_clicks = int(estimated_views * 0.01)
    estimated_earnings = int(estimated_clicks * 0.50)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pinterest Automation Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ background-color: #f8fafc; font-family: 'Inter', sans-serif; }}
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-7xl mx-auto">
            <h1 class="text-4xl font-bold text-slate-800 mb-2">📌 Pinterest Bot Dashboard</h1>
            <p class="text-slate-500 mb-8">Zero-Cost Scaling Command Center</p>
            
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h3 class="text-slate-500 text-sm font-semibold uppercase tracking-wider mb-2">Total Products</h3>
                    <p class="text-4xl font-bold text-slate-800">{total_products}</p>
                </div>
                <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h3 class="text-slate-500 text-sm font-semibold uppercase tracking-wider mb-2">Successfully Pinned</h3>
                    <p class="text-4xl font-bold text-green-600">{pinned}</p>
                </div>
                <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h3 class="text-slate-500 text-sm font-semibold uppercase tracking-wider mb-2">Pending Queue</h3>
                    <p class="text-4xl font-bold text-amber-500">{pending}</p>
                </div>
                <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h3 class="text-slate-500 text-sm font-semibold uppercase tracking-wider mb-2">Est. Monthly Earnings</h3>
                    <p class="text-4xl font-bold text-blue-600">${estimated_earnings}</p>
                    <p class="text-xs text-slate-400 mt-1">Based on {estimated_views} est. views</p>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h3 class="text-slate-800 text-lg font-bold mb-4">Product Categories</h3>
                    <canvas id="categoryChart"></canvas>
                </div>
                <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h3 class="text-slate-800 text-lg font-bold mb-4">Template Distribution</h3>
                    <canvas id="templateChart"></canvas>
                </div>
            </div>
        </div>
        
        <script>
            // Category Chart
            const ctxCat = document.getElementById('categoryChart').getContext('2d');
            new Chart(ctxCat, {{
                type: 'doughnut',
                data: {{
                    labels: {list(category_counts.keys())},
                    datasets: [{{
                        data: {list(category_counts.values())},
                        backgroundColor: ['#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#d946ef', '#f43f5e']
                    }}]
                }},
                options: {{ responsive: true }}
            }});
            
            // Template Chart
            const ctxTpl = document.getElementById('templateChart').getContext('2d');
            new Chart(ctxTpl, {{
                type: 'bar',
                data: {{
                    labels: {list(template_counts.keys())},
                    datasets: [{{
                        label: 'Pins',
                        data: {list(template_counts.values())},
                        backgroundColor: '#3b82f6'
                    }}]
                }},
                options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"✅ Dashboard successfully generated at: file://{os.path.abspath('dashboard.html')}")

if __name__ == "__main__":
    generate_dashboard()
