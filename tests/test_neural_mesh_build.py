import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class NeuralMeshBuildTests(unittest.TestCase):
    def test_protected_build_exists(self):
        from quality_of_life.ui_builds import UIBuildStore
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            self.assertTrue(store.get("neural-mesh").protected)

    def test_entrypoint_installs_bridge(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts" / "jarvis_desktop.pyw").read_text(encoding="utf-8")
        self.assertIn("install_neural_world", text)

    def test_webgl_and_chat_contract(self):
        from quality_of_life.neural_mesh import NEURAL_MESH_BUILTIN
        script = NEURAL_MESH_BUILTIN["script"]
        for token in ("webgl2", "pointerdown", "wheel", "drawElementsInstanced", "neural_world_snapshot", "neural_events", "neural_search", "submit_text", "spatial_windows_catalog", "gods_eye_globe", "neural_observation_state", "jn-earth", "shapeCode", "earthYaw", "earthDistance", "renderEarth", "neural_advanced_tick", "FLUID ECOLOGY", "jn-neural-console", "jn-console-tether", "renderNeuralConsolePlacement", "F13", "jarvis.neuralCommand.collapsed", "ALWAYS IN VIEW", "jn-console-float", "toggle_text_link", "jarvisNeuralCommandSurface", "aRot", "aAngular", "angular_velocity", "globe"):
            self.assertIn(token, script)

    def test_build_2_uses_persistent_camera_facing_command_surface(self):
        from quality_of_life.neural_mesh import NEURAL_MESH_BUILTIN
        self.assertEqual(NEURAL_MESH_BUILTIN["version"], "0.5.0")
        self.assertTrue(NEURAL_MESH_BUILTIN["protected"])
        markup = NEURAL_MESH_BUILTIN["markup"]
        css = NEURAL_MESH_BUILTIN["css"]
        script = NEURAL_MESH_BUILTIN["script"]
        for token in (
            "NEURAL COMMAND",
            "3D CORE LINK",
            "CAMERA FACING",
            "CORE LOCKED",
            "jn-console-collapse",
            "jn-console-hotkey",
            "data-command=",
            "FLOAT",
        ):
            self.assertIn(token, markup)
        self.assertIn('e.key==="Enter"&&!e.shiftKey', script)
        for token in ("transform-style:preserve-3d", "translate3d", "pointer-events:auto", "will-change:transform"):
            self.assertIn(token, css)
        for token in ("jarvis.core", "camera()", "worldToScreen", "clampNumber", "F13", "setConsoleCollapsed"):
            self.assertIn(token, script)

    def test_renderer_has_background_first_observation_contract(self):
        from quality_of_life.neural_mesh import NEURAL_MESH_BUILTIN
        script = NEURAL_MESH_BUILTIN["script"]
        self.assertIn("observation.enabled", script)
        self.assertIn("entity.created", script)
        self.assertIn("entity.retired", script)

    def test_embedded_script_compiles_as_ui_build_script(self):
        import shutil
        import subprocess
        if shutil.which("node") is None:
            self.skipTest("node is unavailable")
        from quality_of_life.neural_mesh import NEURAL_MESH_BUILTIN
        script = NEURAL_MESH_BUILTIN["script"]
        with TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "neural_mesh.js"
            script_path.write_text(script, encoding="utf-8")
            compile_result = subprocess.run(
                ["node", "-e", 'new Function("root", require("fs").readFileSync(process.argv[1], "utf8"));' , str(script_path)],
                capture_output=True,
                text=True,
            )
        self.assertEqual(compile_result.returncode, 0, compile_result.stderr)


if __name__ == "__main__":
    unittest.main()
