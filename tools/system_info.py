"""Potato PC Butler & System Hardware Diagnostics for Hope UltraLight:
Monitors CPU, RAM, battery, disk space, and top memory-hogging processes directly on your laptop.
"""

import os
import sys
import time
import shutil
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import psutil

from config import config

logger = logging.getLogger(__name__)


def get_pc_stats() -> Dict[str, Any]:
    """Gather real-time hardware and resource stats from the host laptop."""
    # 1. CPU
    cpu_pct = psutil.cpu_percent(interval=0.2)
    cpu_count = psutil.cpu_count(logical=True)

    # 2. Memory
    mem = psutil.virtual_memory()
    mem_used_gb = round(mem.used / (1024 ** 3), 2)
    mem_total_gb = round(mem.total / (1024 ** 3), 2)
    mem_pct = mem.percent

    # 3. Battery
    battery = psutil.sensors_battery()
    if battery:
        bat_pct = round(battery.percent)
        bat_plugged = "🔌 Plugged In" if battery.power_plugged else "🔋 On Battery"
        if battery.secsleft > 0:
            hrs = battery.secsleft // 3600
            mins = (battery.secsleft % 3600) // 60
            bat_time = f" (~{hrs}h {mins}m left)"
        else:
            bat_time = ""
        bat_status = f"{bat_pct}% ({bat_plugged}){bat_time}"
    else:
        bat_status = "Desktop / No Battery Detected"

    # 4. Storage / Disks
    disks = []
    partitions = psutil.disk_partitions(all=False)
    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            free_gb = round(usage.free / (1024 ** 3), 1)
            total_gb = round(usage.total / (1024 ** 3), 1)
            pct = usage.percent
            disks.append(f"`{p.device}` {free_gb} GB free / {total_gb} GB ({pct}% used)")
        except (PermissionError, OSError):
            continue

    # 5. Top 5 Memory Hogs
    top_procs = []
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                mem_mb = round(p.info['memory_info'].rss / (1024 ** 2), 1)
                procs.append((p.info['name'], mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x[1], reverse=True)
        top_procs = procs[:5]
    except Exception as e:
        logger.debug(f"Error fetching top processes: {e}")

    # 6. Uptime
    boot_time = psutil.boot_time()
    uptime_secs = int(time.time() - boot_time)
    days = uptime_secs // 86400
    hours = (uptime_secs % 86400) // 3600
    minutes = (uptime_secs % 3600) // 60
    uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

    return {
        "cpu_percent": cpu_pct,
        "cpu_cores": cpu_count,
        "mem_used_gb": mem_used_gb,
        "mem_total_gb": mem_total_gb,
        "mem_percent": mem_pct,
        "battery_status": bat_status,
        "disks": disks,
        "top_processes": top_procs,
        "uptime": uptime_str
    }


def format_pc_report() -> str:
    """Format system metrics into a clear Telegram Markdown report."""
    stats = get_pc_stats()

    # CPU status emoji
    cpu_emoji = "🟢" if stats["cpu_percent"] < 60 else ("🟡" if stats["cpu_percent"] < 85 else "🔴")
    mem_emoji = "🟢" if stats["mem_percent"] < 75 else ("🟡" if stats["mem_percent"] < 90 else "🔴")

    lines = [
        "💻 **Potato PC Hardware Status**",
        f"⏱️ **Uptime**: `{stats['uptime']}`\n",
        f"⚡ **CPU Usage**: {cpu_emoji} `{stats['cpu_percent']}%` ({stats['cpu_cores']} logical cores)",
        f"🧠 **RAM Usage**: {mem_emoji} `{stats['mem_used_gb']} GB` / `{stats['mem_total_gb']} GB` (`{stats['mem_percent']}%`)",
        f"🔋 **Battery**: {stats['battery_status']}\n",
        "💾 **Storage Space**:"
    ]

    for d in stats["disks"]:
        lines.append(f"• {d}")

    if stats["top_processes"]:
        lines.append("\n🚨 **Top 5 Memory Consumers**:")
        for name, mb in stats["top_processes"]:
            lines.append(f"• `{name}`: `{mb} MB`")

    return "\n".join(lines)


def clean_temp_files() -> str:
    """Clean safe temporary files from the system temp directory to free disk space."""
    temp_dir = Path(tempfile.gettempdir())
    freed_bytes = 0
    deleted_files = 0

    if not temp_dir.exists():
        return "Temp directory not accessible."

    for item in temp_dir.iterdir():
        try:
            if item.is_file():
                size = item.stat().st_size
                item.unlink(missing_ok=True)
                freed_bytes += size
                deleted_files += 1
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
        except Exception:
            # Files in active use cannot be deleted, ignore safely
            continue

    freed_mb = round(freed_bytes / (1024 ** 2), 2)
    return f"🧹 **Temp Cleanup Finished**:\nReclaimed `{freed_mb} MB` across {deleted_files} temporary files."

