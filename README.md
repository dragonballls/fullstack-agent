# fullstack-agent

> **Jarvis edition:** this fork provides a cloud-routed Jarvis-style agent with local wake-word voice activation and optional computer-control extensions.

**Jarvis brain: OmniRoute only.** Claude Code and a Claude subscription are not required by the Jarvis runtime and are not valid fallback brains.

## Jarvis voice behavior

Jarvis is designed to remain **always listening locally** after microphone permission is granted. It responds only after the local wake-word gate recognizes **"Jarvis"** with sufficient confidence. Ordinary room speech, television, music, and other conversations do not create an AI request.

After the wake word is accepted, only the bounded post-wake utterance is sent through Jarvis's existing cloud orchestration path. The brain remains OmniRoute; ElevenLabs and Kokoro are speech-output engines, not brains.

The voice activation path fails closed: if safe microphone capture or wake gating cannot be established, Jarvis stays silent rather than sending ambient audio to a provider. Only one active voice session is permitted.

## OmniRoute contract

Jarvis uses the existing OmniRoute route and profile selection. A missing or invalid OmniRoute configuration must produce a clear failure rather than switching to Claude or silently enabling a local LLM.

Default Jarvis voice configuration:

```text
JARVIS_VOICE_MODE=open
JARVIS_WAKE_WORD=jarvis
JARVIS_WAKE_CONFIDENCE=0.70
JARVIS_WAKE_POST_WINDOW_SECONDS=6
JARVIS_VOICE_BRAIN=omniroute
JARVIS_REQUIRE_OMNIROUTE=true
JARVIS_ALLOW_CLAUDE=false
```

`JARVIS_ALLOW_CLAUDE=false` is a fixed Jarvis-profile policy. It is not a supported production override.

## Jarvis capabilities

The repository includes independent guarded extensions for memory, voice plumbing, visualizer, webcam hand control, Windows quality-of-life tools, saved locations, God’s Eye context, multi-AI orchestration, and self-coding. Optional components are isolated so a failure in one does not take down the base stack.

Capability and mutating-operation permission gates remain in force for voice-triggered commands.

## Voice output

The preferred high-quality speech output is ElevenLabs, with Kokoro as the fallback. See `JARVIS_VOICE.md` for credential handling and speech-test requirements. These components synthesize speech only; they never select Jarvis's brain.

## Privacy and safety

- Wake-word recognition is local-only.
- No cloud request is made before wake acceptance.
- Ambient/non-addressed speech is not logged.
- Microphone audio is not logged.
- Voice activation does not bypass existing permissions, confirmations, or emergency-stop controls.
- Duplicate listeners are rejected.

## License

Copyright (c) 2026 Jared Rhodenizer.

Licensed under the GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later). See `LICENSE` for the complete terms.
