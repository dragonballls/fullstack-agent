from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from scripts.jarvis_desktop import FullstackJarvisHost


class FloatingCommandBarContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desktop = Path("scripts/jarvis_desktop.py").read_text(encoding="utf-8")
        cls.smoke = Path("scripts/verify_windows_gui_smoke.ps1").read_text(encoding="utf-8")

    def test_global_hotkey_is_dedicated_and_system_wide(self):
        self.assertIn('FLOATING_HOTKEY_LABEL = "Ctrl+Alt+Shift+F12"', self.desktop)
        self.assertIn("RegisterHotKey(None, FLOATING_HOTKEY_ID", self.desktop)
        self.assertIn("MOD_CONTROL", self.desktop)
        self.assertIn("MOD_ALT", self.desktop)
        self.assertIn("MOD_SHIFT", self.desktop)
        self.assertIn("VK_F12 = 0x7B", self.desktop)

    def test_floating_window_is_separate_draggable_topmost_window(self):
        self.assertIn("FLOATING_TEXT_INPUT_HTML", self.desktop)
        self.assertIn('"hidden": True', self.desktop)
        self.assertIn('"frameless": True', self.desktop)
        self.assertIn('"easy_drag": True', self.desktop)
        self.assertIn('"on_top": True', self.desktop)
        self.assertIn('class="pywebview-drag-region"', self.desktop)
        self.assertIn("events.moved += self._on_floating_moved", self.desktop)

    def test_command_bar_can_return_to_the_main_app(self):
        self.assertIn("toggle_text_link(self, detached: bool | None = None)", self.desktop)
        self.assertIn("window.hide()", self.desktop)
        self.assertIn("_show_main_text_link()", self.desktop)
        self.assertIn("jarvisNeuralCommandSurface", self.desktop)
        self.assertIn("toggle_text_link(false)", self.desktop)

    def test_position_is_persisted(self):
        self.assertIn('FLOATING_POSITION_FILE = LOG_DIR.parent / "settings" / "floating_text_link.json"', self.desktop)
        self.assertIn("_load_floating_position", self.desktop)
        self.assertIn("_save_floating_position", self.desktop)
        self.assertIn('json.dumps({"x": x, "y": y})', self.desktop)

    def test_position_loader_rejects_non_object_and_boolean_coordinates(self):
        import json
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch

        controller = Mock()
        host = FullstackJarvisHost(controller, visualizer=Mock(), voice=Mock(), hands=Mock())

        with TemporaryDirectory() as tmp:
            test_path = Path(tmp) / "floating-position.json"
            for payload in ([1, 2], {"x": True, "y": 20}, {"x": 10, "y": False}):
                with patch("scripts.jarvis_desktop.FLOATING_POSITION_FILE", test_path):
                    test_path.write_text(json.dumps(payload), encoding="utf-8")
                    self.assertEqual(host._load_floating_position(), (None, None))

    def test_main_window_close_destroys_hidden_floating_window(self):
        controller = Mock()
        host = FullstackJarvisHost(controller, visualizer=Mock(), voice=Mock(), hands=Mock())
        floating = SimpleNamespace(x=120, y=80, destroy=Mock())
        host._floating_window = floating
        host._save_floating_position = Mock()

        host._on_main_window_closing()

        self.assertTrue(host._shutting_down)
        self.assertFalse(host._floating_visible)
        host._save_floating_position.assert_called_once_with()
        floating.destroy.assert_called_once_with()
        self.assertIsNone(host._floating_window)

    def test_collapsing_surface_does_not_overwrite_expanded_geometry(self):
        for token in (
            "#jarvis-text-shell.history-collapsed{height:48px!important;min-height:48px!important;resize:none}",
            "function persistGeometry(){",
            "if(historyCollapsed)return;",
        ):
            self.assertIn(token, self.desktop)

    def test_confirmation_cancel_updates_status(self):
        self.assertIn('status.textContent="CANCELLED"', self.desktop)

    def test_command_surface_retries_bridge_readiness(self):
        self.assertIn("const readyPoll=window.setInterval(function(){", self.desktop)

    def test_main_text_surface_is_resizable_and_keeps_response_transcript(self):
        for token in (
            'resize:both',
            'min-width:320px',
            'min-height:170px',
            '#jarvis-text-history',
            'appendOutput',
            'setBuildTheme',
            'jarvis.textSurface.geometry',
            'jarvis.textSurface.collapsed',
            'SHIFT+ENTER — NEW LINE',
        ):
            self.assertIn(token, self.desktop)

    def test_shared_text_surface_is_movable_and_build_aware(self):
        for token in ('#jarvis-text-header', 'startDrag', 'persistGeometry', 'setTheme', 'data-theme'):
            self.assertIn(token, self.desktop)

    def test_release_smoke_requires_floating_window_creation(self):
        self.assertIn("floating command bar window object created;", self.smoke)
        self.assertIn("did not create the floating command bar window object", self.smoke)


if __name__ == "__main__":
    unittest.main()
