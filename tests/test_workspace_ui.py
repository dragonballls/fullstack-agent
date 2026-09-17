import unittest

from quality_of_life.workspace_ui import WorkspaceBridge, workspace_script


class WorkspaceUiTests(unittest.TestCase):
    def test_bridge_keeps_workspace_state_and_command_surface(self):
        bridge = WorkspaceBridge()
        state = bridge.activate("gods-eye")
        self.assertEqual(state["active"], "gods-eye")
        self.assertTrue(state["command_bar_visible"])
        self.assertIn("map", state["panels"])

    def test_workspace_script_contains_persistent_command_and_workspace_controls(self):
        script = workspace_script()
        self.assertIn("God's Eye", script)
        self.assertIn("command", script)
        self.assertIn("pywebview.api.submit_text", script)
        self.assertIn("workspaceState", script)


if __name__ == "__main__":
    unittest.main()
