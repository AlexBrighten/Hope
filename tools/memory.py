"""Long-Term Memory Tools for Hope UltraLight:
Backed by SQLite for instant lookups, with automatic markdown export to workspace/memory.md.
"""

from typing import List, Dict
from database import db


async def create_task(
    title: str,
    description: str = "",
    due_at: str = "",
    priority: str = "medium",
) -> str:
    """Create a persistent task, optionally due at an ISO-8601 datetime."""
    task_id = db.create_task(title, description, due_at or None, priority)
    due_text = f" due {due_at}" if due_at else ""
    return f"✅ Task created{due_text}: **{title}** (ID: `{task_id}`)"


async def list_tasks(status: str = "pending", limit: int = 20) -> str:
    """List persistent tasks by status."""
    tasks = db.list_tasks(status=status, limit=limit)
    if not tasks:
        return f"✅ No {status} tasks found."
    lines = [f"### Tasks ({status})"]
    for task in tasks:
        due = f" — due `{task['due_at']}`" if task["due_at"] else ""
        lines.append(f"- **{task['title']}** [{task['priority']}] {due} (ID: `{task['id']}`)")
    return "\n".join(lines)


async def complete_task(task_id: str) -> str:
    """Mark a persistent task complete."""
    if not db.update_task_status(task_id, "completed"):
        return f"⚠️ Task `{task_id}` was not found or is already closed."
    return f"✅ Completed task `{task_id}`."


async def cancel_task(task_id: str) -> str:
    """Cancel a persistent task."""
    if not db.update_task_status(task_id, "cancelled"):
        return f"⚠️ Task `{task_id}` was not found or is already closed."
    return f"✅ Cancelled task `{task_id}`."


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
