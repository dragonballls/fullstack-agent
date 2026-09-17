import json
import tempfile
import unittest
from pathlib import Path

from quality_of_life.workflows import Workflow, WorkflowRunSummary, WorkflowStep, WorkflowStore


class WorkflowStoreTests(unittest.TestCase):
    def test_round_trip_survives_a_new_store_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflows.json"
            first = WorkflowStore(path)
            workflow = Workflow.new(
                "Morning Setup",
                aliases=("morning", "start my day"),
                steps=(WorkflowStep("applications.list", {}),),
            )
            first.create(workflow)
            second = WorkflowStore(path)
            loaded = second.get(workflow.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.name, "Morning Setup")
            self.assertEqual(loaded.aliases, ("morning", "start my day"))
            self.assertEqual(loaded.steps[0].operation, "applications.list")

    def test_name_and_alias_resolution_is_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(Path(tmp) / "workflows.json")
            workflow = Workflow.new(
                "  Morning   Setup  ",
                aliases=("  Start Day ",),
                steps=(WorkflowStep("applications.list", {}),),
            )
            store.create(workflow)
            self.assertEqual(store.resolve("RUN MY   MORNING SETUP").id, workflow.id)
            self.assertEqual(store.resolve("do start day").id, workflow.id)

    def test_malformed_store_is_rejected_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflows.json"
            path.write_text("[]", encoding="utf-8")
            store = WorkflowStore(path)
            with self.assertRaises(ValueError):
                store.list()
            self.assertEqual(path.read_text(encoding="utf-8"), "[]")

    def test_unknown_operation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflows.json"
            store = WorkflowStore(path)
            with self.assertRaises(ValueError):
                store.create(Workflow.new("Bad", steps=(object(),)))

    def test_ambiguous_resolution_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(Path(tmp) / "workflows.json")
            store.create(Workflow.new("Work", aliases=("daily",), steps=(WorkflowStep("applications.list", {}),)))
            store.create(Workflow.new("Study", aliases=("daily",), steps=(WorkflowStep("applications.list", {}),)))
            self.assertIsNone(store.resolve("daily"))

    def test_run_summary_does_not_persist_arguments_or_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(Path(tmp) / "workflows.json")
            workflow = Workflow.new("Safe", steps=(WorkflowStep("applications.list", {"note": "harmless"}),))
            store.create(workflow)
            store.record_run(workflow.id, WorkflowRunSummary.completed(run_id="r1", completed_steps=1))
            payload = json.loads(Path(tmp, "workflows.json").read_text(encoding="utf-8"))
            self.assertNotIn("arguments", json.dumps(payload[workflow.id]["last_run"]))
            self.assertNotIn("OPENAI_API_KEY", json.dumps(payload[workflow.id]["last_run"]))
            self.assertEqual(payload[workflow.id]["last_run"]["completed_steps"], 1)


if __name__ == "__main__":
    unittest.main()
