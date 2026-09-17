import unittest

from quality_of_life.workspace import WorkspaceState, WorkspaceType


class WorkspaceContractTests(unittest.TestCase):
    def test_workspace_starts_with_persistent_command_surface(self):
        state = WorkspaceState.default()
        self.assertEqual(state.active, WorkspaceType.HOME)
        self.assertTrue(state.command_bar_visible)
        self.assertEqual(state.input_mode, "text")

    def test_switching_workspace_preserves_command_surface(self):
        state = WorkspaceState.default().activate(WorkspaceType.GODS_EYE)
        self.assertEqual(state.active, WorkspaceType.GODS_EYE)
        self.assertTrue(state.command_bar_visible)
        self.assertEqual(state.input_mode, "text")

    def test_gods_eye_workspace_has_expected_quality_of_life_panels(self):
        state = WorkspaceState.default().activate(WorkspaceType.GODS_EYE)
        self.assertIn("map", state.panels)
        self.assertIn("entities", state.panels)
        self.assertIn("activity", state.panels)
        self.assertIn("command", state.panels)


if __name__ == "__main__":
    unittest.main()
