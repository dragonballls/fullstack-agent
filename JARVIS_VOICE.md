# Jarvis voice

Jarvis uses the embedded Backtalk voice I/O layer as its desktop speech interface. Backtalk handles microphone capture, speech recognition, push-to-talk/listening behavior, and speech output; the Jarvis runtime remains the only planner and tool-execution brain.

## Brain and routing

The supported agent brain is **OmniRoute only**. Claude Code and a Claude subscription are not required for Jarvis. Direct Claude routing is not a Jarvis fallback, and the supported disabled-override state is `JARVIS_ALLOW_CLAUDE=false`.

Jarvis uses OmniRoute for conversational and agent routing. The desktop host probes the configured local OmniRoute gateway at startup and before the first typed request. When the gateway is not already running, Jarvis starts the installed `omniroute --no-open` command without a visible console and waits for its health endpoint. Jarvis does not silently install OmniRoute or download an unpinned gateway executable.

A missing or unavailable OmniRoute installation is reported as a bounded routing error rather than silently selecting another agent brain.

## Default Backtalk settings

On first normal startup Jarvis creates `%LOCALAPPDATA%\\Jarvis\\backtalk.json` when it does not already exist. The current defaults are:

```text
name=JARVIS
ptt_key=home
mic_mode=ptt
voice=bm_lewis
stt_model=small.en
stt_device=cpu
stt_compute=int8
```

The exact active values are loaded from the local Backtalk configuration and supported `JARVIS_*` environment settings. Legacy `stt_device=auto` settings, and the incompatible CPU `float16` combination, are migrated to stable CPU `int8` settings unless an explicit `JARVIS_STT_DEVICE` override is present.

## Activation behavior

The default desktop configuration uses Backtalk push-to-talk behavior. When an active voice session is running, the voice bridge passes recognized speech into the existing `JarvisDesktopController`, which routes the request through the normal Jarvis orchestration and capability policy.

The centered Jarvis visual remains the primary interaction surface. The text link is normally hidden and is revealed by hovering over the transparent center hit zone that tracks the canvas-drawn Jarvis element; moving onto the revealed field keeps it active. Typed text goes directly to the `JarvisDesktopController`, never through microphone, speech-recognition, or speech-output code.

While the text field has focus, Space inserts a normal space and does not trigger the visualizer's cinematic shortcut. When the text field is not focused, the existing visualizer Space shortcut remains untouched.

Mutating requests are still confirmation-gated. Voice input cannot bypass confirmation, permissions, cancellation, or the deny-by-default capability policy.

An open-microphone mode is available through the supported Backtalk configuration. It still routes accepted transcripts through the same Jarvis brain and policy boundary.

## Speech output and shutdown

Kokoro is embedded as a local speech-output option. **ElevenLabs** is supported as an optional externally configured speech-output provider. When configured remotely, its credential is referenced through the supported secret/credential mechanism; `ELEVENLABS_API_KEY` must not be stored in tracked source, local diagnostic logs, or generated application reports. Never store or save an API key in the voice configuration itself.

Both Kokoro and ElevenLabs are output engines only; neither becomes an agent planner or tool executor, and neither changes the OmniRoute-only brain boundary.

Before the voice listener begins live microphone work, Jarvis performs a speech-recognition preflight against the actual embedded Backtalk `warm()` path. A preflight failure disables only voice input and retries later; the Fullstack visualizer and text link remain available. This keeps ordinary STT/model/device initialization failures out of the desktop application's startup path.

The embedded Backtalk mouth worker receives an explicit shutdown sentinel during Jarvis exit and is joined before the desktop host finishes cleanup. Its audio output stream is also closed on the normal exit path. This is intended to eliminate resource races that can leave PyInstaller's `_MEI...` extraction directory locked at process shutdown.

## Real speech test

A **real speech test** is a machine-level verification performed on the target Windows PC after installation. It checks the selected microphone, Windows audio permission, speech recognition model, speaker/output device, and spoken response path. Passing the hosted CI smoke test does not substitute for this physical-device check.

Microphone/speaker access is machine-specific. If audio initialization fails, Jarvis should keep the Fullstack visualizer running and log the degraded voice component rather than terminating the desktop application.

## Frozen-build verification

The Windows release gate explicitly embeds `backtalk/source` inside the PyInstaller bundle and runs a frozen-EXE smoke validation that resolves that embedded path and imports the Backtalk `Ears`, `Mouth`, and `PTTListener` contracts without requiring real microphone/speaker hardware.

That smoke check proves the packaged source/import contract. It does not prove a particular PC's audio hardware, Windows privacy settings, microphone permissions, or speech quality.

## Privacy and logging

The voice bridge must not write ambient room audio or non-addressed speech into Jarvis diagnostic logs. Voice errors may be recorded as bounded exception messages. Credentials and provider tokens must never be included in voice logs.

## Installation

The base Jarvis Windows product is the single `Jarvis.exe` release asset. End users do not install a separate Backtalk repository. Development/build environments may install the optional voice dependencies needed to produce the executable.
