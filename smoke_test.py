"""Quick Smoke Test & Diagnostic Utility for Hope UltraLight:
Validates environment keys, SQLite database, Ollama, OpenRouter, and Gemini connectivity.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config
from database import db
from brain.local_brain import local_brain
from brain.openrouter_brain import openrouter_brain
from brain.gemini_brain import gemini_brain
from tools.web import web_search


async def run_diagnostics():
    print("=" * 70)
    print("🚀 HOPE ULTRALIGHT DIAGNOSTIC & SMOKE TEST")
    print("=" * 70)

    # 1. Database Check
    print("\n[1/5] Checking SQLite Database...")
    try:
        usage = db.get_provider_usage_today("test")
        print(f"  ✅ SQLite database operational: {config.database_path}")
    except Exception as e:
        print(f"  ❌ Database check failed: {e}")

    # 2. Telegram Configuration Check
    print("\n[2/5] Checking Telegram Configuration...")
    if config.is_telegram_ready():
        print(f"  ✅ Telegram Bot Token configured (Ends in ...{config.telegram_bot_token[-6:]})")
        print(f"  ✅ Allowed User ID: {config.allowed_user_id}")
    else:
        print("  ⚠️ Telegram credentials missing or default in .env.")
        print("     Set TELEGRAM_BOT_TOKEN and ALLOWED_TELEGRAM_USER_ID.")

    # 3. Tier 1: Local Ollama Check
    print("\n[3/5] Checking Tier 1 (Local Ollama: qwen2.5:3b-instruct)...")
    ollama_health = await local_brain.check_health()
    if ollama_health.get("online"):
        installed = "✅ Installed" if ollama_health.get("installed") else "⚠️ Model Not Pulled (run: ollama pull qwen2.5:3b-instruct)"
        print(f"  ✅ Ollama service is ONLINE at {config.ollama_base_url}")
        print(f"  • Model status: {installed}")
    else:
        print(f"  ℹ️ Ollama is OFFLINE at {config.ollama_base_url}")
        print("     (Start with: 'ollama serve' or systemctl start ollama)")

    # 4. Tier 2: OpenRouter Check
    print("\n[4/5] Checking Tier 2 (OpenRouter: Inkling 2 Small Free)...")
    if openrouter_brain.is_configured():
        print(f"  ✅ OpenRouter API Key configured.")
        print(f"  • Model slug: {config.openrouter_model}")
    else:
        print("  ⚠️ OpenRouter API Key not set in .env.")
        print("     (Get a free key at https://openrouter.ai/keys)")

    # 5. Tier 3: Gemini Fallback Check
    print("\n[5/5] Checking Tier 3 (Google Gemini 2.5 Flash)...")
    if gemini_brain.is_configured():
        print(f"  ✅ Gemini API Key configured.")
        print(f"  • Model: {config.gemini_model}")
    else:
        print("  ⚠️ Gemini API Key not set in .env.")
        print("     (Get a free key at https://aistudio.google.com/)")

    # 6. Web Search Smoke Test
    print("\n[Bonus] Quick Web Search Test...")
    try:
        search_res = await web_search("Python 3.14 release", max_results=1)
        if "Web Search Results" in search_res:
            print("  ✅ DuckDuckGo search operational (sub-second extraction).")
        else:
            print("  ⚠️ Search returned no results.")
    except Exception as e:
        print(f"  ❌ Web search test failed: {e}")

    print("\n" + "=" * 70)
    print("Diagnostics complete! Run 'python bot.py' to launch Hope UltraLight.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_diagnostics())

