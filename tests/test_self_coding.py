from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from self_coding.agent import SelfCodingAgent, SelfCodingConfig, SelfCodingError


class SelfCodingTests(unittest.TestCase):
    def make_repo(self, with_remote: bool = False) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fullstack-agent-selfcoding-"))
        subprocess.run(("git", "init", "-b", "main"), cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(("git", "config", "user.name", "Self Coding Test"), cwd=root, check=True)
        subprocess.run(("git", "config", "user.email", "self-coding-test@example.invalid"), cwd=root, check=True)
        (root / "README.md").write_text("seed\n", encoding="utf-8")
        subprocess.run(("git", "add", "README.md"), cwd=root, check=True)
        subprocess.run(("git", "commit", "-m", "seed"), cwd=root, check=True, capture_output=True, text=True)

        if with_remote:
            remote_parent = Path(tempfile.mkdtemp(prefix="fullstack-agent-selfcoding-remote-"))
            remote = remote_parent / "origin.git"
            subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True, text=True)
            subprocess.run(("git", "remote", "add", "origin", str(remote)), cwd=root, check=True)
            subprocess.run(("git", "push", "-u", "origin", "main"), cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(("git", "fetch", "origin", "main"), cwd=root, check=True, capture_output=True, text=True)
        return root

    @staticmethod
    def git(root: Path, *args: str) -> str:
        result = subprocess.run(("git", *args), cwd=root, check=True, capture_output=True, text=True)
        return result.stdout.strip()

    @staticmethod
    def remote_head(root: Path) -> str:
        remote = subprocess.run(
            ("git", "config", "--get", "remote.origin.url"),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        result = subprocess.run(
            ("git", "--git-dir", remote, "rev-parse", "refs/heads/main"),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_dirty_repository_is_rejected(self) -> None:
        root = self.make_repo()
        (root / "dirty.txt").write_text("existing work\n", encoding="utf-8")
        with self.assertRaisesRegex(SelfCodingError, "not clean"):
            SelfCodingAgent(SelfCodingConfig(repo=root)).validate_repo()

    def test_failed_verification_rolls_back_changes(self) -> None:
        root = self.make_repo()
        config = SelfCodingConfig(repo=root, test_commands=((sys.executable, "-c", "raise SystemExit(1)"),))
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "generated.txt").write_text("must disappear\n", encoding="utf-8")  # type: ignore[method-assign]
        with self.assertRaises(SelfCodingError):
            agent.run("make a safe change")
        self.assertFalse((root / "generated.txt").exists())
        self.assertEqual(self.git(root, "status", "--porcelain"), "")
        self.assertEqual(self.git(root, "branch", "--show-current"), "main")

    def test_rollback_failure_is_reported(self) -> None:
        root = self.make_repo()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root))

        def failed_git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(["git", *args], 1, "", "reset failed")

        agent._git = failed_git  # type: ignore[method-assign]
        with self.assertRaisesRegex(SelfCodingError, "reset failed"):
            agent._rollback("deadbeef")

    def test_successful_pass_creates_pending_checkpoint(self) -> None:
        root = self.make_repo()
        config = SelfCodingConfig(repo=root, test_commands=((sys.executable, "-c", "print('ok')"),))
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "verified.txt").write_text("verified\n", encoding="utf-8")  # type: ignore[method-assign]
        checkpoint_id = agent.run("make a verified change")
        checkpoints = agent.list_checkpoints()
        self.assertEqual(len(checkpoints), 1)
        self.assertEqual(checkpoints[0]["checkpoint_id"], checkpoint_id)
        self.assertEqual(checkpoints[0]["state"], "pending")
        self.assertTrue(str(checkpoints[0]["branch"]).startswith("agent/checkpoint/"))
        self.assertEqual(self.git(root, "branch", "--show-current"), str(checkpoints[0]["branch"]))
        self.assertEqual((root / "verified.txt").read_text(encoding="utf-8"), "verified\n")
        self.assertEqual(self.git(root, "log", "-1", "--pretty=%s"), "agent: verified self-coding change")

    def test_self_coding_prompt_requires_repository_wide_coherence(self) -> None:
        root = self.make_repo()
        prompt = SelfCodingAgent._prompt("improve a capability")
        for phrase in (
            "one integrated assistant",
            "capability registry",
            "UI/voice surfaces",
            "packaging implications",
            "existing shared abstractions",
            "integration paths",
            "not declare a feature complete",
        ):
            self.assertIn(phrase, prompt)

    def test_direct_main_publication_is_disabled(self) -> None:
        root = self.make_repo()
        config = SelfCodingConfig(
            repo=root,
            publish_main=True,
            test_commands=((sys.executable, "-c", "print('ok')"),),
        )
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "verified.txt").write_text("verified\n", encoding="utf-8")  # type: ignore[method-assign]
        with self.assertRaisesRegex(SelfCodingError, "Direct main publication is disabled"):
            agent.run("make a verified change")

    def test_legacy_publish_method_is_a_hard_guard(self) -> None:
        root = self.make_repo()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root))
        with self.assertRaisesRegex(SelfCodingError, "Direct main publication is disabled"):
            agent._publish_main("seed", "agent/checkpoint/test")

    def test_pending_checkpoint_can_be_undone(self) -> None:
        root = self.make_repo()
        config = SelfCodingConfig(repo=root, test_commands=((sys.executable, "-c", "print('ok')"),))
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "pending.txt").write_text("discard me\n", encoding="utf-8")  # type: ignore[method-assign]
        checkpoint_id = agent.run("make a pending change")
        self.assertEqual(self.git(root, "branch", "--show-current").startswith("agent/checkpoint/"), True)

        self.assertEqual(agent.undo_checkpoint(checkpoint_id), "undone")
        self.assertFalse((root / "pending.txt").exists())
        self.assertEqual(self.git(root, "branch", "--show-current"), "main")
        self.assertEqual(agent.list_checkpoints()[0]["state"], "undone")
        self.assertNotIn(checkpoint_id, self.git(root, "branch", "-a"))

    def test_approve_and_undo_are_real_remote_operations(self) -> None:
        root = self.make_repo(with_remote=True)
        config = SelfCodingConfig(repo=root, test_commands=((sys.executable, "-c", "print('ok')"),))
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "approved.txt").write_text("publish me\n", encoding="utf-8")  # type: ignore[method-assign]

        baseline = self.git(root, "rev-parse", "HEAD")
        checkpoint_id = agent.run("make an approved change")
        checkpoint = agent.list_checkpoints()[0]
        self.assertEqual(checkpoint["baseline"], baseline)
        promoted = agent.approve_checkpoint(checkpoint_id)

        self.assertEqual(self.git(root, "branch", "--show-current"), "main")
        self.assertTrue((root / "approved.txt").exists())
        self.assertEqual(self.remote_head(root), promoted)
        self.assertEqual(agent.list_checkpoints()[0]["state"], "approved")

        self.assertEqual(agent.undo_checkpoint(checkpoint_id), "undone")
        self.assertFalse((root / "approved.txt").exists())
        remote_head = self.remote_head(root)
        self.assertNotEqual(remote_head, baseline)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), remote_head)
        self.assertEqual(self.git(root, "diff", "--quiet", baseline, remote_head), "")
        self.assertEqual(agent.list_checkpoints()[0]["state"], "undone")

    def test_approved_checkpoint_refuses_to_undo_unrelated_main_work(self) -> None:
        root = self.make_repo(with_remote=True)
        config = SelfCodingConfig(repo=root, test_commands=((sys.executable, "-c", "print('ok')"),))
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "approved.txt").write_text("publish me\n", encoding="utf-8")  # type: ignore[method-assign]

        checkpoint_id = agent.run("make an approved change")
        agent.approve_checkpoint(checkpoint_id)

        (root / "unrelated.txt").write_text("keep me\n", encoding="utf-8")
        subprocess.run(("git", "add", "unrelated.txt"), cwd=root, check=True)
        subprocess.run(("git", "commit", "-m", "unrelated change"), cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(("git", "push", "origin", "main"), cwd=root, check=True, capture_output=True, text=True)

        with self.assertRaisesRegex(SelfCodingError, "main changed after approval"):
            agent.undo_checkpoint(checkpoint_id)

        self.assertTrue((root / "approved.txt").exists())
        self.assertTrue((root / "unrelated.txt").exists())

    def test_inspect_tool_gap_returns_structured_gap_for_missing_adapter(self) -> None:
        root = self.make_repo()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root))
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


if __name__ == "__main__":
    unittest.main()
