import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quality_of_life.external_integrations import (
    EXTERNAL_SKILLS,
    ExternalSkillRegistry,
    HindsightMemoryBridge,
    OptionalAgentLauncher,
    external_skill_status,
    load_skill_text,
)


class ExternalIntegrationTests(unittest.TestCase):
    def test_catalog_contains_all_requested_projects(self):
        names = {spec.name for spec in EXTERNAL_SKILLS}
        self.assertEqual(
            names,
            {
                "archify",
                "go-modern-guidelines",
                "openclaude",
                "scientific-agent-skills",
                "omarchy",
                "hindsight",
                "radiant",
            },
        )

    def test_registry_is_case_and_whitespace_normalized(self):
        registry = ExternalSkillRegistry()
        self.assertEqual(registry.get("  ARCHIFY  ").name, "archify")

    def test_hindsight_is_disabled_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            bridge = HindsightMemoryBridge()
        self.assertFalse(bridge.configured)
        with self.assertRaises(RuntimeError):
            bridge.recall("jarvis", "test")

    def test_hindsight_recall_bounds_limit_and_posts_json(self):
        bridge = HindsightMemoryBridge("http://127.0.0.1:8888")
        self.assertTrue(bridge.configured)
        seen = {}

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self):
                return b'{"ok": true}'

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["method"] = request.method
            seen["body"] = request.data.decode("utf-8")
            seen["timeout"] = timeout
            return Response()

        with patch("quality_of_life.external_integrations.urlopen", fake_urlopen):
            result = bridge.recall("jarvis", "memory", limit=999)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(seen["url"], "http://127.0.0.1:8888/v1/recall")
        self.assertEqual(seen["method"], "POST")
        self.assertIn('"limit": 50', seen["body"])

    def test_launcher_never_uses_shell(self):
        launcher = OptionalAgentLauncher("openclaude")
        completed = type("Completed", (), {"stdout": "1.2.3\n", "stderr": ""})()
        with patch.object(launcher, "available", True), patch(
            "quality_of_life.external_integrations.subprocess.run", return_value=completed
        ) as run:
            self.assertEqual(launcher.version(), "1.2.3")
        kwargs = run.call_args.kwargs
        self.assertFalse(kwargs["shell"])
        self.assertEqual(run.call_args.args[0], ["openclaude", "--version"])

    def test_skill_text_has_a_hard_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skill.md"
            path.write_text("hello", encoding="utf-8")
            self.assertEqual(load_skill_text(path), "hello")
            with self.assertRaises(ValueError):
                load_skill_text(path, max_bytes=2)

    def test_status_is_safe_and_does_not_expose_configuration_values(self):
        with patch.dict(os.environ, {"JARVIS_HINDSIGHT_URL": "http://secret.example"}, clear=True):
            status = external_skill_status()
        raw = repr(status)
        self.assertNotIn("secret.example", raw)
        self.assertTrue({item["name"] for item in status} >= {"archify", "hindsight", "omarchy"})


if __name__ == "__main__":
    unittest.main()
