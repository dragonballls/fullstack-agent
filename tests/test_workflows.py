import json
import tempfile
import unittest
from pathlib import Path

from quality_of_life.workflows import Workflow, WorkflowRunSummary, WorkflowService, WorkflowStep, WorkflowStore


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
            loaded = WorkflowStore(path).get(workflow.id)
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
            with self.assertRaises(ValueError):
                Workflow.new("Bad", steps=(WorkflowStep("not.real", {}),))

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

    def test_execute_can_publish_activity_progress_and_success(self):
        class FakePolicy:
            def needs_confirmation(self, _capability):
                return False

        class FakeRuntime:
            def __init__(self):
                from quality_of_life.activity import ActivityStore
                self.policy = FakePolicy()
                self.activity = ActivityStore()

            def dispatch(self, _capability, operation, **_kwargs):
                return {"operation": operation}

        runtime = FakeRuntime()
        workflow = Workflow.new(
            "Build",
            steps=(
                WorkflowStep("applications.list", {}),
                WorkflowStep("processes.list", {}),
            ),
        )

        result = WorkflowService.execute(runtime, workflow, activity_store=runtime.activity)
        records = runtime.activity.list()

        self.assertTrue(result.verified)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status.value, "succeeded")
        self.assertEqual(records[0].progress, 100)
        self.assertEqual(records[0].step, "Complete")

    def test_execute_marks_activity_waiting_for_confirmation(self):
        class FakePolicy:
            def needs_confirmation(self, _capability):
                return True

        class FakeRuntime:
            def __init__(self):
                from quality_of_life.activity import ActivityStore
                self.policy = FakePolicy()
                self.activity = ActivityStore()

            def dispatch(self, *args, **kwargs):
                raise AssertionError("protected operation must not dispatch without confirmation")

        runtime = FakeRuntime()
        workflow = Workflow.new("Protected", steps=(WorkflowStep("files.delete", {"path": "x"}),))

        result = WorkflowService.execute(runtime, workflow, confirmed=False, activity_store=runtime.activity)
        record = runtime.activity.list()[0]

        self.assertTrue(result.needs_confirmation)
        self.assertFalse(result.verified)
        self.assertEqual(record.status.value, "waiting")
        self.assertEqual(record.step, "Waiting for confirmation")

    def test_continue_on_error_does_not_leave_activity_terminal_before_next_step(self):
        class FakePolicy:
            def needs_confirmation(self, _capability):
                return False

        class FakeRuntime:
            def __init__(self):
                from quality_of_life.activity import ActivityStore
                self.policy = FakePolicy()
                self.activity = ActivityStore()

            def dispatch(self, _capability, operation, **_kwargs):
                if operation == "applications.list":
                    raise RuntimeError("first step failed")
                return {"operation": operation}

        runtime = FakeRuntime()
        workflow = Workflow.new(
            "Resilient",
            steps=(
                WorkflowStep("applications.list", {}, continue_on_error=True),
                WorkflowStep("processes.list", {}),
            ),
        )

        result = WorkflowService.execute(runtime, workflow, activity_store=runtime.activity)
        record = runtime.activity.list()[0]

        self.assertFalse(result.verified)
        self.assertEqual(result.completed_steps, 1)
        self.assertEqual(record.status.value, "failed")
        self.assertIn("first step failed", record.error)

    def test_workflow_error_summary_redacts_common_secret_patterns(self):
        self.assertEqual(
            WorkflowService._safe_error(RuntimeError("token=SECRET123 authorization=Bearer SECRET456")),
            "token=[redacted] authorization=[redacted]",
        )


if __name__ == "__main__":
    unittest.main()
