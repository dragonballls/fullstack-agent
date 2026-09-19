"""Command-line entry point for guarded self-coding."""

from __future__ import annotations

import argparse
from pathlib import Path

from .agent import SelfCodingAgent, SelfCodingConfig, SelfCodingError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run guarded cloud-agent coding with reversible preview checkpoints.")
    parser.add_argument("goal", nargs="?", help="What the coding agent should improve")
    parser.add_argument("--push", action="store_true", help="Push the verified preview branch to origin")
    parser.add_argument("--publish-main", action="store_true", help="Deprecated compatibility flag; direct main publication is disabled")
    parser.add_argument("--approve", action="store_true", help="Explicitly approve the active preview and promote it to main")
    parser.add_argument("--undo", action="store_true", help="Undo the active preview or latest published self-coding checkpoint")
    parser.add_argument("--no-push", action="store_true", help="Do not push main when approving or undoing")
    parser.add_argument("--passes", type=int, default=1, help="Number of verified coding passes")
    parser.add_argument("--backend", default="auto", choices=("auto", "claude", "codex", "gemini"))
    args = parser.parse_args()

    modes = int(bool(args.approve)) + int(bool(args.undo))
    if modes > 1:
        parser.error("--approve and --undo cannot be used together")
    if (args.approve or args.undo) and args.goal:
        parser.error("goal cannot be supplied with --approve or --undo")
    if not (args.approve or args.undo) and not args.goal:
        parser.error("goal is required unless --approve or --undo is used")
    if args.no_push and not (args.approve or args.undo):
        parser.error("--no-push applies only to --approve or --undo")

    repo = Path(__file__).resolve().parents[1]
    config = SelfCodingConfig(
        repo=repo,
        push_branch=args.push,
        publish_main=args.publish_main,
        max_passes=args.passes,
        backend=args.backend,
    )
    agent = SelfCodingAgent(config)
    try:
        if args.approve:
            result = agent.approve(push=not args.no_push)
        elif args.undo:
            result = agent.undo(push=not args.no_push)
        else:
            result = agent.run(args.goal or "")
    except SelfCodingError as exc:
        print(f"SELF-CODING FAILED SAFELY: {exc}")
        return 1

    if args.approve:
        print(f"SELF-CODING APPROVED: {result}")
    elif args.undo:
        print(f"SELF-CODING UNDONE: {result}")
    else:
        print(f"SELF-CODING VERIFIED PREVIEW: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
