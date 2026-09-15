# Jarvis voice

Jarvis uses an **always-listening local microphone path** with a local wake-word gate. After microphone permission is granted, audio can be monitored locally, but Jarvis does not create a cloud request until the wake word **"Jarvis"** is accepted.

## Brain and routing

Jarvis uses **OmniRoute only** as its conversational and agent brain. Claude Code, a Claude subscription, and direct Claude routing are not required and are not valid Jarvis fallbacks. A missing OmniRoute configuration must fail clearly rather than silently switching brains.

Defaults:

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

## Activation behavior

- Non-addressed room speech is ignored locally.
- A recognized `Jarvis` wake word starts a bounded request capture window.
- The accepted utterance then follows the existing Jarvis orchestration and permission path.
- Only one active voice session is allowed; duplicate listeners are rejected.
- Cancel, stop, and speaking interruption remain compatible with existing controls.
- If safe microphone capture or wake gating cannot be established, Jarvis remains silent.

## Speech output

The preferred high-quality speech output is ElevenLabs. Never store an ElevenLabs API key in the repository; use the supported `ELEVENLABS_API_KEY` environment variable or credential mechanism. The requested voice must be looked up in the account library and a real speech test must succeed before setup is declared working.

Kokoro remains the speech-output fallback. Neither ElevenLabs nor Kokoro is an agent brain.

## Privacy

Wake-word detection is local-only. No cloud request is created before wake acceptance. Ambient audio and non-addressed transcripts must not be written to logs.
