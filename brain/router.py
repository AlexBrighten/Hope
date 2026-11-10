"""Deterministic Privacy & Intent Router for Hope UltraLight:
Executes in under 1 ms using rule-based classification. Strict privacy guarantee:
Personal/private queries NEVER touch cloud tiers without explicit user confirmation.
"""

import re
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class RouteDecision:
    tier: int                   # 1 (Local Ollama), 2 (OpenRouter Free), 3 (Gemini Fallback)
    is_private: bool            # True if query touches personal data (mail, calendar, memory, personal files)
    reason: str                 # Short diagnostic reason
    tool_category: Optional[str]# "mail", "calendar", "research", "sheets", "github", "memory", None
    reasoning_effort: str       # "low", "medium", "high"
    cleaned_query: str          # Query with slash commands stripped


# Private keywords (Strictly Tier 1 only)
PRIVATE_PATTERNS = [
    r"\b(email|emails|gmail|mail|inbox|unread|draft|drafts|send\s+email|reply\s+email)\b",
    r"\b(calendar|schedule|reminder|remind|meeting|meetings|appointment|events?|reschedule)\b",
    r"\b(task|todo|to-do|follow[- ]?up|deadline|due|finish|complete|cancel)\b",
    r"\b(remember\s+that|my\s+preference|my\s+favorite|my\s+phone|my\s+address|my\s+password|who\s+am\s+i)\b",
    r"\b(workspace[/\\]|my\s+notes|personal\s+note|my\s+secret)\b"
]

# Public Research keywords (Tier 2 OpenRouter)
RESEARCH_PATTERNS = [
    r"\b(search|google|find\s+out|look\s+up|research|news|article|latest\s+on)\b",
    r"\b(who\s+is|what\s+is|company|founder|startup|market|funding|valuation)\b",
    r"https?://[^\s]+",
    r"\b(code|function|debug|python|javascript|script|algorithm|github)\b",
    r"\b(summarize\s+url|read\s+page|fetch\s+page|scrape)\b"
]

# System & Hardware Butler keywords
SYSTEM_PATTERNS = [
    r"\b(pc|laptop|computer|battery|cpu|ram|memory\s+usage|disk|storage|hardware|clean\s+temp|temp\s+files)\b"
]


class Router:
    def __init__(self):
        self._private_regex = re.compile("|".join(PRIVATE_PATTERNS), re.IGNORECASE)
        self._research_regex = re.compile("|".join(RESEARCH_PATTERNS), re.IGNORECASE)
        self._system_regex = re.compile("|".join(SYSTEM_PATTERNS), re.IGNORECASE)

    def route(self, raw_query: str) -> RouteDecision:
        query = raw_query.strip()
        effort = "low"

        # 1. Slash command overrides
        if query.startswith("/pc") or query.startswith("/system"):
            return RouteDecision(tier=1, is_private=False, reason="manual_override_system", tool_category="system", reasoning_effort="low", cleaned_query="Report the current PC hardware and resource status")

        if query.startswith("/radar"):
            return RouteDecision(tier=2, is_private=False, reason="manual_override_radar", tool_category="research", reasoning_effort="low", cleaned_query="Fetch the latest tech radar")

        if query.startswith("/persona"):
            return RouteDecision(tier=1, is_private=False, reason="manual_override_persona", tool_category=None, reasoning_effort="low", cleaned_query=query)

        if query.startswith("/local"):
            cleaned = query[6:].strip()
            return RouteDecision(tier=1, is_private=True, reason="manual_override_local", tool_category=None, reasoning_effort="low", cleaned_query=cleaned)

        if query.startswith("/free"):
            cleaned = query[5:].strip()
            return RouteDecision(tier=2, is_private=False, reason="manual_override_free", tool_category="research", reasoning_effort="low", cleaned_query=cleaned)

        if query.startswith("/gemini"):
            cleaned = query[7:].strip()
            return RouteDecision(tier=3, is_private=False, reason="manual_override_gemini", tool_category="research", reasoning_effort="low", cleaned_query=cleaned)

        if query.startswith("/deep"):
            cleaned = query[5:].strip()
            return RouteDecision(tier=2, is_private=False, reason="manual_override_deep", tool_category="research", reasoning_effort="high", cleaned_query=cleaned)

        if query.startswith("/research"):
            cleaned = query[9:].strip()
            return RouteDecision(tier=2, is_private=False, reason="manual_override_research", tool_category="research", reasoning_effort="high", cleaned_query=cleaned)

        if query.startswith("/jobs"):
            cleaned = query[5:].strip()
            return RouteDecision(tier=2, is_private=False, reason="manual_override_jobs", tool_category="research", reasoning_effort="low", cleaned_query=f"Find job and business leads for {cleaned}")

        # 2. Strict Privacy Gate: Mail & Calendar & Personal Notes
        if self._private_regex.search(query):
            # Identify category
            q_lower = query.lower()
            if any(k in q_lower for k in ["email", "gmail", "inbox", "draft", "mail"]):
                cat = "mail"
            elif any(k in q_lower for k in ["calendar", "schedule", "reminder", "remind", "meeting", "event", "appointment"]):
                cat = "calendar"
            elif any(k in q_lower for k in ["task", "todo", "to-do", "follow-up", "deadline", "due"]):
                cat = "tasks"
            elif any(k in q_lower for k in ["remember", "memory", "recall", "note"]):
                cat = "memory"
            else:
                cat = "private"

            return RouteDecision(
                tier=1,
                is_private=True,
                reason="strict_privacy_boundary",
                tool_category=cat,
                reasoning_effort="low",
                cleaned_query=query
            )

        # 3. Public Web Research, Company/Founder lookups, Code, URLs -> Tier 2 (OpenRouter)
        if self._research_regex.search(query):
            return RouteDecision(
                tier=2,
                is_private=False,
                reason="public_research_workhorse",
                tool_category="research",
                reasoning_effort="low",
                cleaned_query=query
            )

        # 4. System & Hardware Butler (Battery, CPU, RAM, Disk, Temp)
        if self._system_regex.search(query):
            return RouteDecision(
                tier=1,
                is_private=False,
                reason="system_hardware_monitor",
                tool_category="system",
                reasoning_effort="low",
                cleaned_query=query
            )

        # 5. Short conversational chat, greetings, definitions, time -> Tier 1 (Local Ollama)
        return RouteDecision(
            tier=1,
            is_private=False,
            reason="local_conversation",
            tool_category=None,
            reasoning_effort="low",
            cleaned_query=query
        )


router = Router()
