"""Command-line entry point for guarded self-coding."""

from __future__ import annotations

import argparse
from pathlib import Path

from .agent import SelfCodingAgent, SelfCodingConfig, SelfCodingError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a guarded cloud-agent coding pass in this Git repository.")
    parser.add_argument("goal", help="What the coding agent should improve")
    parser.add_argument("--push", action="store_true", help="Push the verified branch to origin")
    parser.add_argument("--publish-main", action="store_true", help="Publish the verified pass to main only when remote main still matches the starting commit")
    parser.add_argument("--passes", type=int, default=1, help="Number of verified coding passes")
    parser.add_argument("--backend", default="auto", choices=("auto", "claude", "codex", "gemini"))
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    config = SelfCodingConfig(
        repo=repo,
        push_branch=args.push,
        publish_main=args.publish_main,
        max_passes=args.passes,
        backend=args.backend,
    )
    try:
        branch = SelfCodingAgent(config).run(args.goal)
    except SelfCodingError as exc:
        print(f"SELF-CODING FAILED SAFELY: {exc}")
        return 1
    print(f"SELF-CODING VERIFIED: {branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
