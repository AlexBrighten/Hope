"""Unit tests for the Compact Tools Suite & Contextual Filter."""

import unittest
import asyncio
from tools.registry import get_contextual_tools, dispatch_tool_call
from tools.memory import remember, recall, create_task, list_tasks, complete_task
from database import db


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

    def test_task_persistence(self):
        asyncio.run(create_task("Follow up with recruiter", priority="high"))
        task_id = db.list_tasks()[0]["id"]
        self.assertIn(task_id, asyncio.run(list_tasks()))
        self.assertIn("Completed", asyncio.run(complete_task(task_id)))

    def test_system_stats_tool(self):
        """PC hardware butler must gather stats and format cleanly."""
        res = asyncio.run(dispatch_tool_call("pc_status", {}))
        self.assertIn("Hardware", res)
        self.assertIn("CPU Usage", res)
        self.assertIn("RAM Usage", res)

    def test_system_contextual_filtering(self):
        """System tools must return pc_status and clean_temp."""
        sys_tools = get_contextual_tools("system")
        names = [t["function"]["name"] for t in sys_tools]
        self.assertIn("pc_status", names)
        self.assertIn("clean_temp", names)

    def test_persona_engine(self):
        """Persona engine must support dynamic switching between JARVIS, EDITH, etc."""
        from brain.persona import set_active_persona, get_active_persona_name, get_persona_greeting, get_system_persona

        self.assertTrue(set_active_persona("edith"))
        self.assertEqual(get_active_persona_name(), "edith")
        self.assertIn("E.D.I.T.H.", get_persona_greeting())
        self.assertIn("E.D.I.T.H.", get_system_persona())

        self.assertTrue(set_active_persona("jarvis"))
        self.assertEqual(get_active_persona_name(), "jarvis")
        self.assertIn("J.A.R.V.I.S.", get_system_persona())

    def test_terminal_run_command(self):
        """Shell execution tool must execute non-destructive commands autonomously."""
        from tools.terminal import run_command
        res = asyncio.run(run_command("python --version"))
        self.assertIn("Python", str(res))
        self.assertIn("Exit Code", str(res))

    def test_terminal_destructive_staging(self):
        """Destructive shell commands must be staged for user approval."""
        from tools.terminal import run_command
        res = asyncio.run(run_command("del /s /q dangerous_folder"))
        self.assertIsInstance(res, dict)
        self.assertIn("reply_markup", res)
        self.assertIn("Authorization Required", res["description"])

    def test_filesystem_operations(self):
        """Filesystem tools must support listing, writing, reading, and searching."""
        from tools.filesystem import write_file, read_file, list_dir, search_files
        test_file = "workspace/test_unleashed.txt"
        
        # Write
        write_res = write_file(test_file, "JARVIS unleashed operational test.")
        self.assertIn("Successfully wrote", write_res)
        
        # Read
        read_res = read_file(test_file)
        self.assertIn("JARVIS unleashed", read_res)
        
        # List
        list_res = list_dir("workspace")
        self.assertIn("test_unleashed.txt", list_res)
        
        # Search
        search_res = search_files("test_unleashed*", "workspace")
        self.assertIn("test_unleashed.txt", search_res)

        # Cleanup
        try:
            import os
            os.remove(test_file)
        except Exception:
            pass

    def test_desktop_kill_protected_process(self):
        """Desktop process manager must protect critical system processes."""
        from tools.desktop import kill_process
        res = kill_process("explorer.exe")
        self.assertIn("Cannot terminate critical", res)


if __name__ == "__main__":
    unittest.main()
