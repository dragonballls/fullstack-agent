import json
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from quality_of_life.ui_builds import (
    DEFAULT_BUILD_ID,
    UIBuildStore,
    build_manager_script,
)


class UIBuildStoreTests(unittest.TestCase):
    def test_bootstraps_protected_defaults_and_uses_default_as_active(self):
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            catalog = store.catalog()
            self.assertGreaterEqual(len(catalog), 3)
            self.assertEqual(store.active().id, DEFAULT_BUILD_ID)
            self.assertTrue(all("protected" in item for item in catalog))

    def test_supports_arbitrarily_many_builds_without_replacing_core_state(self):
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            for index in range(50):
                build = store.save({
                    "id": f"test-build-{index}",
                    "name": f"Test Build {index}",
                    "version": "1.0.0",
                    "description": "generated",
                    "css": f"#build-{index} {{ opacity: 1; }}",
                    "markup": f"<div id='build-{index}'>build</div>",
                })
                self.assertEqual(build.id, f"test-build-{index}")
            ids = {item.id for item in store.list()}
            self.assertEqual(len(ids), 54)
            self.assertEqual(store.active().id, DEFAULT_BUILD_ID)
            self.assertTrue((Path(tmp) / "test-build-49" / "manifest.json").is_file())

    def test_switch_and_multi_step_rollback(self):
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            store.save({"id": "alpha", "name": "Alpha"})
            store.save({"id": "beta", "name": "Beta"})
            store.activate("alpha")
            store.activate("beta")
            self.assertEqual(store.active().id, "beta")
            self.assertEqual(store.rollback().id, "alpha")
            self.assertEqual(store.rollback().id, DEFAULT_BUILD_ID)

    def test_state_persists_across_store_instances(self):
        with TemporaryDirectory() as tmp:
            first = UIBuildStore(tmp)
            first.save({"id": "persisted", "name": "Persisted"})
            first.activate("persisted")
            second = UIBuildStore(tmp)
            self.assertEqual(second.active().id, "persisted")
            self.assertIn("persisted", {item.id for item in second.list()})

    def test_invalid_markup_is_rejected(self):
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            for markup in (
                "<script>alert(1)</script>",
                "<button onclick='alert(1)'>x</button>",
                "<iframe src='https://example.com'></iframe>",
                "<a href='javascript:alert(1)'>x</a>",
            ):
                with self.assertRaises(ValueError):
                    store.save({"id": "unsafe", "name": "Unsafe", "markup": markup})

    def test_build_id_path_traversal_is_rejected(self):
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            with self.assertRaises(ValueError):
                store.get("../outside")
            with self.assertRaises(ValueError):
                store.get("..\\outside")

    def test_protected_builds_cannot_be_overwritten_or_deleted(self):
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            with self.assertRaises(ValueError):
                store.save({"id": DEFAULT_BUILD_ID, "name": "Overwrite"})
            with self.assertRaises(ValueError):
                store.delete(DEFAULT_BUILD_ID)

    def test_corrupt_active_state_recovers_to_default(self):
        with TemporaryDirectory() as tmp:
            store = UIBuildStore(tmp)
            (Path(tmp) / "state.json").write_text(
                json.dumps({"active": "missing-build", "history": ["missing-build"]}),
                encoding="utf-8",
            )
            self.assertEqual(store.active().id, DEFAULT_BUILD_ID)
            self.assertEqual(store.active().id, json.loads((Path(tmp) / "state.json").read_text(encoding="utf-8"))["active"])

    def test_no_console_entrypoint_installs_ui_build_manager(self):
        entrypoint = Path("scripts/jarvis_desktop.pyw").read_text(encoding="utf-8")
        self.assertIn("from quality_of_life.ui_builds import install as install_ui_builds", entrypoint)
        self.assertIn("install_ui_builds(_desktop)", entrypoint)

    def test_manager_is_additive_to_the_existing_web_api_and_script(self):
        from quality_of_life import ui_builds, workspace_ui

        class BaseApi:
            def __init__(self, host):
                self.host = host

            def submit_text(self, text, confirmed=False):
                return {"text": text, "confirmed": confirmed}

        desktop = type("Desktop", (), {})()
        desktop.JarvisWebApi = BaseApi
        desktop.TEXT_INPUT_SCRIPT = "ORIGINAL_COMMAND_SURFACE"
        workspace_ui.install(desktop)
        ui_builds.install(desktop)

        self.assertIn("ORIGINAL_COMMAND_SURFACE", desktop.TEXT_INPUT_SCRIPT)
        self.assertIn("jarvis-workspace-shell", desktop.TEXT_INPUT_SCRIPT)
        self.assertIn("UI BUILD GALLERY", desktop.TEXT_INPUT_SCRIPT)
        self.assertTrue(hasattr(desktop.JarvisWebApi, "submit_text"))
        self.assertTrue(hasattr(desktop.JarvisWebApi, "ui_builds_catalog"))

    def test_manager_script_is_valid_javascript_when_node_is_available(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed on this runner")
        script_path = Path(self.id().replace(".", "_") + ".js")
        try:
            script_path.write_text(build_manager_script(), encoding="utf-8")
            completed = subprocess.run(
                [node, "--check", str(script_path)],
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        finally:
            script_path.unlink(missing_ok=True)

    def test_manager_script_exposes_catalog_save_switch_and_rollback(self):
        script = build_manager_script()
        for token in (
            "ui_builds_catalog",
            "ui_builds_active",
            "ui_builds_activate",
            "ui_builds_save",
            "ui_builds_rollback",
            "UI BUILD GALLERY",
            "NEW",
            "ROLLBACK",
            "ctrlKey",
            "jarvis-ui-build-toggle",
        ):
            self.assertIn(token, script)


if __name__ == "__main__":
    unittest.main()
