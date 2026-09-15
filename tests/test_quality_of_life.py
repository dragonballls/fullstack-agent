from __future__ import annotations

import sys
import time
import unittest
from threading import Event

from quality_of_life import Action, Capability, CapabilityDenied, CapabilityPolicy, QoLOrchestrator, default_registry
from quality_of_life.background import BackgroundJobs
from quality_of_life.computer import ComputerController
from quality_of_life.router import CloudModelRouter, ProviderTarget


class FakePyAutoGUI:
    FAILSAFE = False
    PAUSE = 0

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def moveTo(self, *args, **kwargs): self.calls.append(("moveTo", args))
    def click(self, *args, **kwargs): self.calls.append(("click", args))
    def scroll(self, *args, **kwargs): self.calls.append(("scroll", args))
    def write(self, *args, **kwargs): self.calls.append(("write", args))
    def hotkey(self, *args, **kwargs): self.calls.append(("hotkey", args))


class QualityOfLifeTests(unittest.TestCase):
    def test_capabilities_are_denied_by_default(self) -> None:
        with self.assertRaises(CapabilityDenied):
            CapabilityPolicy().check(Capability.MOUSE_CONTROL)

    def test_default_registry_names_are_stable(self) -> None:
        self.assertEqual(
            default_registry().names(),
            ("background", "browser", "cloud_router", "computer", "screen"),
        )

    def test_orchestrator_checks_policy(self) -> None:
        policy = CapabilityPolicy(allowed=frozenset({Capability.CLIPBOARD}))
        orchestrator = QoLOrchestrator(policy)
        orchestrator.register(Action(Capability.CLIPBOARD, "echo", lambda value: value))
        self.assertEqual(orchestrator.run(Capability.CLIPBOARD, "echo", "ok"), "ok")

    def test_disabled_mutation_is_rejected_before_execution(self) -> None:
        called = False

        def action() -> None:
            nonlocal called
            called = True

        orchestrator = QoLOrchestrator(CapabilityPolicy())
        orchestrator.register(Action(Capability.MOUSE_CONTROL, "click", action))
        with self.assertRaises(CapabilityDenied):
            orchestrator.run(Capability.MOUSE_CONTROL, "click")
        self.assertFalse(called)

    def test_mutation_requires_confirmation_and_executes_after_approval(self) -> None:
        called = []

        orchestrator = QoLOrchestrator(
            CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL}))
        )
        orchestrator.register(Action(Capability.MOUSE_CONTROL, "click", lambda: called.append(True)))

        with self.assertRaises(PermissionError):
            orchestrator.run(Capability.MOUSE_CONTROL, "click")
        self.assertEqual(called, [])

        self.assertTrue(
            orchestrator.run(
                Capability.MOUSE_CONTROL,
                "click",
                confirmation=lambda capability, operation: capability == Capability.MOUSE_CONTROL and operation == "click",
            )
            is None
        )
        self.assertEqual(called, [True])

    def test_confirmation_denial_prevents_execution(self) -> None:
        called = []
        orchestrator = QoLOrchestrator(
            CapabilityPolicy(allowed=frozenset({Capability.APP_LAUNCH}))
        )
        orchestrator.register(Action(Capability.APP_LAUNCH, "launch", lambda: called.append(True)))
        with self.assertRaises(PermissionError):
            orchestrator.run(Capability.APP_LAUNCH, "launch", confirmation=lambda *_: False)
        self.assertEqual(called, [])

    def test_fake_desktop_adapter_calls_pyautogui(self) -> None:
        policy = CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL, Capability.KEYBOARD_CONTROL, Capability.APP_LAUNCH}))
        fake = FakePyAutoGUI()
        controller = ComputerController.__new__(ComputerController)
        controller.policy = policy
        controller.pyautogui = fake
        controller.move(10, 20)
        controller.click()
        controller.type_text("hello")
        controller.hotkey("ctrl", "l")
        self.assertEqual([name for name, _ in fake.calls], ["moveTo", "click", "write", "hotkey"])

    def test_background_job_can_be_cancelled(self) -> None:
        jobs = BackgroundJobs()
        started = Event()

        def task(cancel: Event) -> None:
            started.set()
            while not cancel.is_set():
                time.sleep(0.005)

        jobs.start("test", task)
        self.assertTrue(started.wait(1))
        self.assertTrue(jobs.cancel("test"))
        time.sleep(0.02)
        self.assertEqual(jobs.active(), ())

    def test_router_requires_at_least_one_target(self) -> None:
        with self.assertRaises(ValueError):
            CloudModelRouter(())

    def test_provider_target_is_immutable(self) -> None:
        target = ProviderTarget("x", "https://example.invalid", "KEY", "model")
        with self.assertRaises(Exception):
            target.model = "other"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
