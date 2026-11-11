"""Filesystem Explorer & Workspace Operations Tool for Hope UltraLight:
Empowers the agent to list folders, inspect files, create documents, and search the laptop filesystem.
"""

import os
import sys
import fnmatch
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def list_dir(path: str = ".") -> str:
    """List files and folders in a directory with size and modification date."""
    try:
        target = Path(path).resolve()
        if not target.exists():
            return f"❌ Path does not exist: `{path}`"
        if not target.is_dir():
            return f"❌ Path is not a directory: `{path}`"

        items = list(target.iterdir())
        if not items:
            return f"📂 Directory `{target}` is empty."

        dirs = [i for i in items if i.is_dir()]
        files = [i for i in items if i.is_file()]

        lines = [f"📂 **Contents of** `{target}` ({len(dirs)} folders, {len(files)} files):\n"]

        # List folders first
        for d in sorted(dirs, key=lambda x: x.name.lower())[:30]:
            lines.append(f"📁 `{d.name}/`")

        # List files
        for f in sorted(files, key=lambda x: x.name.lower())[:50]:
            try:
                sz = f.stat().st_size
                if sz < 1024:
                    sz_str = f"{sz} B"
                elif sz < 1024 ** 2:
                    sz_str = f"{round(sz / 1024, 1)} KB"
                else:
                    sz_str = f"{round(sz / (1024 ** 2), 1)} MB"
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                lines.append(f"📄 `{f.name}` ({sz_str}, {mtime})")
            except Exception:
                lines.append(f"📄 `{f.name}`")

        if len(items) > 80:
            lines.append(f"\n_... and {len(items) - 80} more items._")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing directory '{path}': {e}")
        return f"❌ Error listing directory: {e}"


def read_file(path: str, max_lines: int = 150) -> str:
    """Read the content of a local file (code, text, config, markdown, json)."""
    try:
        target = Path(path).resolve()
        if not target.exists():
            return f"❌ File does not exist: `{path}`"
        if not target.is_file():
            return f"❌ Target is not a file: `{path}`"

        # Check file size (prevent loading giant binary files)
        if target.stat().st_size > 2 * 1024 * 1024:
            return f"⚠️ File is too large to read into chat (>2 MB): `{path}`"

        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = target.read_text(encoding="latin-1", errors="replace")

        lines = content.splitlines()
        truncated = len(lines) > max_lines
        display_lines = lines[:max_lines]

        ext = target.suffix.lstrip(".").lower() or "text"
        formatted_content = "\n".join(display_lines)

        output = [
            f"📄 **File**: `{target.name}` ({len(lines)} lines)",
            f"```{ext}",
            formatted_content,
            "```"
        ]
        if truncated:
            output.append(f"\n_[Showing {max_lines} of {len(lines)} lines. Total length: {len(content)} chars]_")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error reading file '{path}': {e}")
        return f"❌ Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Create or overwrite a file with specified content."""
    try:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        size_kb = round(len(content.encode("utf-8")) / 1024, 2)
        return f"✅ Successfully wrote `{target.name}` ({size_kb} KB) at `{target}`."
    except Exception as e:
        logger.error(f"Error writing to file '{path}': {e}")
        return f"❌ Failed to write file: {e}"


def search_files(query: str, root_dir: str = ".") -> str:
    """Search for files matching a wildcard or keyword (e.g. '*.py', 'test*', 'report')."""
    try:
        root = Path(root_dir).resolve()
        if not root.exists():
            return f"❌ Directory does not exist: `{root_dir}`"

        matches = []
        pattern = f"*{query}*" if not any(c in query for c in "*?[]") else query

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip common giant / virtual environment folders
            dirnames[:] = [d for d in dirnames if d not in (".git", "venv", ".venv", "__pycache__", "node_modules")]
            for f in filenames:
                if fnmatch.fnmatch(f.lower(), pattern.lower()):
                    full_p = Path(dirpath) / f
                    matches.append(full_p)
                    if len(matches) >= 25:
                        break
            if len(matches) >= 25:
                break

        if not matches:
            return f"🔍 No files found matching pattern `{query}` in `{root}`."

        lines = [f"🔍 **Search Results for** `{query}` ({len(matches)} found):\n"]
        for m in matches:
            try:
                rel = m.relative_to(root)
            except Exception:
                rel = m
            lines.append(f"• `{rel}`")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error searching files for '{query}': {e}")
        return f"❌ File search error: {e}"

