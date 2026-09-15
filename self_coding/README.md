# Autonomous self-coding

`self_coding` adds a controlled cloud coding loop to fullstack-agent without replacing the existing memory, voice, face, or hands stack.

## What it does

1. Requires a real Git repository and a clean working tree.
2. Creates an isolated `agent/self-code/<timestamp>` branch.
3. Sends the coding goal to an installed cloud coding CLI (`claude`, `codex`, or `gemini`).
4. Runs verification commands after the agent changes code.
5. Commits only after verification succeeds.
6. Optionally pushes the verified branch with `--push`.
7. If anything fails, restores the exact starting commit and removes newly-created untracked files.

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

The default is intentionally conservative: no automatic push and one verified pass.
