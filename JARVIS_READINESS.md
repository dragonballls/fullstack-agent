# Jarvis readiness

Jarvis readiness is evaluated without Claude Code and without a Claude subscription.

## Required brain

- **OmniRoute:** required for Jarvis conversational/agent requests.
- **Claude/Claude Code:** not a Jarvis dependency and not a fallback.
- **Local LLM:** not a Jarvis fallback.

The default voice policy is:

```text
JARVIS_VOICE_MODE=open
JARVIS_WAKE_WORD=jarvis
JARVIS_WAKE_CONFIDENCE=0.70
JARVIS_WAKE_POST_WINDOW_SECONDS=6
JARVIS_VOICE_BRAIN=omniroute
JARVIS_REQUIRE_OMNIROUTE=true
JARVIS_ALLOW_CLAUDE=false
```

## Voice readiness

A ready voice path must have microphone access available, local wake-word gating configured, and the OmniRoute brain policy selected. Voice activation must fail closed when those requirements are not satisfied.

Always-listening means the local listener may remain active, but it must not send ambient/non-addressed speech to the cloud. A request begins only after the wake word `Jarvis` is accepted.

## Speech output

ElevenLabs may provide the preferred cloud speech output when configured, with Kokoro as fallback. Speech synthesis is not a brain provider and does not change the OmniRoute requirement.

## Existing safeguards

Capability permissions, mutating-action confirmation, cancellation, emergency stop, duplicate-session protection, and the existing quality-of-life/self-coding readiness checks remain required.
