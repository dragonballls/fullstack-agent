# Jarvis Always-Listening + OmniRoute-Only Voice Design

## Goal
Make Jarvis continuously listen locally, respond only when directly addressed with the wake word "Jarvis", and use OmniRoute as the only conversational/agent brain without requiring Claude Code or a Claude subscription.

## Architecture
The voice path is split into three independent stages: local wake-word gating, speech capture/transcription, and Jarvis brain/response. Audio before wake-word acceptance is processed locally and is never sent to an AI provider. Once the wake word is detected, the captured request is passed into the existing Jarvis orchestration path, which must resolve to OmniRoute only. Response audio remains on the existing ElevenLabs/Kokoro voice path.

Claude-specific setup is removed from required installation/readiness contracts. Any legacy Claude integration remains optional and must never be selected by default, silently installed, or required for startup, voice, self-coding, or quality-of-life features.

## Behavioral contract

- Jarvis listens continuously after the local microphone permission is granted.
- Ordinary conversation, television, music, and other speech do not trigger a Jarvis response unless the wake word is detected.
- The accepted invocation form is "Jarvis" followed by the request, with a configurable short post-wake capture window for natural pauses.
- Wake-word detection runs locally; non-addressed audio is discarded locally.
- A detected wake word starts a bounded speech capture session. Silence ends capture; explicit stop/cancel interrupts it.
- The user can interrupt Jarvis while it is speaking without creating a second response pipeline.
- Voice sessions and typed sessions share the same Jarvis brain and tool permissions.
- OmniRoute is the only configured conversational provider. Direct Claude/Claude Code routing is prohibited by contract.
- Missing OmniRoute configuration produces a clear startup/readiness failure rather than falling back to Claude or a local LLM.
- ElevenLabs may be used for speech synthesis when configured; Kokoro remains the fallback. Neither is an agent brain.
- No local LLM is installed or silently enabled as an AI fallback.
- The wake-word listener must fail closed: if it cannot safely establish microphone capture or wake gating, Jarvis remains silent rather than forwarding ambient audio.

## Configuration

Add a voice activation configuration with these defaults:

```text
JARVIS_VOICE_MODE=open
JARVIS_WAKE_WORD=jarvis
JARVIS_WAKE_CONFIDENCE=0.70
JARVIS_WAKE_POST_WINDOW_SECONDS=6
JARVIS_VOICE_LANGUAGE=en-US
JARVIS_VOICE_BRAIN=omniroute
JARVIS_REQUIRE_OMNIROUTE=true
JARVIS_ALLOW_CLAUDE=false
```

The public contract must document that `JARVIS_ALLOW_CLAUDE=false` is fixed for the Jarvis profile and is not a supported production override.

## Safety and privacy

- Wake detection is local-only.
- No cloud request is created until a wake event is accepted.
- The transcription provider, when cloud-backed, receives only the post-wake utterance.
- Logs must not contain microphone audio, transcripts from non-addressed speech, API keys, or credentials.
- Voice activation does not bypass existing capability, permission, confirmation, or emergency-stop controls.
- One active voice session is allowed at a time; duplicate listeners must be prevented by a process/session lock.

## Testing

Unit tests must cover wake-word acceptance/rejection, confidence thresholding, post-wake capture expiry, cancellation, duplicate-session locking, and configuration defaults. Integration tests must verify that accepted utterances route through the existing OmniRoute client and that no Claude target or Claude dependency appears in readiness/configuration. Contract tests must verify documentation/install paths no longer require Claude Code or a Claude subscription.

## Non-goals

This change does not replace the existing computer-control, hand-control, saved-location, self-coding, God’s Eye, or Windows-maintenance capabilities. It also does not promise a particular speech-recognition vendor or exact actor voice; it defines the routing and activation contracts those components must satisfy.
