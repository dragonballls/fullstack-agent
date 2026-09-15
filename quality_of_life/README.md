# Quality of Life

This subsystem is a separate capability layer for fullstack-agent. It is designed to add computer awareness, computer interaction, orchestration, background maintenance, and model routing without replacing the existing memory, voice, face, hands, or self-coding components.

## Planned capabilities

- Windows computer control: mouse, keyboard, clipboard, windows/apps.
- Screen capture and structured screen context.
- Browser/app orchestration through explicit tools.
- Background maintenance jobs with visible status and cancellation.
- Cloud model routing with ordered fallbacks; no local LLM required.
- Self-coding integration through the existing guarded `self_coding` engine.

## Safety boundaries

Tools are explicit and deny-by-default. Every mutating operation receives a capability check before execution. Credentials, browser profiles, and files outside configured workspaces are never treated as ordinary agent context. High-impact actions must expose a confirmation hook to the caller.

## Compatibility

The subsystem is optional. If its dependencies are absent, the rest of fullstack-agent continues to work normally.
