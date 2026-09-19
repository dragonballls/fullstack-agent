from __future__ import annotations

import unittest
from unittest.mock import patch

import scripts.jarvis_desktop as desktop


class JarvisDesktopStartupTests(unittest.TestCase):
    def test_prism_live_smoke_is_opt_in_and_uses_prism_target(self) -> None:
        calls: list[tuple[object, ...]] = []

        class FakeRouter:
            def __init__(self, targets):
                calls.append(("init", targets))

            @classmethod
            def prism_target(cls):
                return "fake-prism-target"

            def complete(self, messages):
                calls.append(("complete", messages))
                return "prism-ready", "prism-astra"

        with patch.dict(__import__("os").environ, {"JARVIS_PRISM_LIVE_SMOKE": "1"}, clear=False):
            with patch.object(desktop, "CloudModelRouter", FakeRouter):
                desktop._run_prism_live_smoke()

        self.assertEqual(calls[0], ("init", ("fake-prism-target",)))
        self.assertEqual(calls[1][0], "complete")
        self.assertEqual(calls[1][1][0]["content"], "Reply with exactly: prism-ready")

    def test_visualizer_starts_before_core_controller_construction(self) -> None:
        events: list[str] = []

        class FakeVisualizer:
            def __init__(self) -> None:
                events.append("visualizer_init")

            def start(self) -> None:
                events.append("visualizer_start")

            def stop(self) -> None:
                events.append("visualizer_stop")

        class FakeController:
            def __init__(self) -> None:
                events.append("controller_init")

        class FakeHost:
            def __init__(self, controller, *, visualizer):
                events.append("host_init")
                self.controller = controller
                self.visualizer = visualizer

            def start(self) -> None:
                events.append("host_start")

            def run_window(self) -> None:
                events.append("run_window")

            def stop(self) -> None:
                events.append("host_stop")

        with patch.object(desktop, "VisualizerAdapter", FakeVisualizer), patch.object(
            desktop, "JarvisDesktopController", FakeController
        ), patch.object(desktop, "FullstackJarvisHost", FakeHost):
            self.assertEqual(desktop.main(), 0)

        self.assertLess(events.index("visualizer_start"), events.index("controller_init"))
        self.assertEqual(events[-1], "host_stop")


if __name__ == "__main__":
    unittest.main()
