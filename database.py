"""SQLite database manager for Hope UltraLight:
Handles usage quotas, response caching, memory notes, and pending human approvals.
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from config import config

DB_INIT_SQL = """
-- 1. Daily usage counters per provider
CREATE TABLE IF NOT EXISTS usage_counters (
    date TEXT NOT NULL,
    provider TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    PRIMARY KEY (date, provider)
);

-- 2. Response cache for repetitive public research
CREATE TABLE IF NOT EXISTS response_cache (
    cache_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    response_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Staged human approval actions
CREATE TABLE IF NOT EXISTS pending_actions (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- 4. Long-term memory notes
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT DEFAULT 'general',
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Local conversation history
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_chat
ON conversation_messages (chat_id, id);
"""


class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.database_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.executescript(DB_INIT_SQL)

    # --------------------------------------------------------------------------
    # Usage Tracking & Quota Checks
    # --------------------------------------------------------------------------
    def get_today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def record_usage(self, provider: str, prompt_tokens: int = 0, completion_tokens: int = 0):
        today = self.get_today_str()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO usage_counters (date, provider, request_count, prompt_tokens, completion_tokens)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(date, provider) DO UPDATE SET
                    request_count = request_count + 1,
                    prompt_tokens = prompt_tokens + excluded.prompt_tokens,
                    completion_tokens = completion_tokens + excluded.completion_tokens
                """,
                (today, provider, prompt_tokens, completion_tokens)
            )

    def get_provider_usage_today(self, provider: str) -> Dict[str, int]:
        today = self.get_today_str()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT request_count, prompt_tokens, completion_tokens FROM usage_counters WHERE date = ? AND provider = ?",
                (today, provider)
            ).fetchone()
            if row:
                return {
                    "request_count": row["request_count"],
                    "prompt_tokens": row["prompt_tokens"],
                    "completion_tokens": row["completion_tokens"]
                }
            return {"request_count": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def is_quota_exceeded(self, provider: str) -> bool:
        usage = self.get_provider_usage_today(provider)
        count = usage["request_count"]
        if provider == "openrouter" and config.daily_openrouter_limit > 0:
            return count >= config.daily_openrouter_limit
        if provider == "gemini" and config.daily_gemini_limit > 0:
            return count >= config.daily_gemini_limit
        return False

    # --------------------------------------------------------------------------
    # Response Caching (Research queries)
    # --------------------------------------------------------------------------
    def get_cached_response(self, cache_key: str, max_age_hours: int = 4) -> Optional[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT response_text FROM response_cache WHERE cache_key = ? AND created_at >= ?",
                (cache_key, cutoff.isoformat())
            ).fetchone()
            if row:
                return row["response_text"]
        return None

    def set_cached_response(self, cache_key: str, provider: str, response_text: str):
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO response_cache (cache_key, provider, response_text, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (cache_key, provider, response_text, now_iso)
            )

    # --------------------------------------------------------------------------
    # Pending Human Approvals (Mutating operations)
    # --------------------------------------------------------------------------
    def stage_action(self, action_id: str, action_type: str, payload: Dict[str, Any], expiry_minutes: int = 30):
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO pending_actions (id, action_type, payload_json, status, expires_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (action_id, action_type, json.dumps(payload), expires_at.isoformat())
            )

    def get_pending_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id, action_type, payload_json, status, expires_at FROM pending_actions WHERE id = ?",
                (action_id,)
            ).fetchone()
            if row:
                now_iso = datetime.now(timezone.utc).isoformat()
                is_expired = row["expires_at"] < now_iso
                status = "expired" if (row["status"] == "pending" and is_expired) else row["status"]
                return {
                    "id": row["id"],
                    "action_type": row["action_type"],
                    "payload": json.loads(row["payload_json"]),
                    "status": status,
                    "is_expired": is_expired
                }
        return None

    def resolve_action(self, action_id: str, new_status: str) -> bool:
        """Mark action as 'approved', 'rejected', or 'executed'."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE pending_actions SET status = ? WHERE id = ? AND status = 'pending'",
                (new_status, action_id)
            )
            return cur.rowcount > 0

    # --------------------------------------------------------------------------
    # Long-term Memory
    # --------------------------------------------------------------------------
    def remember(self, key: str, value: str, category: str = "general"):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (category, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    category = excluded.category,
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (category, key.strip(), value.strip())
            )

    def recall(self, query: str = "") -> List[Dict[str, str]]:
        with self._get_connection() as conn:
            if query:
                rows = conn.execute(
                    "SELECT category, key, value FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY updated_at DESC",
                    (f"%{query}%", f"%{query}%")
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT category, key, value FROM memories ORDER BY updated_at DESC LIMIT 50"
                ).fetchall()
            return [{"category": r["category"], "key": r["key"], "value": r["value"]} for r in rows]

    def export_memory_to_markdown(self, markdown_path=None):
        md_file = markdown_path or (config.database_path.parent / "memory.md")
        memories = self.recall()
        lines = ["# 🧠 Hope Long-Term Memory Notes", "", f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_", ""]
        if not memories:
            lines.append("No saved memories yet.")
        else:
            current_cat = None
            for mem in sorted(memories, key=lambda x: x["category"]):
                if mem["category"] != current_cat:
                    current_cat = mem["category"]
                    lines.append(f"\n## {current_cat.capitalize()}")
                lines.append(f"- **{mem['key']}**: {mem['value']}")
        md_file.write_text("\n".join(lines), encoding="utf-8")

    # --------------------------------------------------------------------------
    # Conversation Context
    # --------------------------------------------------------------------------
    def add_conversation_message(self, chat_id: str, role: str, content: str):
        if not content.strip():
            return
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversation_messages (chat_id, role, content)
                VALUES (?, ?, ?)
                """,
                (chat_id, role, content.strip())
            )

    def get_conversation_messages(self, chat_id: str, limit: int = 12) -> List[Dict[str, str]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM conversation_messages
                WHERE chat_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (chat_id, limit)
            ).fetchall()
        return [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]


# Global singleton instance
db = DatabaseManager()
