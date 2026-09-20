# Autonomous self-coding

`self_coding` adds a controlled cloud coding loop to fullstack-agent without replacing the existing memory, voice, face, or hands stack.

## What it does

1. Requires a real Git repository and a clean working tree.
2. Creates an isolated named `agent/checkpoint/<name>` branch.
3. Sends the coding goal to an installed cloud coding CLI (`claude`, `codex`, or `gemini`).
4. Runs verification commands quietly after every coding attempt; test output is captured instead of being printed into the UI.
5. If verification fails, feeds the concrete failure diagnostics into the next coding attempt so the agent can repair its own change.
6. Commits only after verification succeeds.
6. Saves durable checkpoint metadata under `.git/jarvis-checkpoints/`.
7. Optionally pushes the verified checkpoint branch with `--push`; this never publishes `main`.
8. If anything fails, restores the exact starting commit and removes newly-created untracked files.
9. A checkpoint remains pending until an explicit `--approve CHECKPOINT` action promotes it to `main`.
10. `--undo CHECKPOINT` discards a pending checkpoint or creates a safe revert for an approved checkpoint.
11. Undo refuses to touch `main) when unrelated work has landed since approval.

The coding agent is explicitly instructed to stay inside the repository and never access or expose credentials, private keys, browser profiles, or files outside the repository.

## Run

From the repository root:

```text
python -m self_coding.run "Improve the highest-value part of this project, add tests, and keep all existing behavior working."
```

To select a backend explicitly:

```text
python -m self_coding.run --backend claude "Improve the highest-value part of this project and verify it."
```

To push the verified branch:

```text
python -m self_coding.run --push "Implement the requested improvement and verify it."
```

The default is intentionally conservative: no automatic push and up to five autonomous repair/verification attempts. The loop is hard-bounded at eight attempts so self-coding can never run forever.
