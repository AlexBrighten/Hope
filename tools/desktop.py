"""Desktop & Application Management Tool for Hope UltraLight:
Empowers the agent to launch applications, inspect active windows/processes,
and control the local operating system desktop.
"""

import os
import sys
import psutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from config import config

logger = logging.getLogger(__name__)

# Critical operating system processes that must NEVER be terminated
PROTECTED_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "svchost.exe", "explorer.exe",
    "fontdrvhost.exe", "winlogon.exe", "dwm.exe", "spoolsv.exe"
}


def list_running_apps(limit: int = 15) -> str:
    """List major interactive applications currently running on the laptop."""
    apps = []
    try:
        for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                name = p.info['name']
                # Skip protected system processes
                if name.lower() in PROTECTED_PROCESSES:
                    continue
                mem_mb = round(p.info['memory_info'].rss / (1024 ** 2), 1)
                if mem_mb > 50:  # Only report apps using meaningful memory (>50MB)
                    apps.append((name, p.info['pid'], mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by RAM usage descending
        apps.sort(key=lambda x: x[2], reverse=True)
        lines = [f"🖥️ **Active Applications & Heavy Processes** ({len(apps)} found):\n"]
        for name, pid, mem in apps[:limit]:
            lines.append(f"• `{name}` (PID: `{pid}`) — `{mem} MB RAM`")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing running apps: {e}")
        return f"❌ Error listing apps: {e}"


def kill_process(target: str) -> str:
    """Terminate a process by name (e.g. 'chrome.exe') or PID (e.g. '1234')."""
    target = target.strip()
    if not target:
        return "Process target cannot be empty."

    # Check protected processes
    if target.lower() in PROTECTED_PROCESSES:
        return f"⛔ Cannot terminate critical operating system process `{target}`."

    terminated_count = 0
    try:
        # Check if target is a PID
        if target.isdigit():
            pid = int(target)
            proc = psutil.Process(pid)
            pname = proc.name()
            if pname.lower() in PROTECTED_PROCESSES:
                return f"⛔ Cannot terminate critical process `{pname}` (PID: {pid})."
            proc.terminate()
            return f"🛑 Successfully terminated process `{pname}` (PID: {pid})."

        # Otherwise match by process name
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if p.info['name'].lower() == target.lower() or p.info['name'].lower().startswith(target.lower()):
                    if p.info['name'].lower() in PROTECTED_PROCESSES:
                        continue
                    p.terminate()
                    terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if terminated_count > 0:
            return f"🛑 Successfully terminated {terminated_count} instance(s) of `{target}`."
        return f"⚠️ No running process found matching `{target}`."
    except Exception as e:
        logger.error(f"Error terminating process '{target}': {e}")
        return f"❌ Failed to terminate process: {e}"


def capture_screenshot(filename: str = "screenshot.png") -> str:
    """Capture a screenshot of the laptop desktop screen."""
    save_path = config.database_path.parent / filename
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        img.save(save_path, "PNG")
        return f"📸 Screenshot captured successfully ({img.width}x{img.height}) and saved to `{save_path}`."
    except Exception as e:
        # Fallback to PowerShell
        try:
            ps_cmd = (
                f"$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
                f"$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
                f"$g=[System.Drawing.Graphics]::FromImage($bmp);"
                f"$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
                f"$bmp.Save('{save_path}');"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=10)
            if save_path.exists():
                return f"📸 Screenshot captured via PowerShell and saved to `{save_path}`."
        except Exception:
            pass
        logger.warning(f"Screenshot capture failed: {e}")
        return f"⚠️ Screenshot could not be captured in the current session: {e}"

