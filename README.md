# fullstack-agent

> **Jarvis edition:** a cloud-routed Jarvis-style agent with local wake-word voice activation and optional computer-control extensions.

**Jarvis brain: OmniRoute only.** Claude Code and a Claude subscription are not required by the Jarvis runtime and are not valid fallback brains.

## Jarvis voice

Jarvis is designed to remain **always listening locally** after microphone permission is granted. It responds only after the local wake-word gate accepts **"Jarvis"** at the configured confidence threshold. Ordinary room speech does not create an AI request.

After wake-word acceptance, the bounded utterance is handed to the existing Jarvis orchestration path. The brain remains OmniRoute. ElevenLabs and Kokoro are speech-output engines only.

The activation path fails closed: if safe microphone capture or wake gating cannot be established, Jarvis remains silent rather than forwarding ambient audio. Only one active voice session is permitted.

Default configuration:

```text
JARVIS_VOICE_MODE=open
JARVIS_WAKE_WORD=jarvis
JARVIS_WAKE_CONFIDENCE=0.70
JARVIS_WAKE_POST_WINDOW_SECONDS=6
JARVIS_VOICE_BRAIN=omniroute
JARVIS_REQUIRE_OMNIROUTE=true
JARVIS_ALLOW_CLAUDE=false
```

`JARVIS_ALLOW_CLAUDE=false` is fixed for the Jarvis profile.

## Existing Jarvis capabilities

This fork includes guarded quality-of-life tooling for Windows computer control, screen capture, browser automation, saved locations, webcam hand control, health/maintenance workflows, cloud-model orchestration, God’s Eye context, and self-coding. Optional components remain isolated so one failure does not disable unrelated capabilities.

## Voice output

The preferred high-quality speech output remains ElevenLabs, with Kokoro as the fallback. See `JARVIS_VOICE.md` for secret handling and real speech-test requirements. Neither speech engine is permitted to become Jarvis's brain.

## Privacy and safety

- Wake-word detection is local-only.
- No cloud request is created before wake acceptance.
- Ambient/non-addressed speech and microphone audio are not logged.
- Voice activation does not bypass existing capability, permission, confirmation, cancellation, or emergency-stop controls.
- Duplicate voice listeners are rejected.

## License

Copyright (c) 2026 Jared Rhodenizer.

Licensed under the GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later). See `LICENSE` for the complete terms.
