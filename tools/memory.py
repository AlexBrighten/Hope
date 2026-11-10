"""Long-Term Memory Tools for Hope UltraLight:
Backed by SQLite for instant lookups, with automatic markdown export to workspace/memory.md.
"""

from typing import List, Dict
from database import db


async def remember(key: str, value: str, category: str = "general") -> str:
    """Save an enduring fact, preference, or rule to long-term memory."""
    db.remember(key=key, value=value, category=category)
    db.export_memory_to_markdown()
    return f"🧠 Remembered under [{category}]: **{key}** = {value}"


async def recall(query: str = "") -> str:
    """Retrieve facts and preferences from long-term memory."""
    memories = db.recall(query=query)
    if not memories:
        return "No matching memories found."

    lines = ["### 🧠 Recalled Memories:\n"]
    for m in memories:
        lines.append(f"- **[{m['category']}] {m['key']}**: {m['value']}")
    return "\n".join(lines)


def get_all_memories_text() -> str:
    """Helper for Telegram /mem command."""
    memories = db.recall()
    if not memories:
        return "🧠 Long-term memory is currently empty. Tell me facts to remember!"
    lines = ["🧠 **Long-Term Memory Notes**:\n"]
    for m in memories:
        lines.append(f"• `[{m['category']}]` **{m['key']}**: {m['value']}")
    return "\n".join(lines)

