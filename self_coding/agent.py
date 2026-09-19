"""Safe, provider-agnostic autonomous coding loop.

The module limits an agent to a clean Git repository, requires verification
after every coding pass, and restores the exact starting commit on failure.

Successful work is never published directly to main. Every successful run
becomes a named pending checkpoint. Promotion and undo are explicit runtime
actions with durable local state under .git/jarvis-checkpoints/.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


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
    # Retained for source compatibility, but direct main publication is disabled.
    # Use approve_checkpoint() for an explicit promotion action.
    publish_main: bool = False
    max_passes: int = 1
    backend: str = "auto"


@dataclass(frozen=True)
class _Checkpoint:
    checkpoint_id: str
    branch: str
    baseline: str
    base_branch: str
    commits: tuple[str, ...]
    created_at: str
    state: str
    promoted_sha: str | None = None
    undo_commits: tuple[str, ...] = ()


class SelfCodingAgent:
    """Run a cloud coding agent against this repository with Git guardrails."""

    def __init__(self, config: SelfCodingConfig) -> None:
        self.config = config
        self.repo = config.repo.resolve()
        if not self.repo.is_dir():
            raise SelfCodingError(f"Repository does not exist: {self.repo}")

    @property
    def _checkpoint_dir(self) -> Path:
        return self.repo / ".git" / "jarvis-checkpoints"

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

    def _current_branch(self) -> str:
        result = self._git("rev-parse", "--abbrev-ref", "HEAD")
        if result.returncode != 0:
            raise SelfCodingError(result.stderr.strip() or "Unable to determine the current Git branch.")
        branch = result.stdout.strip()
        if not branch or branch == "HEAD":
            raise SelfCodingError("Self-coding requires an attached Git branch; detached HEAD is not allowed.")
        return branch

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

        self._current_branch()

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

    @staticmethod
    def _goal_slug(goal: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", goal.casefold()).strip("-")
        return (slug[:36].rstrip("-") or "change")

    def _new_branch(self, goal: str) -> tuple[str, str, str]:
        head = self._git("rev-parse", "HEAD")
        if head.returncode != 0:
            raise SelfCodingError("Unable to read the current Git commit.")
        baseline = head.stdout.strip()
        base_branch = self._current_branch()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch = f"agent/checkpoint/{stamp}-{self._goal_slug(goal)}-{baseline[:8]}"
        created = self._git("switch", "-c", branch)
        if created.returncode != 0:
            raise SelfCodingError(created.stderr.strip() or "Unable to create self-coding checkpoint branch.")
        return branch, baseline, base_branch

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", checkpoint_id):
            raise SelfCodingError(f"Invalid checkpoint id: {checkpoint_id}")
        return self._checkpoint_dir / f"{checkpoint_id}.json"

    def _save_checkpoint(self, checkpoint: _Checkpoint) -> None:
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "branch": checkpoint.branch,
            "baseline": checkpoint.baseline,
            "base_branch": checkpoint.base_branch,
            "commits": list(checkpoint.commits),
            "created_at": checkpoint.created_at,
            "state": checkpoint.state,
            "promoted_sha": checkpoint.promoted_sha,
            "undo_commits": list(checkpoint.undo_commits),
        }
        path = self._checkpoint_path(checkpoint.checkpoint_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)

    def _load_checkpoint(self, checkpoint_id: str) -> _Checkpoint:
        path = self._checkpoint_path(checkpoint_id)
        if not path.exists():
            raise SelfCodingError(f"Checkpoint not found: {checkpoint_id}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return _Checkpoint(
                checkpoint_id=str(payload["checkpoint_id"]),
                branch=str(payload["branch"]),
                baseline=str(payload["baseline"]),
                base_branch=str(payload["base_branch"]),
                commits=tuple(str(value) for value in payload.get("commits", [])),
                created_at=str(payload["created_at"]),
                state=str(payload["state"]),
                promoted_sha=str(payload["promoted_sha"]) if payload.get("promoted_sha") else None,
                undo_commits=tuple(str(value) for value in payload.get("undo_commits", [])),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SelfCodingError(f"Checkpoint metadata is invalid: {checkpoint_id}") from exc

    def list_checkpoints(self) -> tuple[dict[str, object], ...]:
        """Return durable checkpoint metadata without modifying repository state."""
        if not self._checkpoint_dir.exists():
            return ()
        results: list[dict[str, object]] = []
        for path in sorted(self._checkpoint_dir.glob("*.json")):
            try:
                checkpoint = self._load_checkpoint(path.stem)
            except SelfCodingError:
                continue
            results.append(
                {
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "branch": checkpoint.branch,
                    "baseline": checkpoint.baseline,
                    "base_branch": checkpoint.base_branch,
                    "commits": checkpoint.commits,
                    "created_at": checkpoint.created_at,
                    "state": checkpoint.state,
                    "promoted_sha": checkpoint.promoted_sha,
                    "undo_commits": checkpoint.undo_commits,
                }
            )
        return tuple(results)

    def _delete_branch(self, branch: str) -> None:
        result = self._git("branch", "-D", branch)
        if result.returncode != 0:
            raise SelfCodingError(result.stderr.strip() or f"Unable to delete checkpoint branch: {branch}")

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
- Add or update tests for every behavioral change.
- Run the repository's relevant tests before declaring success.
- Never claim success when tests fail.
- Do not commit generated secrets or machine-specific configuration.

System-coherence mandate:
- Treat this repository as one integrated assistant, not a collection of unrelated features.
- Before editing, inspect the relevant architecture, capability registry, runtime dispatch paths, shared contracts, startup/packaging paths, and existing tests so the change fits the system.
- When a change touches a capability, inspect its callers, providers, UI/voice surfaces, persistence/state, permissions, and packaging implications; update integration points rather than creating parallel one-off behavior.
- Prefer existing shared abstractions, adapters, events, and contracts over duplicating logic.
- After implementing, test the changed feature and the integration paths it can affect. Check for broken imports, stale APIs, contradictory configuration, missing packaging assets, and inconsistent user-facing behavior.
- Do not declare a feature complete merely because its local unit test passes; verify that it is wired into the surrounding Jarvis workflow where applicable.
- Preserve or improve the repository quality floor; never lower a verified quality level, remove a protected contract, or loosen a performance budget.
- Treat UI quality as a monotonic ladder: only equal-or-higher verified rungs may become the new baseline; a richer UI must not trade away existing functionality, safety, integration, or performance.

Implement the goal directly, then leave the repository in a clean, testable, coherently integrated state."""

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

        baseline = getattr(self, "_verification_baseline", "")
        quality_floor = self.repo / "quality_floor.json"
        quality_gate = self.repo / "scripts" / "verify_quality_floor.py"
        if not quality_floor.is_file() or not quality_gate.is_file():
            raise SelfCodingError("Quality-floor verification is mandatory; its manifest or gate is missing.")
        command = (sys.executable, "-m", "scripts.verify_quality_floor")
        if baseline:
            command += ("--baseline", baseline)
        result = self._run(command)
        if result.returncode != 0:
            output = (result.stdout + "\n" + result.stderr).strip()
            raise SelfCodingError(f"Quality-floor verification failed.\n{output[-12000:]}")

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

    def run(self, goal: str) -> str:
        """Preview verified self-coding work as a named checkpoint; never publish main."""
        if not goal.strip():
            raise SelfCodingError("A non-empty coding goal is required.")
        if self.config.max_passes < 1:
            raise SelfCodingError("max_passes must be at least 1.")
        if self.config.publish_main:
            raise SelfCodingError("Direct main publication is disabled; preview the change and explicitly approve its checkpoint.")

        self.validate_repo()
        branch, baseline, base_branch = self._new_branch(goal)
        self._verification_baseline = baseline
        checkpoint_id = branch.split("/", 2)[-1]
        created_at = datetime.now(timezone.utc).isoformat()
        commits: list[str] = []
        checkpoint = _Checkpoint(
            checkpoint_id=checkpoint_id,
            branch=branch,
            baseline=baseline,
            base_branch=base_branch,
            commits=(),
            created_at=created_at,
            state="pending",
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
                    raise SelfCodingError("Unable to record the verified checkpoint commit.")
                commits.append(commit.stdout.strip())
                checkpoint = _Checkpoint(
                    checkpoint_id=checkpoint.checkpoint_id,
                    branch=checkpoint.branch,
                    baseline=checkpoint.baseline,
                    base_branch=checkpoint.base_branch,
                    commits=tuple(commits),
                    created_at=checkpoint.created_at,
                    state="pending",
                )
                self._save_checkpoint(checkpoint)

            if self.config.push_branch:
                pushed = self._git("push", "-u", "origin", branch)
                if pushed.returncode != 0:
                    raise SelfCodingError(pushed.stderr.strip() or "Unable to push self-coding checkpoint branch")

            return checkpoint_id
        except Exception:
            try:
                self._rollback(baseline)
                self._git("switch", base_branch)
                self._delete_branch(branch)
            finally:
                checkpoint_path = self._checkpoint_dir / f"{checkpoint_id}.json"
                checkpoint_path.unlink(missing_ok=True)
            raise

    def _refers_to_checkpoint(self, checkpoint: _Checkpoint) -> None:
        head = self._git("rev-parse", checkpoint.branch)
        if head.returncode != 0:
            raise SelfCodingError(f"Checkpoint branch is missing: {checkpoint.branch}")
        if not checkpoint.commits or head.stdout.strip() != checkpoint.commits[-1]:
            raise SelfCodingError("Checkpoint metadata does not match its Git branch head.")

    def approve_checkpoint(self, checkpoint_id: str) -> str:
        """Explicitly promote one pending checkpoint to main after a fresh baseline check."""
        checkpoint = self._load_checkpoint(checkpoint_id)
        if checkpoint.state != "pending":
            raise SelfCodingError(f"Checkpoint {checkpoint_id} is not pending; current state is {checkpoint.state}.")
        self.validate_repo()
        self._refers_to_checkpoint(checkpoint)

        previous_branch = self._current_branch()
        fetched = self._git("fetch", "origin", "main")
        if fetched.returncode != 0:
            raise SelfCodingError(fetched.stderr.strip() or "Unable to fetch remote main.")
        remote = self._git("rev-parse", "refs/remotes/origin/main")
        if remote.returncode != 0:
            raise SelfCodingError(remote.stderr.strip() or "Unable to inspect remote main.")
        if remote.stdout.strip() != checkpoint.baseline:
            raise SelfCodingError("remote main changed after preview; refusing explicit promotion.")

        local_main = self._git("rev-parse", "refs/heads/main")
        if local_main.returncode != 0 or local_main.stdout.strip() != checkpoint.baseline:
            raise SelfCodingError("local main no longer matches the checkpoint baseline; refusing promotion.")

        promoting = _Checkpoint(
            checkpoint_id=checkpoint.checkpoint_id,
            branch=checkpoint.branch,
            baseline=checkpoint.baseline,
            base_branch=checkpoint.base_branch,
            commits=checkpoint.commits,
            created_at=checkpoint.created_at,
            state="promoting",
        )
        self._save_checkpoint(promoting)

        switched = self._git("switch", "main")
        if switched.returncode != 0:
            self._save_checkpoint(checkpoint)
            raise SelfCodingError(switched.stderr.strip() or "Unable to switch to main for promotion.")

        pushed_remote = False
        promoted = ""
        try:
            merged = self._git("merge", "--ff-only", checkpoint.branch)
            if merged.returncode != 0:
                raise SelfCodingError(merged.stderr.strip() or "Unable to fast-forward main.")
            promoted_sha = self._git("rev-parse", "HEAD")
            if promoted_sha.returncode != 0:
                raise SelfCodingError("Unable to record the promoted main commit.")
            promoted = promoted_sha.stdout.strip()

            promoting = _Checkpoint(
                checkpoint_id=checkpoint.checkpoint_id,
                branch=checkpoint.branch,
                baseline=checkpoint.baseline,
                base_branch=checkpoint.base_branch,
                commits=checkpoint.commits,
                created_at=checkpoint.created_at,
                state="promoting",
                promoted_sha=promoted,
            )
            self._save_checkpoint(promoting)

            pushed = self._git("push", "origin", "main")
            if pushed.returncode != 0:
                raise SelfCodingError(pushed.stderr.strip() or "Unable to publish the approved checkpoint to main.")
            pushed_remote = True

            approved = _Checkpoint(
                checkpoint_id=checkpoint.checkpoint_id,
                branch=checkpoint.branch,
                baseline=checkpoint.baseline,
                base_branch=checkpoint.base_branch,
                commits=checkpoint.commits,
                created_at=checkpoint.created_at,
                state="approved",
                promoted_sha=promoted,
            )
            self._save_checkpoint(approved)
            return promoted
        except Exception as exc:
            if not pushed_remote:
                self._git("reset", "--hard", checkpoint.baseline)
                self._save_checkpoint(checkpoint)
                if previous_branch != "main":
                    restored = self._git("switch", previous_branch)
                    if restored.returncode != 0:
                        raise SelfCodingError("Promotion failed and the previous branch could not be restored.")
            else:
                raise SelfCodingError(
                    f"Checkpoint {checkpoint_id} was promoted to main at {promoted}, but checkpoint metadata could not be finalized; it remains in a promoting state."
                ) from exc
            raise

    def undo_checkpoint(self, checkpoint_id: str) -> str:
        """Undo one pending or approved checkpoint without touching unrelated later main work."""
        checkpoint = self._load_checkpoint(checkpoint_id)
        self.validate_repo()

        current = self._current_branch()
        if checkpoint.state == "pending":
            if current == checkpoint.branch:
                restored = self._git("switch", checkpoint.base_branch)
                if restored.returncode != 0:
                    raise SelfCodingError(restored.stderr.strip() or "Unable to restore the checkpoint base branch.")
            self._delete_branch(checkpoint.branch)
            undone = _Checkpoint(
                checkpoint_id=checkpoint.checkpoint_id,
                branch=checkpoint.branch,
                baseline=checkpoint.baseline,
                base_branch=checkpoint.base_branch,
                commits=checkpoint.commits,
                created_at=checkpoint.created_at,
                state="undone",
            )
            self._save_checkpoint(undone)
            return "undone"

        if checkpoint.state != "approved" or not checkpoint.promoted_sha:
            raise SelfCodingError(f"Checkpoint {checkpoint_id} cannot be undone from state {checkpoint.state}.")

        fetched = self._git("fetch", "origin", "main")
        if fetched.returncode != 0:
            raise SelfCodingError(fetched.stderr.strip() or "Unable to fetch remote main.")
        remote = self._git("rev-parse", "refs/remotes/origin/main")
        local_main = self._git("rev-parse", "refs/heads/main")
        if remote.returncode != 0 or local_main.returncode != 0:
            raise SelfCodingError("Unable to inspect main before undo.")
        if remote.stdout.strip() != checkpoint.promoted_sha or local_main.stdout.strip() != checkpoint.promoted_sha:
            raise SelfCodingError("main changed after approval; refusing to undo unrelated work.")

        switched = self._git("switch", "main")
        if switched.returncode != 0:
            raise SelfCodingError(switched.stderr.strip() or "Unable to switch to main for undo.")

        undo_commits: list[str] = []
        pushed_remote = False
        try:
            for commit in reversed(checkpoint.commits):
                reverted = self._git("revert", "--no-edit", commit)
                if reverted.returncode != 0:
                    self._git("revert", "--abort")
                    raise SelfCodingError(reverted.stderr.strip() or f"Unable to revert checkpoint commit {commit}.")
                head = self._git("rev-parse", "HEAD")
                if head.returncode != 0:
                    raise SelfCodingError("Unable to record an undo commit.")
                undo_commits.append(head.stdout.strip())

            undoing = _Checkpoint(
                checkpoint_id=checkpoint.checkpoint_id,
                branch=checkpoint.branch,
                baseline=checkpoint.baseline,
                base_branch=checkpoint.base_branch,
                commits=checkpoint.commits,
                created_at=checkpoint.created_at,
                state="undoing",
                promoted_sha=checkpoint.promoted_sha,
                undo_commits=tuple(undo_commits),
            )
            self._save_checkpoint(undoing)

            pushed = self._git("push", "origin", "main")
            if pushed.returncode != 0:
                raise SelfCodingError(pushed.stderr.strip() or "Unable to publish checkpoint undo to main.")
            pushed_remote = True

            undone = _Checkpoint(
                checkpoint_id=checkpoint.checkpoint_id,
                branch=checkpoint.branch,
                baseline=checkpoint.baseline,
                base_branch=checkpoint.base_branch,
                commits=checkpoint.commits,
                created_at=checkpoint.created_at,
                state="undone",
                promoted_sha=checkpoint.promoted_sha,
                undo_commits=tuple(undo_commits),
            )
            self._save_checkpoint(undone)
            return "undone"
        except Exception as exc:
            if not pushed_remote:
                self._git("reset", "--hard", checkpoint.promoted_sha)
                approved = _Checkpoint(
                    checkpoint_id=checkpoint.checkpoint_id,
                    branch=checkpoint.branch,
                    baseline=checkpoint.baseline,
                    base_branch=checkpoint.base_branch,
                    commits=checkpoint.commits,
                    created_at=checkpoint.created_at,
                    state="approved",
                    promoted_sha=checkpoint.promoted_sha,
                )
                self._save_checkpoint(approved)
            else:
                raise SelfCodingError(
                    f"Checkpoint {checkpoint_id} undo reached main, but checkpoint metadata could not be finalized; it remains in an undoing state."
                ) from exc
            raise

    def _publish_main(self, baseline: str, branch: str) -> None:
        """Legacy guard: direct main publication is intentionally unavailable."""
        raise SelfCodingError(
            "Direct main publication is disabled. Create a checkpoint, inspect it, then explicitly approve the checkpoint."
        )


if __name__ == "__main__":
    raise SystemExit("Use python -m self_coding.run for the guarded CLI.")
