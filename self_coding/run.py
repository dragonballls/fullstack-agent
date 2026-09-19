"""Command-line entry point for guarded self-coding checkpoints."""

from __future__ import annotations

import argparse
from pathlib import Path

from .agent import SelfCodingAgent, SelfCodingConfig, SelfCodingError


def _agent(backend: str, passes: int, push: bool = False) -> SelfCodingAgent:
    repo = Path(__file__).resolve().parents[1]
    return SelfCodingAgent(
        SelfCodingConfig(
            repo=repo,
            push_branch=push,
            max_passes=passes,
            backend=backend,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview guarded self-coding work as a named checkpoint, then explicitly approve or undo it."
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--approve", metavar="CHECKPOINT", help="Explicitly promote a pending checkpoint to main")
    actions.add_argument("--undo", metavar="CHECKPOINT", help="Undo a pending checkpoint or safely revert an approved checkpoint")
    actions.add_argument("--list", action="store_true", help="List durable self-coding checkpoints")

    parser.add_argument("goal", nargs="?", help="What the coding agent should improve (default action: preview)")
    parser.add_argument("--push", action="store_true", help="Push the verified checkpoint branch to origin")
    parser.add_argument("--passes", type=int, default=1, help="Number of verified coding passes")
    parser.add_argument("--backend", default="auto", choices=("auto", "claude", "codex", "gemini"))
    args = parser.parse_args()

    if args.approve or args.undo or args.list:
        if args.goal or args.push:
            parser.error("--approve/--undo/--list cannot be combined with a goal or --push")
        try:
            agent = _agent(args.backend, args.passes)
            if args.approve:
                promoted = agent.approve_checkpoint(args.approve)
                print(f"SELF-CODING APPROVED: {args.approve} -> main @ {promoted}")
            elif args.undo:
                agent.undo_checkpoint(args.undo)
                print(f"SELF-CODING UNDONE: {args.undo}")
            else:
                for checkpoint in agent.list_checkpoints():
                    print(
                        f"{checkpoint['state']}: {checkpoint['checkpoint_id']} "
                        f"branch={checkpoint['branch']} commits={len(checkpoint['commits'])}"
                    )
            return 0
        except SelfCodingError as exc:
            print(f"SELF-CODING ACTION FAILED SAFELY: {exc}")
            return 1

    if not args.goal:
        parser.error("a goal is required unless --approve, --undo, or --list is used")
    try:
        checkpoint = _agent(args.backend, args.passes, args.push).run(args.goal)
    except SelfCodingError as exc:
        print(f"SELF-CODING FAILED SAFELY: {exc}")
        return 1
    print(f"SELF-CODING PREVIEW VERIFIED: {checkpoint}")
    print("Explicit action required: inspect the checkpoint, then use --approve CHECKPOINT or --undo CHECKPOINT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
