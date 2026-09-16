import unittest

from quality_of_life.background_mode import (
    BackgroundComponent,
    BackgroundMode,
    BackgroundModeController,
)


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


if __name__ == "__main__":
    unittest.main()
