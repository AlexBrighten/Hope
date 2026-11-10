"""Configuration loader and system environment manager for Hope UltraLight."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Load .env file
load_dotenv(BASE_DIR / ".env")


@dataclass
class Config:
    # Telegram settings
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    allowed_user_id: int = int(os.getenv("ALLOWED_TELEGRAM_USER_ID", "0"))

    # Database
    database_path: Path = BASE_DIR / os.getenv("DATABASE_PATH", "workspace/hope.db")

    # Tier 1: Local Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
    ollama_deep_model: str = os.getenv("OLLAMA_DEEP_MODEL", "qwen2.5:7b-instruct-q4_K_M")
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    ollama_timeout: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60.0"))

    # Tier 2: OpenRouter (Inkling 2 Small)
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "thinkingmachines/inkling-2-small:free")
    daily_openrouter_limit: int = int(os.getenv("DAILY_OPENROUTER_LIMIT", "200"))

    # Tier 3: Gemini Fallback
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    daily_gemini_limit: int = int(os.getenv("DAILY_GEMINI_LIMIT", "50"))

    # Integrations
    github_token: str = os.getenv("GITHUB_TOKEN", "").strip()
    github_allowed_repos: str = os.getenv("GITHUB_ALLOWED_REPOS", "").strip()
    google_credentials_file: Path = BASE_DIR / os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    google_token_file: Path = BASE_DIR / os.getenv("GOOGLE_TOKEN_FILE", "token.json")

    # SMTP Settings (Standard instant email alternative to Google OAuth)
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_email: str = os.getenv("SMTP_EMAIL", os.getenv("GMAIL_ADDRESS", "")).strip()
    smtp_password: str = os.getenv("SMTP_PASSWORD", os.getenv("GMAIL_APP_PASSWORD", "")).strip()
    allow_cloud_fallback: bool = os.getenv("ALLOW_CLOUD_FALLBACK", "false").lower() in ("true", "1", "yes")

    # Security & Safeguards
    require_approval: bool = os.getenv("REQUIRE_APPROVAL", "true").lower() in ("true", "1", "yes")
    approval_expiry_minutes: int = int(os.getenv("APPROVAL_EXPIRY_MINUTES", "30"))
    response_cache_hours: int = int(os.getenv("RESPONSE_CACHE_HOURS", "4"))
    timezone: str = os.getenv("TIMEZONE", "UTC")
    autonomous_research_queries: tuple[str, ...] = tuple(
        query.strip() for query in os.getenv("AUTONOMOUS_RESEARCH_QUERIES", "").split("|") if query.strip()
    )
    autonomous_research_interval_hours: int = int(os.getenv("AUTONOMOUS_RESEARCH_INTERVAL_HOURS", "6"))

    # Persona & Title Settings
    agent_persona: str = os.getenv("AGENT_PERSONA", "jarvis").strip().lower()
    user_title: str = os.getenv("USER_TITLE", "Sir").strip()

    def is_telegram_ready(self) -> bool:
        return bool(self.telegram_bot_token and self.allowed_user_id)

    def is_tier1_ready(self) -> bool:
        return bool(self.ollama_base_url)

    def is_tier2_ready(self) -> bool:
        return bool(self.openrouter_api_key)

    def is_tier3_ready(self) -> bool:
        return bool(self.gemini_api_key)

    def is_smtp_ready(self) -> bool:
        return bool(self.smtp_email and self.smtp_password)


# Global singleton instance
config = Config()
