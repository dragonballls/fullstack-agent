"""Safe, provider-agnostic autonomous coding loop.

The module limits an agent to a clean Git repository, verifies every coding
pass, keeps successful work on a reversible preview branch, and never promotes
to the original branch unless explicitly requested.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .checkpoints import CheckpointRecord, CheckpointStore


class SelfCodingError(RuntimeError):
    """Raised when a self-coding run cannot safely proceed."""


@dataclass(frozen=True)
class ToolGap:
    """Structured description of a missing broker/tool capability."""

    kind: str
    operation: str
    reason: str


@dataclass(frozen=True)
class SelfCodingConfig:
    repo: Path
    test_commands: tuple[tuple[str, ...], ...] = ((sys.executable, "-m", "unittest", "discover", "-s", "tests"),)
    timeout_seconds: int = 900
    push_branch: bool = False
    publish_main: bool = False
    max_passes: int = 1
    backend: str = "auto"
    state_dir: Path | None = None


class SelfCodingAgent:
    """Run a cloud coding agent with technical rollback and user-controlled promotion."""

    def __init__(self, config: SelfCodingConfig) -> None:
        self.config = config
        self.repo = config.repo.resolve()
        if not self.repo.is_dir():
            raise SelfCodingError(f"Repository does not exist: {self.repo}")
        self.checkpoints = CheckpointStore(config.state_dir)

    def _run(self, args: Sequence[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                list(args),
                cwd=self.repo,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout or self.config.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise SelfCodingError(f"Required executable is missing: {args[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise SelfCodingError(f"Command timed out: {' '.join(args)}") from exc

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self._run(("git", *args))

    def validate_repo(self) -> None:
        if not (self.repo / ".git").exists():
            raise SelfCodingError("Self-coding requires a real Git clone with a .git directory.")
        result = self._git("rev-parse", "--show-toplevel")
        if result.returncode != 0 or Path(result.stdout.strip()).resolve() != self.repo:
            raise SelfCodingError("Git repository root does not match the configured agent home.")

        status = self._git("status", "--porcelain")
        if status.returncode != 0:
            raise SelfCodingError(status.stderr.strip() or "Unable to inspect Git status.")
        if status.stdout.strip():
            raise SelfCodingError("Repository is not clean; refusing to overwrite existing work.")

    def inspect_tool_gap(self, goal: str) -> ToolGap | None:
        """Detect explicit broker failure language without inferring permissions."""
        normalized = " ".join(goal.casefold().split())
        markers = (
            "unsupported operation",
            "no adapter is registered",
            "unknown capability operation",
            "tool capability is unavailable",
            "missing adapter",
        )
        if any(marker in normalized for marker in markers):
            return ToolGap("tool_capability", "unknown", goal.strip())
        return None

    def propose_tool_extension(self, goal: str, gap: ToolGap | None) -> dict[str, object]:
        """Create a machine-readable repository task; never grants or activates access."""
        if gap is None:
            raise SelfCodingError("A concrete tool gap is required before proposing an extension.")
        return {
            "kind": "tool_extension",
            "operation": gap.operation,
            "reason": gap.reason,
            "goal": goal.strip(),
            "adapter_target": "quality_of_life/",
            "tests_required": True,
            "verification": "python -m unittest discover -s tests -p 'test_*.py' -v",
            "activation_requires": ("declared capability", "policy approval", "passing tests"),
        }

    def _current_branch(self) -> str:
        result = self._git("symbolic-ref", "--quiet", "--short", "HEAD")
        if result.returncode != 0 or not result.stdout.strip():
            raise SelfCodingError("Self-coding requires a named Git branch; detached HEAD is not supported.")
        return result.stdout.strip()

    def _new_branch(self) -> tuple[str, str, str]:
        original = self._current_branch()
        head = self._git("rev-parse", "HEAD")
        if head.returncode != 0:
            raise SelfCodingError("Unable to read the current Git commit.")
        baseline = head.stdout.strip()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch = f"agent/self-code/{stamp}"
        checkpoint_tag = f"agent/self-code/checkpoint/{stamp}"
        created = self._git("switch", "-c", branch)
        if created.returncode != 0:
            raise SelfCodingError(created.stderr.strip() or "Unable to create self-coding branch.")
        tagged = self._git("tag", checkpoint_tag, baseline)
        if tagged.returncode != 0:
            self._git("switch", original)
            self._git("branch", "-D", branch)
            raise SelfCodingError(tagged.stderr.strip() or "Unable to create the self-coding checkpoint tag.")
        return branch, baseline, original

    def _publish_main(self, baseline: str, branch: str, original_branch: str) -> str:
        fetched = self._git("fetch", "origin", "main")
        if fetched.returncode != 0:
            raise SelfCodingError(fetched.stderr.strip() or "Unable to fetch remote main")
        remote = self._git("rev-parse", "refs/remotes/origin/main")
        if remote.returncode != 0:
            raise SelfCodingError(remote.stderr.strip() or "Unable to inspect remote main")
        if remote.stdout.strip() != baseline:
            raise SelfCodingError("remote main changed after self-coding started; refusing to publish")
        if original_branch != "main":
            raise SelfCodingError("Automatic publication is restricted to the main branch.")
        switched = self._git("switch", "main")
        if switched.returncode != 0:
            raise SelfCodingError(switched.stderr.strip() or "Unable to switch to main")
        merged = self._git("merge", "--ff-only", branch)
        if merged.returncode != 0:
            raise SelfCodingError(merged.stderr.strip() or "Unable to fast-forward main")
        pushed = self._git("push", "origin", "main")
        if pushed.returncode != 0:
            raise SelfCodingError(pushed.stderr.strip() or "Unable to publish verified self-coding change to main")
        return self._git("rev-parse", "HEAD").stdout.strip()

    @staticmethod
    def _prompt(goal: str) -> str:
        return f"""You are the implementation agent for this repository.

Goal: {goal}

Rules:
- Work ONLY inside the supplied Git repository.
- Read the existing code and documentation before changing anything.
- Preserve existing behavior unless the goal requires a change.
- Do not access, print, copy, or modify credentials, tokens, private keys, browser profiles, or files outside the repository.
- Do not weaken authentication, permissions, safety checks, tests, or rollback logic.
- Prefer small, reversible changes.
- Treat a passing test suite as technical verification, not proof that the user will like a visual or behavioral change.
- Add or update tests for every behavioral change.
- Run the repository's relevant tests before declaring success.
- Never claim success when tests fail.
- Do not commit generated secrets or machine-specific configuration.

Implement the goal directly, then leave the repository clean and testable."""

    def _find_backend(self) -> str:
        requested = self.config.backend.lower()
        if requested != "auto":
            if shutil.which(requested) is None:
                raise SelfCodingError(f"Configured coding backend is unavailable: {requested}")
            return requested
        for candidate in ("claude", "codex", "gemini"):
            if shutil.which(candidate):
                return candidate
        raise SelfCodingError("No supported cloud coding CLI was found (claude, codex, or gemini).")

    def _invoke_backend(self, goal: str) -> None:
        backend = self._find_backend()
        prompt = self._prompt(goal)
        if backend == "claude":
            args = (backend, "-p", prompt)
        elif backend == "codex":
            args = (backend, "exec", prompt)
        else:
            args = (backend, "-p", prompt)
        result = self._run(args)
        if result.returncode != 0:
            raise SelfCodingError(result.stderr.strip() or result.stdout.strip() or f"{backend} exited with code {result.returncode}.")

    def _verify(self) -> None:
        for command in self.config.test_commands:
            result = self._run(command)
            if result.returncode != 0:
                output = (result.stdout + "\n" + result.stderr).strip()
                raise SelfCodingError(f"Verification failed for {' '.join(command)}.\n{output[-12000:]}")
        status = self._git("status", "--porcelain")
        if status.returncode != 0:
            raise SelfCodingError("Unable to verify the post-test Git state.")

    def _rollback(self, baseline: str) -> None:
        reset = self._git("reset", "--hard", baseline)
        if reset.returncode != 0:
            raise SelfCodingError(reset.stderr.strip() or "Rollback failed while resetting the repository.")
        clean = self._git("clean", "-fd")
        if clean.returncode != 0:
            raise SelfCodingError(clean.stderr.strip() or "Rollback failed while cleaning untracked files.")
        status = self._git("status", "--porcelain")
        if status.returncode != 0:
            raise SelfCodingError(status.stderr.strip() or "Rollback verification failed while checking Git status.")
        if status.stdout.strip():
            raise SelfCodingError("Rollback verification failed: repository is still dirty.")

    def _cleanup_failed_run(self, baseline: str, branch: str, original_branch: str, checkpoint_tag: str) -> None:
        self._rollback(baseline)
        switched = self._git("switch", original_branch)
        if switched.returncode != 0:
            raise SelfCodingError(switched.stderr.strip() or "Rollback succeeded but original branch could not be restored.")
        deleted = self._git("branch", "-D", branch)
        if deleted.returncode != 0:
            raise SelfCodingError(deleted.stderr.strip() or "Rollback succeeded but preview branch could not be removed.")
        self._git("tag", "-d", checkpoint_tag)

    def run(self, goal: str) -> str:
        """Create a verified preview; publication is intentionally a separate action."""
        if not goal.strip():
            raise SelfCodingError("A non-empty coding goal is required.")
        if self.config.max_passes < 1:
            raise SelfCodingError("max_passes must be at least 1.")
        if self.config.publish_main and self.config.push_branch:
            raise SelfCodingError("publish_main and push_branch cannot be combined")

        self.validate_repo()
        if self.checkpoints.active_preview(self.repo) is not None:
            raise SelfCodingError("An unapproved self-coding preview already exists; approve or undo it before starting another.")

        branch, baseline, original_branch = self._new_branch()
        checkpoint_tag = f"agent/self-code/checkpoint/{branch.rsplit('/', 1)[-1]}"
        checkpoint_id = branch.rsplit("/", 1)[-1]
        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            repo=str(self.repo),
            original_branch=original_branch,
            baseline_commit=baseline,
            preview_branch=branch,
            checkpoint_tag=checkpoint_tag,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            for _ in range(self.config.max_passes):
                self._invoke_backend(goal)
                self._verify()
                status = self._git("status", "--porcelain")
                if not status.stdout.strip():
                    raise SelfCodingError("Coding agent completed without producing a change.")
                staged = self._git("add", "--all")
                if staged.returncode != 0:
                    raise SelfCodingError(staged.stderr.strip() or "Unable to stage changes.")
                committed = self._git("commit", "-m", "agent: verified self-coding change")
                if committed.returncode != 0:
                    raise SelfCodingError(committed.stderr.strip() or "Unable to commit verified changes.")
                commit = self._git("rev-parse", "HEAD")
                if commit.returncode != 0:
                    raise SelfCodingError(commit.stderr.strip() or "Unable to record verified self-coding commit.")
                record.commits.append(commit.stdout.strip())

            if self.config.publish_main:
                published_head = self._publish_main(baseline, branch, original_branch)
                record.status = "published"
                record.published_head = published_head
                self.checkpoints.add(record)
                self._git("branch", "-D", branch)
                return original_branch

            self.checkpoints.add(record)
            if self.config.push_branch:
                pushed = self._git("push", "-u", "origin", branch)
                if pushed.returncode != 0:
                    raise SelfCodingError(pushed.stderr.strip() or "Unable to push self-coding branch")
            return branch
        except Exception:
            self._cleanup_failed_run(baseline, branch, original_branch, checkpoint_tag)
            raise

    def approve(self, *, push: bool = True) -> str:
        """Promote the active preview to main only after an explicit approval."""
        self.validate_repo()
        record = self.checkpoints.active_preview(self.repo)
        if record is None:
            raise SelfCodingError("There is no active self-coding preview to approve.")
        if self._current_branch() != record.preview_branch:
            raise SelfCodingError("The active self-coding preview is not the current branch.")
        self._verify()
        status = self._git("status", "--porcelain")
        if status.stdout.strip():
            raise SelfCodingError("The preview changed after verification; refusing to promote dirty work.")

        if record.original_branch != "main":
            raise SelfCodingError("Preview promotion is restricted to the main branch for the desktop product.")
        fetched = self._git("fetch", "origin", "main")
        if fetched.returncode != 0:
            raise SelfCodingError(fetched.stderr.strip() or "Unable to refresh remote main before approval.")
        remote = self._git("rev-parse", "refs/remotes/origin/main")
        if remote.returncode != 0 or remote.stdout.strip() != record.baseline_commit:
            raise SelfCodingError("main changed since the preview checkpoint; refusing to promote it.")
        local_main = self._git("rev-parse", "refs/heads/main")
        if local_main.returncode != 0 or local_main.stdout.strip() != record.baseline_commit:
            raise SelfCodingError("local main changed since the preview checkpoint; refusing to promote it.")

        switched = self._git("switch", "main")
        if switched.returncode != 0:
            raise SelfCodingError(switched.stderr.strip() or "Unable to switch back to main for approval.")
        merged = self._git("merge", "--ff-only", record.preview_branch)
        if merged.returncode != 0:
            raise SelfCodingError(merged.stderr.strip() or "Unable to promote the verified preview.")
        published_head = self._git("rev-parse", "HEAD")
        if published_head.returncode != 0:
            raise SelfCodingError("Unable to record the promoted commit.")
        published = published_head.stdout.strip()
        if push:
            pushed = self._git("push", "origin", "main")
            if pushed.returncode != 0:
                raise SelfCodingError(pushed.stderr.strip() or "Preview was promoted locally, but pushing main failed.")

        self.checkpoints.update(record.checkpoint_id, status="published", published_head=published)
        self._git("branch", "-D", record.preview_branch)
        return "main"

    def undo(self, *, push: bool = True) -> str:
        """Undo the active preview or the latest published self-coding checkpoint."""
        self.validate_repo()
        preview = self.checkpoints.active_preview(self.repo)
        if preview is not None:
            if self._current_branch() != preview.preview_branch:
                raise SelfCodingError("The active self-coding preview is not the current branch.")
            switched = self._git("switch", preview.original_branch)
            if switched.returncode != 0:
                raise SelfCodingError(switched.stderr.strip() or "Unable to restore the original branch.")
            deleted = self._git("branch", "-D", preview.preview_branch)
            if deleted.returncode != 0:
                raise SelfCodingError(deleted.stderr.strip() or "Unable to remove the self-coding preview branch.")
            self._git("tag", "-d", preview.checkpoint_tag)
            self.checkpoints.update(preview.checkpoint_id, status="reverted")
            return preview.original_branch

        published = self.checkpoints.latest_published(self.repo)
        if published is None:
            raise SelfCodingError("There is no self-coding checkpoint available to undo.")
        if published.original_branch != "main" or self._current_branch() != "main":
            raise SelfCodingError("Published self-coding undo is restricted to main.")
        status = self._git("status", "--porcelain")
        if status.stdout.strip():
            raise SelfCodingError("main must be clean before undoing a self-coding checkpoint.")
        head = self._git("rev-parse", "HEAD")
        if head.returncode != 0:
            raise SelfCodingError(head.stderr.strip() or "Unable to inspect main before undo.")
        original_head = head.stdout.strip()

        commits = list(reversed(published.commits))
        if not commits:
            raise SelfCodingError("The checkpoint contains no self-coding commits to undo.")
        for commit in commits:
            reverted = self._git("revert", "--no-edit", "--no-commit", commit)
            if reverted.returncode != 0:
                self._git("reset", "--hard", original_head)
                raise SelfCodingError(reverted.stderr.strip() or "Unable to construct a safe undo.")
        committed = self._git("commit", "-m", f"agent: undo self-coding checkpoint {published.checkpoint_id}")
        if committed.returncode != 0:
            self._git("reset", "--hard", original_head)
            raise SelfCodingError(committed.stderr.strip() or "Unable to commit the self-coding undo.")
        undo_head = self._git("rev-parse", "HEAD")
        if undo_head.returncode != 0:
            self._git("reset", "--hard", original_head)
            raise SelfCodingError("Unable to record the undo commit.")
        try:
            self._verify()
        except Exception:
            self._git("reset", "--hard", original_head)
            raise
        if push:
            pushed = self._git("push", "origin", "main")
            if pushed.returncode != 0:
                raise SelfCodingError(pushed.stderr.strip() or "Undo committed locally, but pushing main failed.")
        self.checkpoints.update(published.checkpoint_id, status="reverted", revert_commit=undo_head.stdout.strip())
        return "main"

    def status(self) -> dict[str, object]:
        """Return the user's reversible self-coding state without touching the repository."""
        preview = self.checkpoints.active_preview(self.repo)
        if preview is not None:
            return {
                "state": "preview",
                "checkpoint_id": preview.checkpoint_id,
                "branch": preview.preview_branch,
                "baseline": preview.baseline_commit,
                "commits": list(preview.commits),
            }
        published = self.checkpoints.latest_published(self.repo)
        if published is not None:
            return {
                "state": "published",
                "checkpoint_id": published.checkpoint_id,
                "branch": published.original_branch,
                "published_head": published.published_head,
                "commits": list(published.commits),
                "revert_commit": published.revert_commit,
            }
        return {"state": "clean"}

