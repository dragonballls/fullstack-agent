import unittest
from unittest.mock import Mock

from quality_of_life.background_mode import (
    BackgroundComponent,
    BackgroundMode,
    BackgroundModeController,
)
from quality_of_life.background_runtime import JarvisBackgroundRuntime


class BackgroundModeTests(unittest.TestCase):
    def test_minimize_suspends_foreground_only_but_keeps_always_component_active(self) -> None:
        events: list[str] = []
        controller = BackgroundModeController()
        controller.register(
            BackgroundComponent(
                "ui",
                "foreground_only",
                lambda: events.append("ui-bg"),
                lambda: events.append("ui-fg"),
            )
        )
        controller.register(
            BackgroundComponent(
                "voice",
                "always",
                lambda: events.append("voice-bg"),
                lambda: events.append("voice-fg"),
            )
        )

        self.assertTrue(controller.enter_background())
        self.assertEqual(controller.state, BackgroundMode.BACKGROUND)
        self.assertEqual(events, ["ui-bg"])

        self.assertTrue(controller.enter_foreground())
        self.assertEqual(controller.state, BackgroundMode.FOREGROUND)
        self.assertEqual(events, ["ui-bg", "ui-fg"])

    def test_callback_failure_does_not_abort_other_components(self) -> None:
        events: list[str] = []
        controller = BackgroundModeController()
        controller.register(
            BackgroundComponent(
                "bad",
                "foreground_only",
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            )
        )
        controller.register(
            BackgroundComponent("good", "foreground_only", lambda: events.append("good"))
        )

        self.assertTrue(controller.enter_background())
        self.assertEqual(events, ["good"])
        self.assertEqual(controller.status()["state"], "background")
        self.assertEqual(controller.status()["degraded"], ["bad"])

    def test_repeated_transitions_are_idempotent(self) -> None:
        calls: list[str] = []
        controller = BackgroundModeController()
        controller.register(
            BackgroundComponent(
                "ui",
                "foreground_only",
                lambda: calls.append("bg"),
                lambda: calls.append("fg"),
            )
        )

        self.assertTrue(controller.enter_background())
        self.assertFalse(controller.enter_background())
        self.assertTrue(controller.enter_foreground())
        self.assertFalse(controller.enter_foreground())
        self.assertEqual(calls, ["bg", "fg"])

    def test_background_runtime_minimize_does_not_stop_services(self) -> None:
        voice = Mock()
        voice.running = True
        voice.last_error = None
        hand = Mock()
        hand.status.return_value = {"enabled": True, "state": "active"}
        ui_events: list[str] = []
        runtime = JarvisBackgroundRuntime(
            voice_listener=voice,
            hand_control=hand,
            on_ui_background=lambda: ui_events.append("bg"),
            on_ui_foreground=lambda: ui_events.append("fg"),
        )

        runtime.start()
        self.assertTrue(runtime.minimize())
        self.assertEqual(runtime.lifecycle.state, BackgroundMode.BACKGROUND)
        voice.start.assert_called_once_with()
        hand.stop.assert_not_called()
        self.assertEqual(ui_events, ["bg"])
        self.assertTrue(runtime.status()["voice"]["running"])
        self.assertEqual(runtime.status()["hand_control"]["state"], "active")

        self.assertTrue(runtime.restore())
        self.assertEqual(ui_events, ["bg", "fg"])
        runtime.stop()
        voice.stop.assert_called_once_with()
        hand.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
