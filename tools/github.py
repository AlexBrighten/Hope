"""GitHub REST API Client for Hope UltraLight:
Read-first integration for inspecting issues and reading repository files.
"""

import base64
import logging
from typing import Optional
import httpx
from config import config

logger = logging.getLogger(__name__)


def _get_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "HopeUltraLightAgent/2.0"
    }
    if config.github_token:
        headers["Authorization"] = f"token {config.github_token}"
    return headers


async def gh_issues(repo: str, state: str = "open", limit: int = 5) -> str:
    """List issues or PRs for a repository (format: 'owner/repo')."""
    if not config.github_token:
        return "⚠️ GITHUB_TOKEN is not configured in .env."

    url = f"https://api.github.com/repos/{repo}/issues?state={state}&per_page={limit}"
    try:
        async with httpx.AsyncClient(headers=_get_headers(), timeout=10.0) as client:
            res = await client.get(url)
            res.raise_for_status()
            issues = res.json()

        if not issues:
            return f"No {state} issues found in `{repo}`."

        output = [f"### 🐙 GitHub Issues in `{repo}` ({len(issues)}):\n"]
        for issue in issues:
            is_pr = "pull_request" in issue
            kind = "PR" if is_pr else "Issue"
            output.append(
                f"- **#{issue['number']}** [{kind}]: [{issue['title']}]({issue['html_url']})\n"
                f"  Author: @{issue.get('user', {}).get('login', 'unknown')} | State: {issue['state']}"
            )
        return "\n".join(output)
    except Exception as e:
        logger.error(f"GitHub issues error for {repo}: {e}")
        return f"Failed to fetch GitHub issues for {repo}: {e}"


async def gh_read_file(repo: str, file_path: str, branch: str = "") -> str:
    """Read a text file from a GitHub repository (format: 'owner/repo', file_path='README.md')."""
    if not config.github_token:
        return "⚠️ GITHUB_TOKEN is not configured in .env."

    ref_param = f"?ref={branch}" if branch else ""
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}{ref_param}"
    try:
        async with httpx.AsyncClient(headers=_get_headers(), timeout=10.0) as client:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()

        content_b64 = data.get("content", "")
        content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        return f"### 🐙 `{file_path}` in `{repo}`:\n\n```\n{content[:5000]}\n```"
    except Exception as e:
        logger.error(f"GitHub read file error: {e}")
        return f"Failed to read `{file_path}` from {repo}: {e}"

