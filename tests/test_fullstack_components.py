from pathlib import Path
import unittest
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "fetch-fullstack-components.py"
SPEC = importlib.util.spec_from_file_location("fetch_fullstack_components", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FullstackComponentTests(unittest.TestCase):
    def test_all_required_components_have_pinned_revisions(self):
        self.assertEqual(set(MODULE.COMPONENTS), {
            "backtalk", "ai-visualizer", "barehands", "ai-memory-vault"
        })
        for meta in MODULE.COMPONENTS.values():
            self.assertRegex(meta["repo"], r"^jaredrhod/")
            self.assertRegex(meta["commit"], r"^[0-9a-f]{40}$")

    def test_manifest_is_valid(self):
        self.assertEqual(MODULE.validate_component_manifest(MODULE.COMPONENTS), [])


if __name__ == "__main__":
    unittest.main()
