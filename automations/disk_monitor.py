#!/usr/bin/env python3
"""
disk_monitor.py — Disk Space Monitor for JARVIS

Monitors disk usage and alerts when thresholds are exceeded.
Run as a cron job (e.g., every 5 minutes).
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from alert_manager import get_alert_manager, alert_warning, alert_critical

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_WARNING_THRESHOLD = 80  # percent
DEFAULT_CRITICAL_THRESHOLD = 90  # percent

# Paths to monitor (add more as needed)
DEFAULT_PATHS = [
    "/home/venu",
    "/var/lib/docker",
    "/tmp",
]


@dataclass
class DiskUsage:
    """Disk usage information for a path."""
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    status: str  # "ok", "warning", "critical"


def get_disk_usage(path: str) -> DiskUsage:
    """Get disk usage for a path."""
    try:
        total, used, free = shutil.disk_usage(path)
        usage_percent = (used / total) * 100 if total > 0 else 0
        
        if usage_percent >= DEFAULT_CRITICAL_THRESHOLD:
            status = "critical"
        elif usage_percent >= DEFAULT_WARNING_THRESHOLD:
            status = "warning"
        else:
            status = "ok"
        
        return DiskUsage(
            path=path,
            total_gb=round(total / (1024**3), 2),
            used_gb=round(used / (1024**3), 2),
            free_gb=round(free / (1024**3), 2),
            usage_percent=round(usage_percent, 1),
            status=status,
        )
    except Exception as e:
        logger.error(f"Error getting disk usage for {path}: {e}")
        return DiskUsage(
            path=path,
            total_gb=0,
            used_gb=0,
            free_gb=0,
            usage_percent=0,
            status="error",
        )


def check_all_disks(paths: Optional[List[str]] = None) -> List[DiskUsage]:
    """Check disk usage for all specified paths."""
    paths = paths or DEFAULT_PATHS
    results = []
    for path in paths:
        if os.path.exists(path):
            results.append(get_disk_usage(path))
        else:
            logger.warning(f"Path does not exist: {path}")
    return results


def check_and_alert(
    paths: Optional[List[str]] = None,
    warning_threshold: int = DEFAULT_WARNING_THRESHOLD,
    critical_threshold: int = DEFAULT_CRITICAL_THRESHOLD,
) -> Dict[str, any]:
    """
    Check disk usage and send alerts if thresholds exceeded.
    
    Returns summary dict with overall status and any alerts sent.
    """
    global DEFAULT_WARNING_THRESHOLD, DEFAULT_CRITICAL_THRESHOLD
    DEFAULT_WARNING_THRESHOLD = warning_threshold
    DEFAULT_CRITICAL_THRESHOLD = critical_threshold
    
    usages = check_all_disks(paths)
    
    alerts_sent = []
    overall_status = "ok"
    
    for usage in usages:
        if usage.status == "critical":
            overall_status = "critical"
            # Send critical alert
            try:
                alert_critical(
                    title=f"Disk Critical: {usage.path}",
                    message=(
                        f"Disk usage at {usage.usage_percent}% "
                        f"({usage.used_gb}GB / {usage.total_gb}GB) on {usage.path}. "
                        f"Free: {usage.free_gb}GB. Immediate action required."
                    ),
                    source="disk-monitor",
                    path=usage.path,
                    usage_percent=usage.usage_percent,
                    free_gb=usage.free_gb,
                )
                alerts_sent.append({"path": usage.path, "level": "critical", "usage": usage.usage_percent})
            except Exception as e:
                logger.error(f"Failed to send critical alert for {usage.path}: {e}")
                
        elif usage.status == "warning" and overall_status != "critical":
            overall_status = "warning"
            # Send warning alert
            try:
                alert_warning(
                    title=f"Disk Warning: {usage.path}",
                    message=(
                        f"Disk usage at {usage.usage_percent}% "
                        f"({usage.used_gb}GB / {usage.total_gb}GB) on {usage.path}. "
                        f"Free: {usage.free_gb}GB. Consider cleanup."
                    ),
                    source="disk-monitor",
                    path=usage.path,
                    usage_percent=usage.usage_percent,
                    free_gb=usage.free_gb,
                )
                alerts_sent.append({"path": usage.path, "level": "warning", "usage": usage.usage_percent})
            except Exception as e:
                logger.error(f"Failed to send warning alert for {usage.path}: {e}")
    
    # Log summary
    logger.info(
        f"Disk check complete | status={overall_status} | "
        f"checked={len(usages)} | alerts={len(alerts_sent)}"
    )
    
    return {
        "status": overall_status,
        "checked_paths": len(usages),
        "alerts_sent": len(alerts_sent),
        "details": [asdict(u) for u in usages],
    }


def write_status_file(status: Dict, output_path: str = "/home/venu/.jarvis/disk_status.json"):
    """Write disk status to JSON file for Prometheus node_exporter or other consumers."""
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write status file: {e}")


if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Parse args
    paths = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Run check
    result = check_and_alert(paths)
    
    # Write status file
    write_status_file(result)
    
    # Print summary
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    if result["status"] == "critical":
        sys.exit(2)
    elif result["status"] == "warning":
        sys.exit(1)
    else:
        sys.exit(0)