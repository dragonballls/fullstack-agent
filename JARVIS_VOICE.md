# Jarvis voice

Jarvis uses the embedded Backtalk voice I/O layer as its desktop speech interface. Backtalk handles microphone capture, speech recognition, push-to-talk/listening behavior, and speech output; the Jarvis runtime remains the only planner and tool-execution brain.

## Brain and routing

Jarvis uses **OmniRoute** for conversational and agent routing. Claude Code, a Claude subscription, and direct Claude routing are not Jarvis fallbacks.

A missing or unavailable OmniRoute configuration must fail clearly rather than silently selecting another agent brain.

## Default Backtalk settings

On first normal startup Jarvis creates `%LOCALAPPDATA%\\Jarvis\\backtalk.json` when it does not already exist. The current defaults are:

```text
name=JARVIS
ptt_key=home
mic_mode=ptt
voice=bm_lewis
stt_model=small.en
stt_device=auto
stt_compute=int8
```

The exact active values are loaded from the local Backtalk configuration and supported `JARVIS_*` environment settings.

## Activation behavior

The default desktop configuration uses Backtalk push-to-talk behavior. When an active voice session is running, the voice bridge passes recognized speech into the existing `JarvisDesktopController`, which routes the request through the normal Jarvis orchestration and capability policy.

Mutating requests are still confirmation-gated. Voice input cannot bypass confirmation, permissions, cancellation, or the deny-by-default capability policy.

An open-microphone mode is available through the supported Backtalk configuration. It still routes accepted transcripts through the same Jarvis brain and policy boundary.

## Speech output

Kokoro is embedded as a local speech-output option. **ElevenLabs** is supported as an optional externally configured speech-output provider. Both are output engines only; neither becomes an agent planner or tool executor, and neither changes the OmniRoute-only brain boundary.

Microphone/speaker access is machine-specific. If audio initialization fails, Jarvis should keep the Fullstack visualizer running and log the degraded voice component rather than terminating the desktop application.

## Frozen-build verification

The Windows release gate explicitly embeds `backtalk/source` inside the PyInstaller bundle and runs a frozen-EXE smoke validation that resolves that embedded path and imports the Backtalk `Ears`, `Mouth`, and `PTTListener` contracts without requiring real microphone/speaker hardware.

That smoke check proves the packaged source/import contract. It does not prove a particular PC's audio hardware, Windows privacy settings, microphone permissions, or speech quality.

## Privacy and logging

The voice bridge must not write ambient room audio or non-addressed speech into Jarvis diagnostic logs. Voice errors may be recorded as bounded exception messages. Credentials and provider tokens must never be included in voice logs.

## Installation

The base Jarvis Windows product is the single `Jarvis.exe` release asset. End users do not install a separate Backtalk repository. Development/build environments may install the optional voice dependencies needed to produce the executable.
