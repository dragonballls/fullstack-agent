import os
import subprocess
import tempfile
import unittest

from quality_of_life.account_access import AccountGrant, AccountProvider, AccountRisk, AccountScope
from quality_of_life.gods_eye import GeoPoint, LocationSnapshot, Place
from quality_of_life.permissions import Capability, CapabilityDenied, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class FakeEye:
    def __init__(self):
        self.place = Place("Tokyo", GeoPoint(35.6762, 139.6503), "tokyo", "fake")
    def search(self, query):
        return [self.place]
    def locate_me(self):
        return LocationSnapshot(GeoPoint(34.1, -117.7), 20, True, "fake")
    def open_place(self, place):
        return {"surface": "gods-eye", "place": place.as_dict()}


class FakeMaintenance:
    def handle(self, request, confirmed=False):
        return {"request": request, "confirmed": confirmed}
    def diagnose(self):
        return {"diagnose": True}


class FakeAccounts:
    def __init__(self):
        self.grants = (
            AccountGrant(
                AccountProvider.GITHUB,
                "primary",
                (AccountScope("repo.fork", "Create a fork", AccountRisk.WRITE),),
            ),
        )
    def list_accounts(self):
        return self.grants


class FakeGitHubClient:
    def __init__(self):
        self.calls = []
    def fork_repository(self, repository, **kwargs):
        self.calls.append((repository, kwargs))
        return {"full_name": "primary/example", "html_url": "https://github.com/primary/example", "clone_url": "https://github.com/primary/example.git"}


class JarvisRuntimeTests(unittest.TestCase):
    def test_runtime_exposes_all_capability_tools_and_dispatches_gods_eye(self):
        policy = CapabilityPolicy(frozenset({Capability.LOCATION_READ}))
        runtime = JarvisRuntime(policy, factories={"gods_eye": lambda: FakeEye()})
        names = set(runtime.available_tools())
        self.assertTrue({"computer", "screen", "browser", "clipboard", "windows", "background", "cloud_router", "gods_eye", "windows_maintenance", "account_access"} <= names)
        places = runtime.dispatch(Capability.LOCATION_READ, "gods_eye.search", query="Tokyo")
        self.assertEqual(places[0].name, "Tokyo")

    def test_runtime_defaults_cloud_router_to_omniroute(self):
        old = {name: os.environ.get(name) for name in (
            "JARVIS_CLOUD_BASE_URL", "JARVIS_CLOUD_MODEL", "JARVIS_OMNIROUTE_ENABLED", "JARVIS_PRISM_ENABLED"
        )}
        try:
            for name in old:
                os.environ.pop(name, None)
            runtime = JarvisRuntime(CapabilityPolicy())
            router = runtime._tool("cloud_router")
            self.assertEqual(len(router.targets), 1)
            self.assertEqual(router.targets[0].name, "omniroute")
            self.assertEqual(router.targets[0].base_url, "http://127.0.0.1:20128/v1")
            self.assertEqual(router.targets[0].model, "auto")
            self.assertEqual(router.targets[0].api_key_env, "OMNIROUTE_API_KEY")
        finally:
            for name, value in old.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_runtime_adds_prism_target_when_explicitly_enabled(self):
        old = {name: os.environ.get(name) for name in (
            "JARVIS_CLOUD_BASE_URL", "JARVIS_CLOUD_MODEL", "JARVIS_OMNIROUTE_ENABLED", "JARVIS_PRISM_ENABLED", "JARVIS_PRISM_SESSION"
        )}
        with tempfile.NamedTemporaryFile(suffix=".json") as session:
            try:
                for name in old:
                    os.environ.pop(name, None)
                os.environ["JARVIS_PRISM_ENABLED"] = "1"
                os.environ["JARVIS_PRISM_SESSION"] = session.name
                runtime = JarvisRuntime(CapabilityPolicy())
                router = runtime._tool("cloud_router")
                self.assertEqual([target.name for target in router.targets], ["prism-astra", "omniroute"])
                self.assertEqual(router.targets[0].base_url, "http://127.0.0.1:8319/v1")
            finally:
                for name, value in old.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
    def test_runtime_self_coding_defaults_to_preview_only(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as state_dir:
            root = os.path.abspath(root_dir)
            subprocess.run(("git", "init", "-b", "main"), cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(("git", "config", "user.name", "Runtime Test"), cwd=root, check=True)
            subprocess.run(("git", "config", "user.email", "runtime-test@example.invalid"), cwd=root, check=True)
            open(os.path.join(root, "README.md"), "w", encoding="utf-8").write("seed\\n")
            subprocess.run(("git", "add", "README.md"), cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(("git", "commit", "-m", "seed"), cwd=root, check=True, capture_output=True, text=True)
            old = {name: os.environ.get(name) for name in ("JARVIS_SELF_CODING_REPO", "JARVIS_SELF_CODING_PUBLISH_MAIN", "JARVIS_SELF_CODING_STATE_DIR")}
            try:
                os.environ["JARVIS_SELF_CODING_REPO"] = root
                os.environ.pop("JARVIS_SELF_CODING_PUBLISH_MAIN", None)
                os.environ["JARVIS_SELF_CODING_STATE_DIR"] = state_dir
                runtime = JarvisRuntime(CapabilityPolicy())
                agent = runtime._tool("self_coding")
                self.assertFalse(agent.config.publish_main)
                self.assertFalse(agent.config.push_branch)
                self.assertEqual(runtime._tool("self_coding").status()["state"], "clean")
            finally:
                for name, value in old.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

    def test_runtime_preserves_deny_by_default(self):
        runtime = JarvisRuntime(CapabilityPolicy(), factories={"gods_eye": FakeEye})
        with self.assertRaises(CapabilityDenied):
            runtime.dispatch(Capability.LOCATION_READ, "gods_eye.locate_me")

    def test_runtime_requires_confirmation_for_mutations(self):
        calls = []
        policy = CapabilityPolicy(frozenset({Capability.MOUSE_CONTROL}))
        fake = type("Computer", (), {"move": lambda self, x, y: calls.append((x, y))})()
        runtime = JarvisRuntime(policy, factories={"computer": lambda: fake})
        with self.assertRaises(PermissionError):
            runtime.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=1, y=2)
        runtime.confirmation = lambda capability, operation: True
        runtime.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=1, y=2)
        self.assertEqual(calls, [(1, 2)])

    def test_read_only_maintenance_diagnosis_has_no_confirmation_gate(self):
        policy = CapabilityPolicy(frozenset({Capability.SYSTEM_DIAGNOSTICS}), require_confirmation=frozenset())
        runtime = JarvisRuntime(policy, factories={"windows_maintenance": lambda: FakeMaintenance()})
        result = runtime.handle_text("diagnose my PC")
        self.assertEqual(result["intent"].kind, "windows_maintenance")
        self.assertEqual(result["result"], {"diagnose": True})

    def test_maintenance_mutation_still_uses_confirmed_capability(self):
        policy = CapabilityPolicy(frozenset({Capability.SYSTEM_MAINTENANCE}))
        runtime = JarvisRuntime(policy, factories={"windows_maintenance": lambda: FakeMaintenance()})
        with self.assertRaises(PermissionError):
            runtime.handle_text("fix my PC")
        runtime.confirmation = lambda capability, operation: True
        result = runtime.handle_text("fix my PC")
        self.assertEqual(result["result"]["confirmed"], False)

    def test_background_methods_are_safe_and_idempotent(self):
        runtime = JarvisRuntime(CapabilityPolicy())
        self.assertTrue(runtime.enter_background())
        self.assertEqual(runtime.background_status()["state"], "background")
        self.assertFalse(runtime.enter_background())
        self.assertTrue(runtime.enter_foreground())
        self.assertEqual(runtime.background_status()["state"], "foreground")
        self.assertFalse(runtime.enter_foreground())


if __name__ == "__main__":
    unittest.main()
