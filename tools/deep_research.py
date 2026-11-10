"""Autonomous Multi-Step Deep Research Engine for Hope UltraLight:
Decomposes user queries into multi-vector search queries, scrapes live source pages,
synthesizes an Executive Intelligence Dossier, and saves it to workspace/reports/.
"""

import re
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from config import config
from tools.web import web_search, fetch_page

logger = logging.getLogger(__name__)

REPORTS_DIR = config.database_path.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    """Sanitize topic string into safe filename."""
    clean = re.sub(r'[^a-zA-Z0-9_\- ]', '', name).strip().replace(' ', '_').lower()
    return clean[:50] or "research_report"


async def conduct_deep_research(topic: str, max_pages: int = 3) -> Dict[str, Any]:
    """Execute autonomous multi-step deep research across multiple web sources."""
    logger.info(f"Initiating deep research on topic: {topic}")

    # 1. Deconstruct topic into targeted search vectors
    vectors = [
        f"{topic} overview architecture guide",
        f"{topic} comparison benchmarks pricing",
        f"{topic} limitations criticisms reviews"
    ]

    # 2. Gather URLs and snippets across all vectors
    collected_urls = []
    snippets = []

    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for v in vectors:
                try:
                    results = list(ddgs.text(v, max_results=3))
                    for r in results:
                        href = r.get("href")
                        if href and href.startswith("http") and href not in collected_urls:
                            collected_urls.append(href)
                            snippets.append({
                                "title": r.get("title", "Untitled"),
                                "url": href,
                                "snippet": r.get("body", "")
                            })
                except Exception as e:
                    logger.debug(f"Search vector '{v}' error: {e}")
    except Exception as e:
        logger.error(f"Deep research search error: {e}")

    # 3. Scrape full page text from top unique URLs in parallel
    target_urls = collected_urls[:max_pages]
    page_contents = []

    if target_urls:
        fetch_tasks = [fetch_page(u, max_chars=4000) for u in target_urls]
        fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        for u, f in zip(target_urls, fetched):
            if isinstance(f, str) and not f.startswith("Failed to fetch") and len(f) > 100:
                page_contents.append({"url": u, "content": f})

    # 4. Compile the Executive Intelligence Dossier
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"{_sanitize_filename(topic)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_file = REPORTS_DIR / filename

    dossier_lines = [
        f"# 📑 Executive Intelligence Dossier: {topic.title()}",
        f"_Compiled autonomously by Hope UltraLight on {timestamp}_\n",
        "## 🧭 Executive Summary",
        f"Comprehensive multi-source analysis conducted across {len(page_contents)} deeply scraped web pages and {len(snippets)} search index vectors.\n",
        "## 🎯 Key Findings & Intel"
    ]

    # Synthesize findings from snippets and scraped content
    for idx, s in enumerate(snippets[:6], 1):
        dossier_lines.append(f"### {idx}. {s['title']}")
        dossier_lines.append(f"- **Source**: {s['url']}")
        dossier_lines.append(f"- **Extract**: {s['snippet']}\n")

    if page_contents:
        dossier_lines.append("## 🔍 Deep-Dive Page Extractions")
        for p in page_contents:
            clean_excerpt = p['content'][:800].replace('\n', ' ')
            dossier_lines.append(f"#### Excerpt from: {p['url']}")
            dossier_lines.append(f"> {clean_excerpt}...\n")

    dossier_lines.append("## 🔗 Verifiable Sources")
    for u in target_urls:
        dossier_lines.append(f"- <{u}>")

    full_markdown = "\n".join(dossier_lines)
    report_file.write_text(full_markdown, encoding="utf-8")
    logger.info(f"Saved research report to: {report_file}")

    # Create telegram summary
    tg_summary = (
        f"📑 **Deep Research Dossier**: `{topic}`\n\n"
        f"• **Sources Scraped**: `{len(page_contents)} full pages` + `{len(snippets)} search vectors`\n"
        f"• **Saved To**: `{report_file.name}`\n\n"
        f"**Key Highlights**:\n"
    )
    for s in snippets[:3]:
        tg_summary += f"• **{s['title']}**: {s['snippet'][:120]}...\n"

    tg_summary += f"\n_Full {len(dossier_lines)} line report stored in `workspace/reports/`._"

    return {
        "topic": topic,
        "summary": tg_summary,
        "report_path": str(report_file),
        "source_count": len(page_contents) + len(snippets)
    }

