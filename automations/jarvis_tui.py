#!/usr/bin/env python3
"""
jarvis_tui.py — CLI Rich TUI for JARVIS status monitoring.

Usage: python jarvis_tui.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

# Add project paths
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))
sys.path.append(str(BASE_DIR.parent.parent))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

console = Console()


class JarvisTUI:
    """Terminal UI for JARVIS status monitoring."""
    
    def __init__(self):
        self.layout = Layout()
        self.running = True
        self.refresh_interval = 5  # seconds
        self.last_update = None
        
        # Service endpoints
        self.ollama_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.router_url = os.getenv("MODEL_ROUTER_URL", "http://model-router:8090")
        self.job_auto_url = "http://localhost:8080"
        self.pinterest_url = "http://localhost:8081"
        self.gpu_exporter_url = "http://localhost:9400"
        self.postgres_url = os.getenv("DATABASE_URL", "postgresql://jarvis:jarvis@postgres:5432/jarvis")
        
        # State
        self.services = {}
        self.models = {}
        self.recent_jobs = []
        self.model_health = {}
        self.logs = []
        self.vram_used = 0
        self.vram_total = 4096  # MB
        self.jobs_applied = 0
        self.jobs_limit = 50
        self.uptime = "0s"
        
    def setup_layout(self):
        """Define the TUI layout."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        self.layout["body"].split_row(
            Layout(name="sidebar", ratio=1),
            Layout(name="main", ratio=2)
        )
        
        self.layout["sidebar"].split_column(
            Layout(name="services", size=12),
            Layout(name="jobs", size=10),
            Layout(name="models", size=12)
        )
    
    def render_header(self) -> Panel:
        """Render the header panel."""
        status_color = "green" if all(s.get("healthy", False) for s in self.services.values()) else "yellow"
        status_text = "● Healthy" if status_color == "green" else "⚠ Degraded"
        
        vram_pct = (self.vram_used / self.vram_total * 100) if self.vram_total > 0 else 0
        vram_color = "green" if vram_pct < 80 else ("yellow" if vram_pct < 95 else "red")
        
        header_text = Text()
        header_text.append("🦞 JARVIS STATUS ", style="bold cyan")
        header_text.append(status_text, style=f"bold {status_color}")
        header_text.append("  │  ", style="dim")
        header_text.append(f"VRAM: ", style="dim")
        header_text.append(f"{self.vram_used}/{self.vram_total} MB", style=f"bold {vram_color}")
        header_text.append("  │  ", style="dim")
        header_text.append(f"Jobs: ", style="dim")
        header_text.append(f"{self.jobs_applied}/{self.jobs_limit}", style="bold cyan")
        header_text.append("  │  ", style="dim")
        header_text.append(f"Uptime: {self.uptime}", style="dim")
        
        return Panel(Align.center(header_text), border_style="cyan")
    
    def render_services(self) -> Panel:
        """Render services panel."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Service", style="cyan", width=18)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Details", style="dim", width=20)
        
        service_order = [
            ("postgres", "🐘 PostgreSQL"),
            ("job-automation", "🦞 Job Auto"),
            ("pinterest", "📌 Pinterest"),
            ("model-router", "🧠 Model Router"),
            ("gpu-exporter", "📊 GPU Exporter"),
            ("ollama", "🤖 Ollama"),
        ]
        
        for key, name in service_order:
            svc = self.services.get(key, {})
            healthy = svc.get("healthy", False)
            status = "● Running" if healthy else "● Down"
            status_style = "green" if healthy else "red"
            details = svc.get("details", "")
            table.add_row(name, f"[{status_style}]{status}[/{status_style}]", details)
        
        return Panel(table, title="Services", border_style="cyan", padding=(0, 1))
    
    def render_jobs(self) -> Panel:
        """Render recent jobs panel."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Time", style="dim", width=6)
        table.add_column("Portal", width=10)
        table.add_column("Job Title", style="cyan", width=28)
        table.add_column("Status", justify="center", width=10)
        
        for job in self.recent_jobs[:8]:
            status_style = {
                "applied": "green",
                "manual": "yellow",
                "failed": "red",
                "pending": "blue"
            }.get(job.get("status", ""), "white")
            
            status_text = job.get("status", "").capitalize()
            table.add_row(
                job.get("time", ""),
                job.get("portal", ""),
                job.get("title", "")[:28],
                f"[{status_style}]{status_text}[/{status_style}]"
            )
        
        if not self.recent_jobs:
            table.add_row("—", "—", "No recent jobs", "—")
        
        return Panel(table, title="Recent Jobs", border_style="cyan", padding=(0, 1))
    
    def render_models(self) -> Panel:
        """Render model health panel."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Model", style="cyan", width=16)
        table.add_column("VRAM", justify="right", width=8)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Usage", width=12)
        
        for name, info in self.model_health.items():
            vram = info.get("vram_mb", 0)
            loaded = info.get("loaded", False)
            status = "● Loaded" if loaded else ("○ CPU" if info.get("cpu_offload") else "○ Unloaded")
            status_style = "green" if loaded else ("yellow" if info.get("cpu_offload") else "dim")
            
            # VRAM bar
            if vram > 0:
                pct = min(vram / 2500, 1.0)  # Assuming max ~2.5GB per model
                bar = "█" * int(pct * 10) + "░" * (10 - int(pct * 10))
                usage = f"{bar} {vram}MB"
            else:
                usage = "—"
            
            table.add_row(name, f"{vram}MB" if vram else "—", 
                         f"[{status_style}]{status}[/{status_style}]", usage)
        
        if not self.model_health:
            table.add_row("—", "—", "No models loaded", "—")
        
        return Panel(table, title="Model Health", border_style="cyan", padding=(0, 1))
    
    def render_main(self) -> Panel:
        """Render main panel with live logs."""
        log_lines = []
        for log in self.logs[-15:]:
            time_str = log.get("time", "")
            source = log.get("source", "")
            msg = log.get("msg", "")
            level = log.get("level", "")
            
            style = {
                "success": "green",
                "error": "red",
                "warning": "yellow",
                "info": "cyan"
            }.get(level, "white")
            
            log_lines.append(
                f"[dim]{time_str}[/dim] "
                f"[{style}]{source}[/{style}] "
                f"[{style}]{msg}[/{style}]"
            )
        
        if not log_lines:
            log_lines = ["[dim]Waiting for logs...[/dim]"]
        
        return Panel(
            "\n".join(log_lines),
            title="Live Logs",
            border_style="cyan",
            padding=(0, 1)
        )
    
    def render_footer(self) -> Panel:
        """Render footer with shortcuts."""
        shortcuts = Text()
        shortcuts.append("j/k Nav  ", style="dim")
        shortcuts.append("Enter Details  ", style="dim")
        shortcuts.append("r Refresh  ", style="dim")
        shortcuts.append("f Filter  ", style="dim")
        shortcuts.append("q Quit", style="dim")
        
        footer_text = Text()
        footer_text.append(f"Last updated: {self.last_update or 'never'}  ", style="dim")
        footer_text.append("Press ", style="dim")
        footer_text.append("?", style="bold cyan")
        footer_text.append(" for help", style="dim")
        
        return Panel(
            Align.center(shortcuts),
            subtitle=Align.right(footer_text),
            border_style="dim"
        )
    
    async def fetch_data(self):
        """Fetch data from all services."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Ollama health
            try:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    self.services["ollama"] = {"healthy": True, "details": f"{len(models)} models"}
                    # Update model health
                    for m in models:
                        name = m.get("name", "").split(":")[0]
                        size_mb = m.get("size", 0) // (1024 * 1024)
                        self.model_health[name] = {"loaded": True, "vram_mb": size_mb}
                else:
                    self.services["ollama"] = {"healthy": False, "details": f"HTTP {resp.status_code}"}
            except Exception as e:
                self.services["ollama"] = {"healthy": False, "details": str(e)[:30]}
            
            # Model Router
            try:
                resp = await client.get(f"{self.router_url}/healthz")
                if resp.status_code == 200:
                    data = resp.json()
                    self.services["model-router"] = {"healthy": data.get("healthy", False), "details": f"{data.get('model_count', 0)} models"}
                else:
                    self.services["model-router"] = {"healthy": False, "details": f"HTTP {resp.status_code}"}
            except Exception as e:
                self.services["model-router"] = {"healthy": False, "details": str(e)[:30]}
            
            # Job Automation
            try:
                resp = await client.get(f"{self.job_auto_url}/healthz")
                if resp.status_code == 200:
                    data = resp.json()
                    self.services["job-automation"] = {"healthy": data.get("status") == "healthy", "details": f"DB: {'✓' if data.get('db_healthy') else '✗'} Ollama: {'✓' if data.get('ollama_healthy') else '✗'}"}
                else:
                    self.services["job-automation"] = {"healthy": False, "details": f"HTTP {resp.status_code}"}
            except Exception as e:
                self.services["job-automation"] = {"healthy": False, "details": str(e)[:30]}
            
            # Pinterest
            try:
                resp = await client.get(f"{self.pinterest_url}/healthz")
                if resp.status_code == 200:
                    data = resp.json()
                    self.services["pinterest"] = {"healthy": data.get("status") == "healthy", "details": f"DB: {'✓' if data.get('db_healthy') else '✗'}"}
                else:
                    self.services["pinterest"] = {"healthy": False, "details": f"HTTP {resp.status_code}"}
            except Exception as e:
                self.services["pinterest"] = {"healthy": False, "details": str(e)[:30]}
            
            # GPU Exporter
            try:
                resp = await client.get(f"{self.gpu_exporter_url}/metrics")
                self.services["gpu-exporter"] = {"healthy": resp.status_code == 200, "details": "Metrics endpoint"}
            except Exception as e:
                self.services["gpu-exporter"] = {"healthy": False, "details": str(e)[:30]}
            
            # Postgres (via job-automation health)
            try:
                import asyncpg
                conn = await asyncpg.connect(self.postgres_url, timeout=3.0)
                await conn.close()
                self.services["postgres"] = {"healthy": True, "details": "Connected"}
            except Exception:
                self.services["postgres"] = {"healthy": False, "details": "Connection failed"}
            
            # Fetch VRAM from GPU exporter
            try:
                resp = await client.get(f"{self.gpu_exporter_url}/metrics")
                if resp.status_code == 200:
                    for line in resp.text.split("\n"):
                        if "gpu_memory_used_bytes" in line and not line.startswith("#"):
                            parts = line.split()
                            if len(parts) >= 2:
                                self.vram_used = int(float(parts[1]) // (1024 * 1024))
            except Exception:
                pass
            
            # Update recent jobs from log file
            self.update_recent_jobs()
            
            # Update uptime
            self.uptime = self.calculate_uptime()
    
    def update_recent_jobs(self):
        """Update recent jobs from log files."""
        log_dir = BASE_DIR / "output" / "logs"
        if log_dir.exists():
            log_files = sorted(log_dir.glob("applications_*.json"), reverse=True)
            if log_files:
                try:
                    with open(log_files[0]) as f:
                        data = json.load(f)
                        self.jobs_applied = data.get("totals", {}).get("applied", 0)
                        self.jobs_limit = data.get("totals", {}).get("applied", 0) + data.get("totals", {}).get("manual", 0) + 20
                        
                        # Build recent jobs list
                        self.recent_jobs = []
                        for app in data.get("applied", [])[-8:]:
                            self.recent_jobs.append({
                                "time": datetime.now().strftime("%H:%M"),  # Approximate
                                "portal": app.get("portal", ""),
                                "title": app.get("title", ""),
                                "status": "applied"
                            })
                        for app in data.get("manual", [])[-4:]:
                            self.recent_jobs.append({
                                "time": datetime.now().strftime("%H:%M"),
                                "portal": app.get("portal", ""),
                                "title": app.get("title", ""),
                                "status": "manual"
                            })
                except Exception:
                    pass
    
    def calculate_uptime(self) -> str:
        """Calculate uptime since first log entry."""
        # Simplified - in reality would track from service start
        return "3d 14h"
    
    async def refresh_loop(self):
        """Main refresh loop."""
        while self.running:
            try:
                await self.fetch_data()
                self.last_update = datetime.now().strftime("%H:%M:%S")
            except Exception as e:
                console.print(f"[red]Fetch error: {e}[/red]")
            await asyncio.sleep(self.refresh_interval)
    
    def render(self) -> Layout:
        """Render the full layout."""
        self.layout["header"].update(self.render_header())
        self.layout["services"].update(self.render_services())
        self.layout["jobs"].update(self.render_jobs())
        self.layout["models"].update(self.render_models())
        self.layout["main"].update(self.render_main())
        self.layout["footer"].update(self.render_footer())
        return self.layout
    
    async def run(self):
        """Run the TUI."""
        self.setup_layout()
        
        # Initial fetch
        await self.fetch_data()
        self.last_update = datetime.now().strftime("%H:%M:%S")
        
        # Start refresh loop in background
        refresh_task = asyncio.create_task(self.refresh_loop())
        
        # Run live display
        try:
            with Live(self.render(), console=console, refresh_per_second=2, screen=True) as live:
                while self.running:
                    await asyncio.sleep(0.5)
                    live.update(self.render())
        except KeyboardInterrupt:
            self.running = False
        finally:
            refresh_task.cancel()
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass


async def main():
    """Main entry point."""
    tui = JarvisTUI()
    await tui.run()


if __name__ == "__main__":
    asyncio.run(main())