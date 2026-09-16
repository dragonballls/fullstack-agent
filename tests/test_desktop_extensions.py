from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from quality_of_life.family_locations import FamilyLocationService
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.workflows import Workflow, WorkflowStep, WorkflowStore
from scripts.jarvis_desktop_extensions import JarvisExtendedController, _family_command


class FakeRuntime:
    def __init__(self):
        self.policy = CapabilityPolicy(allowed=frozenset({Capability.APP_READ}), require_confirmation=frozenset())
        self.calls = []

    def dispatch(self, capability, operation, *args, **kwargs):
        self.calls.append((capability, operation, args, kwargs))
        return "ok"


class DesktopExtensionTests(unittest.TestCase):
    def test_workflow_request_is_resolved_before_general_orchestrator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflows.json"
            store = WorkflowStore(path)
            workflow = Workflow.new("Morning", steps=(WorkflowStep("applications.list", {}),))
            store.create(workflow)
            result = JarvisExtendedController.run_workflow_request(
                FakeRuntime(), store, "do my morning", confirmed=True
            )
            self.assertTrue(result.verified)
            self.assertEqual(result.completed_steps, 1)

    def test_family_commands_parse_as_expected(self):
        self.assertEqual(_family_command("where is Alex"), ("where", "Alex"))
        self.assertEqual(_family_command("show Alex on God’s Eye"), ("show", "Alex"))
        self.assertEqual(_family_command("follow Alex"), ("follow", "Alex"))
        self.assertEqual(_family_command("show my family"), ("show_all", None))
        self.assertEqual(_family_command("stop following"), ("stop", None))

    def test_unconfigured_family_location_does_not_hijack_ordinary_place_lookup(self):
        controller = object.__new__(JarvisExtendedController)
        controller.family_service = FamilyLocationService(provider=None)
        self.assertIsNone(controller._family_request("where is the nearest coffee shop"))


if __name__ == "__main__":
    unittest.main()
