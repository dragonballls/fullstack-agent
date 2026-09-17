import unittest

from quality_of_life.workspace_ui import WorkspaceBridge, workspace_script


class WorkspaceUiTests(unittest.TestCase):
    def test_bridge_keeps_workspace_state_and_command_surface(self):
        bridge = WorkspaceBridge()
        state = bridge.activate("gods-eye")
        self.assertEqual(state["active"], "gods-eye")
        self.assertTrue(state["command_bar_visible"])
        self.assertIn("map", state["panels"])

    def test_bridge_rejects_unknown_workspace(self):
        bridge = WorkspaceBridge()
        with self.assertRaises(ValueError):
            bridge.activate("not-a-workspace")

    def test_workspace_script_preserves_existing_command_surface_and_persists_view(self):
        script = workspace_script()
        self.assertIn("GOD'S EYE", script)
        self.assertIn("jarvis-text-input", script)
        self.assertIn("localStorage", script)
        self.assertIn("jarvis.activeWorkspace", script)
        self.assertIn("activate_workspace", script)
        self.assertIn("gods_eye_status", script)


if __name__ == "__main__":
    unittest.main()
