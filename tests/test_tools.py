"""Unit tests for the Compact Tools Suite & Contextual Filter."""

import unittest
import asyncio
from tools.registry import get_contextual_tools, dispatch_tool_call
from tools.memory import remember, recall


class TestTools(unittest.TestCase):
    def setUp(self):
        asyncio.run(remember(key="office_location", value="Floor 4, Tower B", category="work"))

    def test_contextual_tool_filtering(self):
        """Contextual filter must return 3-6 specific schemas per category, not all 40+ schemas."""
        mail_tools = get_contextual_tools("mail")
        self.assertLessEqual(len(mail_tools), 6)
        mail_names = [t["function"]["name"] for t in mail_tools]
        self.assertIn("mail_search", mail_names)
        self.assertIn("mail_draft", mail_names)
        self.assertNotIn("cal_list", mail_names)

        cal_tools = get_contextual_tools("calendar")
        self.assertLessEqual(len(cal_tools), 6)
        cal_names = [t["function"]["name"] for t in cal_tools]
        self.assertIn("cal_list", cal_names)
        self.assertIn("cal_add", cal_names)
        self.assertNotIn("mail_search", cal_names)

        research_tools = get_contextual_tools("research")
        res_names = [t["function"]["name"] for t in research_tools]
        self.assertIn("web_search", res_names)
        self.assertIn("company_brief", res_names)
        self.assertNotIn("mail_draft", res_names)

    def test_memory_persistence(self):
        """Memory tools must store and recall facts from SQLite."""
        asyncio.run(remember(key="office_location", value="Floor 4, Tower B", category="work"))
        result = asyncio.run(recall("office_location"))
        self.assertIn("Floor 4, Tower B", result)

    def test_dispatch_tool_call(self):
        """Dispatching tool call directly executes the registered Python function."""
        res = asyncio.run(dispatch_tool_call("recall", {"query": "office_location"}))
        self.assertIn("Floor 4, Tower B", res)


if __name__ == "__main__":
    unittest.main()
