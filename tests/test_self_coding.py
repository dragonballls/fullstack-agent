from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from self_coding.agent import SelfCodingAgent, SelfCodingConfig, SelfCodingError


class SelfCodingTests(unittest.TestCase):
    def make_repo(self, with_remote: bool = False) -> tuple[Path, Path | None]:
        root = Path(tempfile.mkdtemp(prefix="fullstack-agent-selfcoding-"))
        remote = None
        subprocess.run(("git", "init", "-b", "main"), cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(("git", "config", "user.name", "Self Coding Test"), cwd=root, check=True)
        subprocess.run(("git", "config", "user.email", "self-coding-test@example.invalid"), cwd=root, check=True)
        (root / "README.md").write_text("seed\n", encoding="utf-8")
        subprocess.run(("git", "add", "README.md"), cwd=root, check=True)
        subprocess.run(("git", "commit", "-m", "seed"), cwd=root, check=True, capture_output=True, text=True)
        if with_remote:
            remote = Path(tempfile.mkdtemp(prefix="fullstack-agent-selfcoding-remote-"))
            subprocess.run(("git", "init", "--bare", str(remote)), cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(("git", "remote", "add", "origin", str(remote)), cwd=root, check=True)
            subprocess.run(("git", "push", "-u", "origin", "main"), cwd=root, check=True, capture_output=True, text=True)
        return root, remote

    def state_dir(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fullstack-agent-selfcoding-state-"))

    def test_dirty_repository_is_rejected(self) -> None:
        root, _ = self.make_repo()
        (root / "dirty.txt").write_text("existing work\n", encoding="utf-8")
        with self.assertRaisesRegex(SelfCodingError, "not clean"):
            SelfCodingAgent(SelfCodingConfig(repo=root)).validate_repo()

    def test_failed_verification_rolls_back_changes(self) -> None:
        root, _ = self.make_repo()
        config = SelfCodingConfig(repo=root, state_dir=self.state_dir(), test_commands=((sys.executable, "-c", "raise SystemExit(1)"),))
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "generated.txt").write_text("must disappear\n", encoding="utf-8")  # type: ignore[method-assign]
        with self.assertRaises(SelfCodingError):
            agent.run("make a safe change")
        self.assertFalse((root / "generated.txt").exists())
        status = subprocess.run(("git", "status", "--porcelain"), cwd=root, check=True, capture_output=True, text=True)
        self.assertEqual(status.stdout, "")

    def test_rollback_failure_is_reported(self) -> None:
        root, _ = self.make_repo()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root, state_dir=self.state_dir()))

        def failed_git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(["git", *args], 1, "", "reset failed")

        agent._git = failed_git  # type: ignore[method-assign]
        with self.assertRaisesRegex(SelfCodingError, "reset failed"):
            agent._rollback("deadbeef")

    def test_successful_pass_is_committed(self) -> None:
        root, _ = self.make_repo()
        config = SelfCodingConfig(repo=root, state_dir=self.state_dir(), test_commands=((sys.executable, "-c", "print('ok')"),))
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "verified.txt").write_text("verified\n", encoding="utf-8")  # type: ignore[method-assign]
        branch = agent.run("make a verified change")
        self.assertTrue(branch.startswith("agent/self-code/"))
        self.assertEqual((root / "verified.txt").read_text(encoding="utf-8"), "verified\n")
        log = subprocess.run(("git", "log", "-1", "--pretty=%s"), cwd=root, check=True, capture_output=True, text=True)
        self.assertEqual(log.stdout.strip(), "agent: verified self-coding change")

    def test_publish_main_is_opt_in_and_requires_remote_baseline_match(self) -> None:
        root, _ = self.make_repo()
        config = SelfCodingConfig(repo=root, publish_main=True, state_dir=self.state_dir())
        agent = SelfCodingAgent(config)
        agent._git = lambda *args: subprocess.CompletedProcess(["git", *args], 0, "different\n", "")  # type: ignore[method-assign]
        with self.assertRaisesRegex(SelfCodingError, "remote main"):
            agent._publish_main("seed", "agent/self-code/test", "main")

    def test_inspect_tool_gap_returns_structured_gap_for_missing_adapter(self) -> None:
        root, _ = self.make_repo()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root, state_dir=self.state_dir()))
        gap = agent.inspect_tool_gap("the requested tool returned an unsupported operation because no adapter is registered")
        self.assertIsNotNone(gap)
        self.assertEqual(gap.kind, "tool_capability")
        self.assertEqual(gap.operation, "unknown")

    def test_propose_tool_extension_is_machine_readable(self) -> None:
        root = self.make_repo()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root))
        gap = agent.inspect_tool_gap("the requested tool returned an unsupported operation because no adapter is registered")
        proposal = agent.propose_tool_extension("connect the missing provider", gap)
        self.assertEqual(proposal["kind"], "tool_extension")
        self.assertEqual(proposal["tests_required"], True)
        self.assertIn("operation", proposal)


    def test_successful_pass_creates_reversible_preview(self) -> None:
        root, _ = self.make_repo()
        state = self.state_dir()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root, state_dir=state, test_commands=((sys.executable, "-c", "print('ok')"),)))
        agent._invoke_backend = lambda goal: (root / "preview.txt").write_text("preview\n", encoding="utf-8")  # type: ignore[method-assign]
        branch = agent.run("add a preview-safe change")
        self.assertTrue(branch.startswith("agent/self-code/"))
        self.assertEqual(self._git_out(root, "branch", "--show-current"), branch)
        status = agent.status()
        self.assertEqual(status["state"], "preview")
        self.assertEqual(status["branch"], branch)
        self.assertTrue((root / "preview.txt").exists())

    def test_undo_preview_returns_to_main_and_clears_active_preview(self) -> None:
        root, _ = self.make_repo()
        state = self.state_dir()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root, state_dir=state, test_commands=((sys.executable, "-c", "print('ok')"),)))
        agent._invoke_backend = lambda goal: (root / "preview.txt").write_text("preview\n", encoding="utf-8")  # type: ignore[method-assign]
        agent.run("make a preview")
        result = agent.undo(push=False)
        self.assertEqual(result, "main")
        self.assertEqual(self._git_out(root, "branch", "--show-current"), "main")
        self.assertFalse((root / "preview.txt").exists())
        self.assertEqual(agent.status()["state"], "clean")

    def test_approve_then_undo_published_checkpoint_is_reversible(self) -> None:
        root, _ = self.make_repo(with_remote=True)
        state = self.state_dir()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root, state_dir=state, test_commands=((sys.executable, "-c", "print('ok')"),)))
        agent._invoke_backend = lambda goal: (root / "approved.txt").write_text("approved\n", encoding="utf-8")  # type: ignore[method-assign]
        agent.run("make an approved change")
        self.assertEqual(agent.status()["state"], "preview")
        self.assertEqual(agent.approve(push=True), "main")
        self.assertEqual(agent.status()["state"], "published")
        self.assertTrue((root / "approved.txt").exists())
        self.assertEqual(self._git_out(root, "rev-parse", "refs/remotes/origin/main"), self._git_out(root, "rev-parse", "HEAD"))

        self.assertEqual(agent.undo(push=True), "main")
        self.assertEqual(agent.status()["state"], "clean")
        self.assertFalse((root / "approved.txt").exists())
        self.assertEqual(self._git_out(root, "rev-parse", "refs/remotes/origin/main"), self._git_out(root, "rev-parse", "HEAD"))

    @staticmethod
    def _git_out(root: Path, *args: str) -> str:
        result = subprocess.run(("git", *args), cwd=root, check=True, capture_output=True, text=True)
        return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()
