"""Provider Chain Orchestrator for Hope UltraLight:
Coordinates Tier 1 (Ollama), Tier 2 (OpenRouter Inkling 2 Small), and Tier 3 (Gemini 2.5 Flash).
Enforces privacy guarantees, failover on 429/5xx/timeout, daily quota tracking, and response caching.
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from database import db
from config import config
from brain.local_brain import local_brain
from brain.openrouter_brain import openrouter_brain
from brain.gemini_brain import gemini_brain

logger = logging.getLogger(__name__)


class ProviderManager:
    def __init__(self):
        self.local = local_brain
        self.openrouter = openrouter_brain
        self.gemini = gemini_brain

    def _generate_cache_key(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> str:
        serialized = f"system:{system_prompt or ''}" + "".join(
            f"{m.get('role')}:{m.get('content', '')}" for m in messages
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tier: int = 1,
        is_private: bool = False,
        effort: str = "low",
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute chat turn through the appropriate provider with caching and failover."""
        # 1. Check response cache for public non-tool queries
        if not is_private and not tools:
            cache_key = self._generate_cache_key(messages, system_prompt)
            cached = db.get_cached_response(cache_key, max_age_hours=config.response_cache_hours)
            if cached:
                logger.info(f"Response cache hit for key {cache_key[:8]}")
                return {
                    "provider": "cache",
                    "model": "cached_response",
                    "content": cached,
                    "tool_calls": [],
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                }

        # 2. Strict Privacy Route (Tier 1 Local Only)
        if is_private or tier == 1:
            try:
                res = await self.local.chat(
                    messages=messages,
                    tools=tools,
                    use_deep_model=(effort == "high"),
                    system_prompt=system_prompt
                )
                db.record_usage("ollama", res.get("prompt_tokens", 0), res.get("completion_tokens", 0))
                return res
            except Exception as e:
                logger.error(f"Local brain error on private query: {e}")
                if is_private:
                    return {
                        "provider": "privacy_guard",
                        "model": "none",
                        "content": (
                            "⚠️ **Privacy Guard**: The local Ollama model is currently unreachable or timed out.\n\n"
                            "Because this request involves your private data (email, calendar, or notes), "
                            "it **cannot be forwarded to cloud AI** without your explicit confirmation.\n\n"
                            "• Ensure Ollama is running (`ollama serve`).\n"
                            "• Or retry by typing `/gemini <your query>` if you grant permission to use cloud AI."
                        ),
                        "tool_calls": [],
                        "prompt_tokens": 0,
                        "completion_tokens": 0
                    }
                # If not private, allow falling through to cloud
                logger.info("Non-private query failed on local; falling over to cloud tier.")
                tier = 2

        # 3. Tier 2: OpenRouter Free (Inkling 2 Small)
        if tier == 2:
            if not db.is_quota_exceeded("openrouter") and self.openrouter.is_configured():
                try:
                    res = await self.openrouter.chat(
                        messages=messages,
                        tools=tools,
                        effort=effort,
                        system_prompt=system_prompt
                    )
                    db.record_usage("openrouter", res.get("prompt_tokens", 0), res.get("completion_tokens", 0))
                    # Cache public responses without tools
                    if not tools and res.get("content"):
                        cache_key = self._generate_cache_key(messages, system_prompt)
                        db.set_cached_response(cache_key, "openrouter", res["content"])
                    return res
                except Exception as e:
                    logger.warning(f"Tier 2 (OpenRouter) failed: {e}. Falling over to Tier 3 (Gemini)...")
                    tier = 3
            else:
                logger.info("OpenRouter quota reached or not configured. Falling over to Gemini.")
                tier = 3

        # 4. Tier 3: Gemini 2.5 Flash Fallback
        if tier == 3:
            if db.is_quota_exceeded("gemini"):
                return {
                    "provider": "quota_guard",
                    "model": "none",
                    "content": "⚠️ Today's daily quota for Gemini has been reached. Please try again tomorrow or run locally with `/local`.",
                    "tool_calls": [],
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                }

            if not self.gemini.is_configured():
                return {
                    "provider": "config_guard",
                    "model": "none",
                    "content": "⚠️ Cloud brain is not configured. Please add `OPENROUTER_API_KEY` or `GEMINI_API_KEY` to `.env`.",
                    "tool_calls": [],
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                }

            res = await self.gemini.chat(
                messages=messages,
                tools=tools,
                system_prompt=system_prompt
            )
            db.record_usage("gemini", res.get("prompt_tokens", 0), res.get("completion_tokens", 0))
            if not tools and res.get("content"):
                cache_key = self._generate_cache_key(messages, system_prompt)
                db.set_cached_response(cache_key, "gemini", res["content"])
            return res

        raise RuntimeError("Unreachable provider state")


provider_manager = ProviderManager()
