"""Terminal & Shell Command Execution Tool for Hope UltraLight:
Empowers the agent to execute PowerShell/Bash commands, compile code, inspect git status,
and run local scripts autonomously, with human-in-the-loop safeguards on destructive operations.
"""

import os
import sys
import re
import asyncio
import logging
import subprocess
from typing import Dict, Any, Union
from config import config
from tools.approval import stage_action, register_approvable_action

logger = logging.getLogger(__name__)

# Patterns that require explicit user approval before execution
DESTRUCTIVE_PATTERNS = [
    r"\b(format|diskpart|mkfs)\b",
    r"\b(shutdown|reboot|Stop-Computer|Restart-Computer)\b",
    r"\b(rmdir\s+/[sq]|del\s+/[sqf]|Remove-Item\s+.*-Recurse\s+.*-Force)\b",
    r"\b(rm\s+-rf\s+[/~])\b",
    r"\b(drop\s+database|truncate\s+table)\b",
]

_destructive_regex = re.compile("|".join(DESTRUCTIVE_PATTERNS), re.IGNORECASE)


async def _actual_run_command(command: str, timeout: int = 30) -> str:
    """Internal helper that executes a shell command on the host OS."""
    try:
        is_windows = sys.platform == "win32"
        shell_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command] if is_windows else ["/bin/bash", "-c", command]

        proc = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(timeout))
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return f"⏱️ Command timed out after {timeout} seconds: `{command}`"

        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()
        exit_code = proc.returncode

        lines = [f"💻 **Command**: `{command}`", f"**Exit Code**: `{exit_code}`"]
        if out_text:
            # Truncate if exceedingly long
            if len(out_text) > 3000:
                out_text = out_text[:3000] + f"\n\n[... Truncated, total length: {len(out_text)} characters]"
            lines.append(f"\n**Output**:\n```text\n{out_text}\n```")
        if err_text:
            if len(err_text) > 1500:
                err_text = err_text[:1500] + "\n[... Truncated]"
            lines.append(f"\n**Error / Stderr**:\n```text\n{err_text}\n```")
        if not out_text and not err_text:
            lines.append("\n_(Command executed with no output)_")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}")
        return f"❌ Command execution error: {e}"


# Register approvable action for dangerous commands
register_approvable_action("shell_command", _actual_run_command)


async def run_command(command: str, timeout: int = 30) -> Union[str, Dict[str, Any]]:
    """Execute a shell or PowerShell command on the host laptop.
    
    Non-destructive commands (git, dir, python, inspect, build, ping, test) execute immediately.
    Potentially destructive commands (format, shutdown, recursive delete) stage for 1-click approval.
    """
    cmd_clean = command.strip()
    if not cmd_clean:
        return "Command cannot be empty."

    # Check for destructive patterns
    if _destructive_regex.search(cmd_clean):
        desc = (
            f"⚠️ **Authorization Required: Potentially Destructive Shell Command**\n\n"
            f"```powershell\n{cmd_clean}\n```\n"
            f"_This command requires explicit owner authorization before execution._"
        )
        return stage_action("shell_command", {"command": cmd_clean, "timeout": timeout}, desc)

    # Execute directly (Unleashed mode!)
    return await _actual_run_command(cmd_clean, timeout=timeout)


async def launch_app(target: str) -> str:
    """Launch an application, document, folder, or executable on the laptop desktop."""
    try:
        t = target.strip()
        if sys.platform == "win32":
            # Use os.startfile on Windows for seamless launch
            os.startfile(t)
        else:
            subprocess.Popen(["xdg-open", t])
        return f"🚀 Launched `{t}` on desktop successfully."
    except Exception as e:
        logger.error(f"Failed to launch app '{target}': {e}")
        return f"❌ Could not launch '{target}': {e}"
