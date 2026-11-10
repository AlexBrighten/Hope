"""Human-in-the-Loop Approval Gate for Hope UltraLight:
Stages mutating actions in SQLite and provides Telegram inline keyboards for 1-click approvals.
"""

import uuid
import logging
from typing import Dict, Any, Callable, Awaitable
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import config

logger = logging.getLogger(__name__)

# Registry of executable tool functions by name
ACTION_REGISTRY: Dict[str, Callable[..., Awaitable[Any]]] = {}


def register_approvable_action(name: str, handler: Callable[..., Awaitable[Any]]):
    """Register an action handler that can be executed upon user approval."""
    ACTION_REGISTRY[name] = handler


def stage_action(action_type: str, payload: Dict[str, Any], description: str) -> Dict[str, Any]:
    """Stage a mutating action in SQLite and create Telegram inline buttons."""
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    db.stage_action(
        action_id=action_id,
        action_type=action_type,
        payload=payload,
        expiry_minutes=config.approval_expiry_minutes
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Execute", callback_data=f"appr:{action_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rejc:{action_id}")
        ]
    ])

    return {
        "action_id": action_id,
        "action_type": action_type,
        "description": description,
        "reply_markup": keyboard
    }


async def execute_approved_action(action_id: str) -> str:
    """Validate and execute a staged action upon user tapping Approve."""
    record = db.get_pending_action(action_id)
    if not record:
        return "❌ Error: Action not found or was purged."

    if record.get("is_expired"):
        db.resolve_action(action_id, "expired")
        return "⏱️ Action expired (exceeded 30-minute approval window)."

    if record["status"] != "pending":
        return f"⚠️ Action already {record['status']}."

    action_type = record["action_type"]
    handler = ACTION_REGISTRY.get(action_type)
    if not handler:
        return f"❌ Error: No handler registered for action type '{action_type}'."

    try:
        # Mark as executing/approved
        db.resolve_action(action_id, "executed")
        result = await handler(**record["payload"])
        return f"✅ **Executed Successfully**:\n{result}"
    except Exception as e:
        logger.error(f"Failed to execute approved action {action_id}: {e}")
        return f"❌ Execution failed: {e}"


def reject_action(action_id: str) -> str:
    """Cancel a staged action upon user tapping Reject."""
    success = db.resolve_action(action_id, "rejected")
    if success:
        return "❌ Action cancelled by user."
    return "⚠️ Action was not in a pending state."

