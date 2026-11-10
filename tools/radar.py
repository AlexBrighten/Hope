"""Live Autonomous Tech & Market Radar for Hope UltraLight:
Scrapes real-time trending engineering stories from Hacker News and GitHub to deliver
proactive intelligence on what matters right now.
"""

import logging
import asyncio
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def fetch_hn_top_stories(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch the top active stories from official Hacker News Firebase API."""
    stories = []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            if resp.status_code != 200:
                return []
            story_ids = resp.json()[:limit]

            # Fetch individual story details in parallel
            tasks = [
                client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                for sid in story_ids
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for r in responses:
                if isinstance(r, httpx.Response) and r.status_code == 200:
                    data = r.json()
                    if data and data.get("type") == "story":
                        stories.append({
                            "title": data.get("title", "Untitled"),
                            "url": data.get("url", f"https://news.ycombinator.com/item?id={data.get('id')}"),
                            "score": data.get("score", 0),
                            "comments": data.get("descendants", 0),
                            "by": data.get("by", "anonymous"),
                            "hn_url": f"https://news.ycombinator.com/item?id={data.get('id')}"
                        })
    except Exception as e:
        logger.error(f"Error fetching Hacker News top stories: {e}")

    return stories


async def fetch_github_trending_topics(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch trending repositories from GitHub Search API (heavily starred recently)."""
    repos = []
    try:
        # Search for popular repositories created or active recently
        url = "https://api.github.com/search/repositories?q=stars:>100+pushed:>2026-01-01&sort=stars&order=desc&per_page=5"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Hope-UltraLight-Agent"
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items[:limit]:
                    repos.append({
                        "name": item.get("full_name", ""),
                        "description": item.get("description", "No description"),
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language", "Code"),
                        "url": item.get("html_url", "")
                    })
    except Exception as e:
        logger.error(f"Error fetching GitHub trends: {e}")

    return repos


async def get_tech_radar_summary() -> str:
    """Compile a structured live Tech Radar report."""
    hn_stories, gh_repos = await asyncio.gather(
        fetch_hn_top_stories(limit=5),
        fetch_github_trending_topics(limit=4),
        return_exceptions=True
    )

    lines = ["📡 **Live Tech & Innovation Radar**\n"]

    if isinstance(hn_stories, list) and hn_stories:
        lines.append("🔥 **Top Hacker News Discussions**:")
        for idx, s in enumerate(hn_stories, 1):
            lines.append(
                f"{idx}. [{s['title']}]({s['url']})  \n"
                f"   *(🔺 {s['score']} pts | 💬 {s['comments']} comments | [HN Thread]({s['hn_url']}))*"
            )
        lines.append("")
    else:
        lines.append("⚠️ Could not load Hacker News trends right now.\n")

    if isinstance(gh_repos, list) and gh_repos:
        lines.append("⭐ **Trending GitHub Projects**:")
        for r in gh_repos:
            desc = r['description'][:100] + ("..." if len(r['description'] or "") > 100 else "")
            lines.append(f"• [{r['name']}]({r['url']}) (`{r['language']}`, ⭐ {r['stars']:,})\n  _{desc}_")
    else:
        lines.append("⚠️ Could not load GitHub trends right now.")

    return "\n".join(lines)

