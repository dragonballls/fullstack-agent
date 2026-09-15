from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from quality_of_life.applications import ApplicationManager, ApplicationError, InstalledApplication
from quality_of_life.browser_registry import BrowserRegistry, BrowserUnavailable
from quality_of_life.capabilities import OPERATION_CATALOG, OperationRisk, operation
from quality_of_life.files import FileController, FilesystemError
from quality_of_life.intents import parse_intent
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.processes import ProcessInfo, ProcessManager, ProcessControlError


class UniversalCapabilityTests(unittest.TestCase):
    def test_catalog_contains_core_families(self):
        names = {item.name for item in OPERATION_CATALOG}
        self.assertIn("browser.open_url", names)
        self.assertIn("files.delete", names)
        self.assertIn("applications.uninstall", names)
        self.assertEqual(operation("applications.uninstall").risk, OperationRisk.DESTRUCTIVE)

    def test_browser_aliases_resolve_without_host_access(self):
        root = Path(tempfile.mkdtemp())
        edge = root / "msedge.exe"
        edge.write_text("stub", encoding="utf-8")
        registry = BrowserRegistry(lambda: {"edge": ("Microsoft Edge", "chromium", (edge,))})
        self.assertEqual(registry.resolve("MS Edge").id, "edge")
        with self.assertRaises(BrowserUnavailable):
            registry.resolve("Opera GX")

    def test_file_mutations_are_policy_and_target_gated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = CapabilityPolicy(allowed=frozenset({Capability.FILE_READ, Capability.FILE_WRITE, Capability.FILE_DELETE}))
            files = FileController(allowed, roots=(root,))
            target = root / "a.txt"
            files.write_text(target, "hello")
            self.assertEqual(files.read_text(target), "hello")
            with self.assertRaises(FilesystemError):
                files.info(Path(tempfile.gettempdir()).parent)
            self.assertTrue(files.delete(target))
            self.assertFalse(target.exists())

    def test_application_uninstall_requires_confirmation_and_safe_executable(self):
        app = InstalledApplication("id", "Example App", "Example Publisher", "1", r"C:\Tools\uninstall.exe /x", "test")
        policy = CapabilityPolicy(allowed=frozenset({Capability.APP_READ, Capability.APP_WRITE}))
        manager = ApplicationManager(policy, provider=lambda: (app,))
        with self.assertRaises(PermissionError):
            manager.uninstall("id", confirmed=False)
        with self.assertRaises(ApplicationError):
            manager.uninstall("id", confirmed=True)

    def test_protected_process_cannot_be_stopped(self):
        policy = CapabilityPolicy(allowed=frozenset({Capability.PROCESS_READ, Capability.PROCESS_CONTROL}))
        manager = ProcessManager(policy, process_provider=lambda: (ProcessInfo(1, "lsass.exe", "C:\\Windows\\System32\\lsass.exe"),))
        with self.assertRaises(ProcessControlError):
            manager.stop(1, confirmed=True)

    def test_intents_select_browser_before_generic_open_place(self):
        self.assertEqual(parse_intent("Open Opera GX").kind, "browser_open")
        self.assertEqual(parse_intent("Open Edge and go to https://example.com").arguments["browser"], "Edge")
        self.assertEqual(parse_intent("Uninstall Discord").kind, "application_uninstall")
        self.assertEqual(parse_intent("Delete file notes.txt").kind, "file_delete")


if __name__ == "__main__":
    unittest.main()
