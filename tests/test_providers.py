"""Unit tests for Provider Chain Failover, Privacy Guard, and Response Caching."""

import unittest
import asyncio
from unittest.mock import AsyncMock, patch
from brain.providers import provider_manager
from database import db


class TestProviders(unittest.TestCase):
    def setUp(self):
        with db._get_connection() as conn:
            conn.execute("DELETE FROM response_cache")

    def test_strict_privacy_guard_never_leaks_to_cloud(self):
        """When a private query fails on local brain, it must NOT fail over to cloud."""
        with patch.object(provider_manager.local, "chat", new_callable=AsyncMock) as mock_local, \
             patch.object(provider_manager.openrouter, "chat", new_callable=AsyncMock) as mock_or, \
             patch.object(provider_manager.gemini, "chat", new_callable=AsyncMock) as mock_gem:

            mock_local.side_effect = RuntimeError("Ollama connection failed")

            result = asyncio.run(provider_manager.chat(
                messages=[{"role": "user", "content": "Check my secret emails"}],
                tier=1,
                is_private=True
            ))

            self.assertEqual(result["provider"], "privacy_guard")
            self.assertIn("Privacy Guard", result["content"])
            # Ensure cloud tiers were NEVER called
            mock_or.assert_not_called()
            mock_gem.assert_not_called()

    def test_tier2_failover_to_tier3_for_public_tasks(self):
        """When Tier 2 fails (e.g. 429/timeout), public queries must fail over to Tier 3."""
        with patch.object(provider_manager.openrouter, "is_configured", return_value=True), \
             patch.object(provider_manager.openrouter, "chat", new_callable=AsyncMock) as mock_or, \
             patch.object(provider_manager.gemini, "is_configured", return_value=True), \
             patch.object(provider_manager.gemini, "chat", new_callable=AsyncMock) as mock_gem:

            mock_or.side_effect = RuntimeError("429 Too Many Requests")
            mock_gem.return_value = {
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "content": "Result from Gemini fallback",
                "tool_calls": [],
                "prompt_tokens": 10,
                "completion_tokens": 5
            }

            result = asyncio.run(provider_manager.chat(
                messages=[{"role": "user", "content": "Search public papers on quantum computing"}],
                tier=2,
                is_private=False
            ))

            self.assertEqual(result["provider"], "gemini")
            self.assertIn("Gemini fallback", result["content"])
            mock_or.assert_called_once()
            mock_gem.assert_called_once()

    def test_response_cache_skips_provider(self):
        """Identical public queries must be served from SQLite response cache."""
        with patch.object(provider_manager.openrouter, "is_configured", return_value=True), \
             patch.object(provider_manager.openrouter, "chat", new_callable=AsyncMock) as mock_or:

            mock_or.return_value = {
                "provider": "openrouter",
                "model": "inkling-2-small",
                "content": "Freshly fetched research result",
                "tool_calls": [],
                "prompt_tokens": 15,
                "completion_tokens": 20
            }

            query = [{"role": "user", "content": "Explain Moore's Law in 1 sentence"}]

            # 1st call: hits provider
            res1 = asyncio.run(provider_manager.chat(query, tier=2, is_private=False))
            self.assertEqual(res1["provider"], "openrouter")
            self.assertEqual(mock_or.call_count, 1)

            # 2nd call: hits cache, provider call count remains 1!
            res2 = asyncio.run(provider_manager.chat(query, tier=2, is_private=False))
            self.assertEqual(res2["provider"], "cache")
            self.assertEqual(res2["content"], "Freshly fetched research result")
            self.assertEqual(mock_or.call_count, 1)


if __name__ == "__main__":
    unittest.main()
