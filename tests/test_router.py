"""Unit tests for the Deterministic Privacy & Intent Router."""

import unittest
import time
from brain.router import router


class TestRouter(unittest.TestCase):
    def test_routing_latency_under_5ms(self):
        """Benchmark: Router must classify in under 5 ms (<1 ms target)."""
        queries = [
            "What's on my calendar for tomorrow?",
            "Search for latest news on OpenAI funding",
            "Can you draft an email to Alice?",
            "Write a Python script to parse JSON",
            "Hello, what time is it?"
        ]
        start = time.perf_counter()
        for q in queries:
            router.route(q)
        duration_ms = (time.perf_counter() - start) * 1000
        avg_ms = duration_ms / len(queries)
        self.assertLess(avg_ms, 5.0, f"Router too slow: {avg_ms:.2f} ms per query")

    def test_strict_privacy_boundary(self):
        """Private personal data must always map to Tier 1 with is_private=True."""
        private_queries = [
            ("Check my unread emails", "mail"),
            ("Mail Alice that the meeting moved", "mail"),
            ("What is my schedule today?", "calendar"),
            ("Remind me tomorrow at 9am", "calendar"),
            ("Please reschedule my meeting at 3pm", "calendar"),
            ("Remember that my favorite coffee is espresso", "memory"),
            ("Add a task to call the recruiter", "tasks"),
            ("Search my inbox for receipt", "mail")
        ]
        for query, expected_cat in private_queries:
            decision = router.route(query)
            self.assertEqual(decision.tier, 1, f"Failed for query: {query}")
            self.assertTrue(decision.is_private, f"Expected private for: {query}")
            if expected_cat:
                self.assertEqual(decision.tool_category, expected_cat)

    def test_public_research_routes_to_tier2(self):
        """Public web research, founder lookups, and code tasks route to Tier 2."""
        research_queries = [
            "Search for Anthropic latest models",
            "Who is the founder of Thinking Machines?",
            "Read page https://news.ycombinator.com",
            "Debug this Python algorithm",
            "What is the valuation of Stripe?"
        ]
        for query in research_queries:
            decision = router.route(query)
            self.assertEqual(decision.tier, 2, f"Failed for query: {query}")
            self.assertFalse(decision.is_private, f"Expected public for: {query}")

    def test_slash_command_overrides(self):
        """Slash command overrides must take absolute precedence."""
        self.assertEqual(router.route("/local what is the weather").tier, 1)
        self.assertEqual(router.route("/free check research paper").tier, 2)
        self.assertEqual(router.route("/gemini transcribe audio").tier, 3)
        self.assertEqual(router.route("/research quantum computing").tool_category, "research")
        self.assertEqual(router.route("/jobs Python developer").tool_category, "research")
        
        deep = router.route("/deep analyze market economics")
        self.assertEqual(deep.tier, 2)
        self.assertEqual(deep.reasoning_effort, "high")
        self.assertEqual(deep.cleaned_query, "analyze market economics")


if __name__ == "__main__":
    unittest.main()
