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
        text = Path("scripts/jarvis_desktop.pyw").read_text(encoding="utf-8")
        self.assertIn("install_neural_world", text)

    def test_webgl_and_chat_contract(self):
        from quality_of_life.neural_mesh import NEURAL_MESH_BUILTIN
        script = NEURAL_MESH_BUILTIN["script"]
        for token in ("webgl2", "pointerdown", "wheel", "neural_world_snapshot", "neural_search", "submit_text"):
            self.assertIn(token, script)


if __name__ == "__main__":
    unittest.main()
