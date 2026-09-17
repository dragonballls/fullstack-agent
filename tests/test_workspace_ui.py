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

    def test_workspace_views_do_not_block_existing_visualizer_input(self):
        script = workspace_script()
        self.assertIn('.jw-view { display:none; position:absolute; inset:0; pointer-events:none; }', script)
        self.assertIn('.jw-tab { border:', script)
        self.assertIn('.jw-chip { padding:', script)

    def test_gods_eye_status_dispatches_registered_location_action(self):
        class FakeRuntime:
            def __init__(self):
                self.calls = []

            def dispatch(self, capability, operation):
                self.calls.append((capability.value, operation))
                return {"point": {"latitude": 1.0, "longitude": 2.0}, "permitted": True, "source": "system"}

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
        self.assertEqual(api.host.controller.runtime.calls, [("location.read", "locations.current")])

    def test_workspace_api_exposes_activity_and_provider_snapshots(self):
        class FakeRuntime:
            def activity_snapshot(self, limit=20):
                return [{"id": "a1", "status": "running", "progress": 42, "step": "Testing"}]

            def activity_cancel(self, activity_id):
                return {"id": activity_id, "status": "running", "cancel_requested": True}

            def dispatch(self, capability, operation):
                return {"point": {"latitude": 1.0, "longitude": 2.0}, "permitted": True, "source": "system"}

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

        self.assertEqual(api.activity_snapshot()[0]["progress"], 42)
        self.assertEqual(api.activity_cancel("a1")["cancel_requested"], True)
        providers = api.gods_eye_providers()
        self.assertEqual([item["kind"] for item in providers], ["device", "phone", "family"])
        self.assertTrue(providers[0]["authorized"])

    def test_workspace_script_surfaces_activity_and_provider_state(self):
        script = workspace_script()
        self.assertIn("activity_snapshot", script)
        self.assertIn("activity_cancel", script)
        self.assertIn("gods_eye_providers", script)
        self.assertIn("ACTIVITY", script)

    def test_gods_eye_status_rejects_unpermitted_location_result(self):
        class FakeRuntime:
            def dispatch(self, capability, operation):
                return {"point": {"latitude": 1.0, "longitude": 2.0}, "permitted": False}

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

        self.assertFalse(result["ok"])
        self.assertFalse(result["available"])
        self.assertIn("authorized", result["reason"].casefold())

    def test_workspace_restore_hydrates_backend_state_before_activation(self):
        script = workspace_script()
        self.assertIn("async function hydrateWorkspace()", script)
        self.assertIn("const state = await api().workspace_state()", script)
        self.assertIn("setView(target, false)", script)


if __name__ == "__main__":
    unittest.main()
