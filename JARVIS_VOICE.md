# Jarvis voice

The Jarvis voice is an always-listening, wake-word-gated interface. The microphone may remain active after permission is granted, but Jarvis only starts a request after the local activation gate accepts the wake word **"Jarvis"**.

## Brain and routing

Jarvis uses **OmniRoute only** as its conversational/agent brain. Claude Code, a Claude subscription, and direct Claude routing are not required and are not valid Jarvis fallbacks.

Required voice routing defaults:

```text
JARVIS_VOICE_MODE=open
JARVIS_WAKE_WORD=jarvis
JARVIS_WAKE_CONFIDENCE=0.70
JARVIS_WAKE_POST_WINDOW_SECONDS=6
JARVIS_VOICE_BRAIN=omniroute
JARVIS_REQUIRE_OMNIROUTE=true
JARVIS_ALLOW_CLAUDE=false
```

`JARVIS_ALLOW_CLAUDE` is fixed to `false` for the Jarvis profile. A misconfigured non-OmniRoute brain must fail closed.

## Always-listening behavior

Wake-word detection is local. Before the wake word is accepted, ambient speech is ignored locally and does not create a cloud request. After acceptance, Jarvis captures only the bounded utterance associated with that wake event, then sends that utterance through the existing OmniRoute orchestration path.

The default wake confidence threshold is 0.70. The default post-wake capture window is 6 seconds. These values are configuration defaults, not guarantees of recognition accuracy across all microphones or environments.

One active voice session is permitted at a time. A duplicate listener must refuse ownership rather than creating two simultaneous response pipelines. Explicit cancel/stop and speaking interruption remain supported.

## Speech output

The preferred high-quality cloud speech output is **ElevenLabs**. Do not store an ElevenLabs API key in this repository. On Windows, provide the key through the supported `ELEVENLABS_API_KEY` environment variable or the credential mechanism supported by the installed speech version.

The built-in **Kokoro** voice remains the fallback. ElevenLabs and Kokoro are speech-output engines only; neither may replace OmniRoute as the Jarvis brain.

## Reliability

The voice setup must:

1. Verify the ElevenLabs credential before completing setup when ElevenLabs is selected.
2. Select the requested voice from the account's voice library rather than guessing or hard-coding a stale voice ID.
3. Perform an actual speech test before declaring voice output successful.
4. Keep Kokoro available as an automatic speech-output fallback.
5. Never print the API key or write it into tracked files.
6. Preserve the always-listening wake-word mode selected by the Jarvis profile; push-to-talk is not the default Jarvis activation behavior.

## Privacy and failure behavior

- Wake detection is local-only.
- No cloud request is created before wake acceptance.
- Non-addressed transcripts must not be written to logs.
- Microphone audio must not be written to logs.
- If safe microphone capture or wake gating cannot be established, Jarvis remains silent.
- Existing capability, permission, confirmation, and emergency-stop controls remain in force.
