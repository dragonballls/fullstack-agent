# fullstack-agent

> **Jarvis edition:** this fork is configured for a cloud-routed Jarvis experience with local voice activation and an OmniRoute-only brain.

**Jarvis brain:** **OmniRoute only.** Claude Code and a Claude subscription are not required and are not part of the Jarvis runtime contract.

Not an agent that writes full-stack code. **An agent that HAS a full stack: memory, voice, and face, plus an optional set of hands.** This repo assembles the open components on your machine into one Jarvis-style agent.

## What you get

Four pieces, each its own open repo, each excellent alone, assembled here into one agent:

- **The mind: [ai-memory-vault](https://github.com/jaredrhod/ai-memory-vault).** Persistent memory built on plain text files your AI reads and writes.
- **The mouth: [backtalk](https://github.com/jaredrhod/backtalk).** Voice input/output plumbing that can be adapted to Jarvis's existing brain and personality.
- **The face: [ai-visualizer](https://github.com/jaredrhod/ai-visualizer).** Visualizers that can idle, listen, think, and speak in sync with the conversation.
- **The hands: [barehands](https://github.com/jaredrhod/barehands).** Optional webcam hand control.

Every piece is optional at the component level; the Jarvis brain itself is not switched to a second provider.

## Jarvis voice behavior

Jarvis's target voice mode is **always listening locally**. The microphone can remain open after the user grants permission, but Jarvis stays silent until a local wake-word gate accepts **"Jarvis"**. Non-addressed room speech is discarded locally and does not create an AI request.

After the wake word is accepted, only that bounded utterance is forwarded into Jarvis's existing orchestration path. The brain target is OmniRoute; speech synthesis may use the configured ElevenLabs voice with Kokoro as fallback. Voice output is not an AI brain.

The wake-word policy is fail-closed: if activation cannot be established safely, Jarvis remains silent rather than forwarding ambient audio.

## Jarvis integration

This fork ships guarded Jarvis extensions without replacing the core stack:

- **`self_coding/`** is a guarded cloud coding engine.
- **`quality_of_life/`** is an optional capability layer for Windows computer control, screen capture, browser automation, saved locations, hand control, cancellable background jobs, and cloud-model failover.
- **OmniRoute** is the Jarvis brain path used for profiled cloud-model requests.

Capabilities remain deny-by-default, mutating operations pass the shared permission/confirmation policy, and optional components must not break the base stack.

## Setup

This Jarvis fork does **not** require Claude Code. Configure OmniRoute using the existing environment contract and then configure the optional voice/memory/visual components that you actually use.

The essential Jarvis runtime setting is:

```text
JARVIS_VOICE_MODE=open
JARVIS_WAKE_WORD=jarvis
JARVIS_WAKE_CONFIDENCE=0.70
JARVIS_WAKE_POST_WINDOW_SECONDS=6
JARVIS_VOICE_BRAIN=omniroute
JARVIS_REQUIRE_OMNIROUTE=true
JARVIS_ALLOW_CLAUDE=false
```

`JARVIS_ALLOW_CLAUDE` is intentionally fixed to `false` for the Jarvis profile. Claude is not a fallback brain.

## Voice quality

The preferred high-quality speech output remains ElevenLabs, with Kokoro as the fallback. See `JARVIS_VOICE.md` for credential handling and speech-test requirements. Neither speech system is allowed to replace OmniRoute as Jarvis's brain.

## Safety and privacy

- Wake-word detection is local-only.
- No cloud request is created before wake-word acceptance.
- Logs must not contain ambient audio, non-addressed transcripts, API keys, or credentials.
- Only one active voice session is allowed at a time.
- Existing capability, confirmation, and emergency-stop controls remain in force.

## License

Copyright (c) 2026 Jared Rhodenizer.

Licensed under the GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later). Use it in your business, commercially, for free. If you redistribute or run a modified version as a service to others, follow the license's corresponding-source requirements. Credit the upstream project when building on it.
