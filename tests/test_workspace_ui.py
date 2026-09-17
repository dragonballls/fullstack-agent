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

    def test_gods_eye_status_dispatches_registered_location_action(self):
        class FakeRuntime:
            def __init__(self):
                self.calls = []

            def dispatch(self, capability, operation):
                self.calls.append((capability.value, operation))
                return {"point": {"latitude": 1.0, "longitude": 2.0}}

        class FakeController:
            def __init__(self):
                self.runtime = FakeRuntime()

        class FakeHost:
            def __init__(self):
                self.controller = FakeController()

        desktop = type("Desktop", (), {})()
        from quality_of_life import workspace_ui
        base_api = type("BaseApi", (), {"__init__": lambda self, host: setattr(self, "host", host)})
        desktop.JarvisWebApi = base_api
        desktop.TEXT_INPUT_SCRIPT = ""
        workspace_ui.install(desktop)
        api = desktop.JarvisWebApi(FakeHost())

        result = api.gods_eye_status()
        self.assertTrue(result["ok"])
        self.assertEqual(result["location"]["point"]["latitude"], 1.0)
        self.assertEqual(api.host.controller.runtime.calls, [("location.read", "gods_eye.locate_me")])


if __name__ == "__main__":
    unittest.main()
