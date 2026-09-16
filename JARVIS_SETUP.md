# Jarvis setup

This is the authoritative setup contract for the Jarvis profile in this repository.

## Runtime requirements

- The conversational/agent brain is **OmniRoute only**.
- Claude Code and a Claude subscription are not required.
- `JARVIS_ALLOW_CLAUDE` is always false for the Jarvis profile.
- ElevenLabs and Kokoro are speech-output engines, not agent brains.

## Voice

Jarvis starts an always-listening local wake-word listener after microphone permission is granted. The detailed voice contract is `JARVIS_VOICE.md` and must be read before configuring the voice runtime.

1. Install the optional voice dependencies from `quality_of_life/voice_requirements.txt` on supported Windows Python versions.
2. Run the local `LocalWakeWordListener` with the `hey_jarvis` wake model.
3. Keep wake detection local; do not upload microphone frames before wake acceptance.
4. After wake detection, pass the resulting speech transcript into `JarvisVoiceRuntime.route(...)`.
5. `JarvisVoiceRuntime` rejects non-addressed speech and routes accepted requests only through the existing OmniRoute router.
6. Keep a single active voice session and debounce repeated wake detections.
7. If microphone or wake-word dependencies are unavailable, fail closed and keep Jarvis silent.

The current repository contains the wake detector and OmniRoute routing boundary. An end-to-end speech-to-text adapter is intentionally a separate component so the microphone/wake layer cannot silently become a second brain.

## Accounts and services

Use the unified account layer for external identities. OAuth consent belongs to the user; passwords must never be requested by Jarvis.

Multiple identities can coexist for Google, Microsoft, GitHub, YouTube, Instagram, and generic web services. Account grants and provider scopes remain the source of authorization. Writes, destructive actions, financial actions, and security-sensitive actions require confirmation by default.

Credentials and refresh tokens stay behind the runtime credential broker and are never stored in tracked configuration or returned to the model.

Official provider APIs should be used when they expose the requested operation. Browser automation is only a bounded fallback behind the existing browser and permission controls. Jarvis must report unsupported operations instead of pretending they are available.

## Existing safety contracts

Do not bypass the capability policy, confirmation hooks, emergency stop, cancellation, self-coding safeguards, or browser/domain restrictions when an action originates from voice or an external account.

## Installation separation

`fullstack-agent.md` is retained for the upstream fullstack-agent setup flow. It is **not** the Jarvis installer and must not be used as the Jarvis runtime contract. Jarvis installations use this document and the repository's normal launcher/update mechanisms.
