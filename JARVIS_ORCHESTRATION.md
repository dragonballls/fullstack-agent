# Jarvis orchestration

Jarvis has one brain path: **OmniRoute**. The orchestration layer may use different OmniRoute model profiles for speed, reasoning, coding, vision, or maintenance, but these remain profiles of the same OmniRoute route.

Voice and typed requests share the same orchestration and permission path. Voice activation is handled before orchestration: the local listener waits for the wake word `Jarvis`, and only the accepted utterance enters the cloud request pipeline.

## Voice defaults

```text
JARVIS_VOICE_MODE=open
JARVIS_WAKE_WORD=jarvis
JARVIS_WAKE_CONFIDENCE=0.70
JARVIS_WAKE_POST_WINDOW_SECONDS=6
JARVIS_VOICE_BRAIN=omniroute
JARVIS_REQUIRE_OMNIROUTE=true
JARVIS_ALLOW_CLAUDE=false
```

## Provider rules

- OmniRoute is required for the Jarvis brain.
- Claude Code and a Claude subscription are not required.
- Claude is not a fallback brain.
- A local LLM is not a silent fallback brain.
- Missing OmniRoute configuration fails clearly instead of switching brains.
- Existing capability, confirmation, cancellation, and emergency-stop controls are shared by typed and voice requests.

## Voice data flow

`microphone -> local wake-word gate -> bounded post-wake utterance -> Jarvis orchestration -> OmniRoute -> existing tools/personality -> speech synthesis`

Wake detection is local-only. Ambient or non-addressed speech does not create an OmniRoute request and must not be logged.

## Reliability

Only one voice session may be active. Duplicate listeners must refuse ownership. If microphone access, wake gating, or required OmniRoute configuration is unavailable, Jarvis remains silent or reports the configuration error rather than forwarding ambient audio or choosing another brain.
