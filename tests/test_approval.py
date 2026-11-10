"""Unit tests for the Human-in-the-Loop Approval Gate."""

import unittest
import asyncio
from tools.approval import stage_action, execute_approved_action, reject_action, register_approvable_action
from database import db


class TestApprovalGate(unittest.TestCase):
    def setUp(self):
        # Register a mock test action
        async def mock_handler(target: str, message: str):
            return f"Mock action performed on {target}: {message}"

        register_approvable_action("mock_test_action", mock_handler)

    def test_stage_and_approve_lifecycle(self):
        """Action must stage, accept execution, and return result."""
        staged = stage_action(
            action_type="mock_test_action",
            payload={"target": "database", "message": "cleanup"},
            description="Test cleanup action"
        )
        action_id = staged["action_id"]
        self.assertTrue(action_id.startswith("act_"))

        # Verify staged state in SQLite
        record = db.get_pending_action(action_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "pending")

        # Execute approval
        result = asyncio.run(execute_approved_action(action_id))
        self.assertIn("Executed Successfully", result)
        self.assertIn("cleanup", result)

        # Replay Protection: cannot execute again
        repeat = asyncio.run(execute_approved_action(action_id))
        self.assertIn("already executed", repeat)

    def test_rejection_lifecycle(self):
        """Action must stage and reject successfully."""
        staged = stage_action(
            action_type="mock_test_action",
            payload={"target": "files", "message": "delete"},
            description="Test delete action"
        )
        action_id = staged["action_id"]

        # Reject action
        reject_res = reject_action(action_id)
        self.assertIn("cancelled", reject_res)

        record = db.get_pending_action(action_id)
        self.assertEqual(record["status"], "rejected")

        # Execution after rejection should fail
        exec_after_reject = asyncio.run(execute_approved_action(action_id))
        self.assertIn("already rejected", exec_after_reject)


if __name__ == "__main__":
    unittest.main()

