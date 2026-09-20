# Jarvis voice

Jarvis uses the embedded Backtalk input layer as its desktop voice interface. Kokoro Local is the default speech output, ElevenLabs remains optional, and the Jarvis runtime remains the only planner and tool-execution brain. New installs use a hands-free Live-like voice loop by default, with local VAD endpointing, speaker-output gating, and a physical push-to-talk barge-in path.

## Brain and routing

The supported agent brain is **OmniRoute only**. Claude Code and a Claude subscription are not required for Jarvis. Direct Claude routing is not a Jarvis fallback, and the supported disabled-override state is `JARVIS_ALLOW_CLAUDE=false`.

Jarvis uses OmniRoute for conversational and agent routing. The desktop host probes the configured local OmniRoute gateway at startup and before the first typed request. When the gateway is not already running, Jarvis starts the installed `omniroute --no-open` command without a visible console and waits for its health endpoint. Jarvis does not silently install OmniRoute or download an unpinned gateway executable.

A missing or unavailable OmniRoute installation is reported as a bounded routing error rather than silently selecting another agent brain.

## Default Backtalk settings

On first normal startup Jarvis creates `%LOCALAPPDATA%\\Jarvis\\backtalk.json` when it does not already exist. The current defaults are:

```text
name=JARVIS
ptt_key=home
mic_mode=open
voice=bm_lewis
stt_model=small.en
stt_device=cpu
stt_compute=int8
```

The exact active values are loaded from the local Backtalk configuration and supported `JARVIS_*` environment settings. Legacy `stt_device=auto` settings, and the incompatible CPU `float16` combination, are migrated to stable CPU `int8` settings unless an explicit `JARVIS_STT_DEVICE` override is present.

## Activation behavior

The default desktop configuration uses Backtalk hands-free listening. Local VAD decides when an utterance starts and ends, while the microphone is speaker-gated during Jarvis playback so ordinary speakers do not feed Jarvis its own voice. When an active voice session is running, the voice bridge passes recognized speech into the existing `JarvisDesktopController`, which routes the request through the normal Jarvis orchestration and capability policy.

The centered Jarvis visual remains the primary interaction surface. The text link is normally hidden and is revealed by hovering over the transparent center hit zone that tracks the canvas-drawn Jarvis element; moving onto the revealed field keeps it active. Typed text goes directly to the `JarvisDesktopController`, never through microphone, speech-recognition, or speech-output code.

While the text field has focus, Space inserts a normal space and does not trigger the visualizer's cinematic shortcut. When the text field is not focused, the existing visualizer Space shortcut remains untouched.

Mutating requests are still confirmation-gated. Voice input cannot bypass confirmation, permissions, cancellation, or the deny-by-default capability policy.

Push-to-talk remains available by setting `JARVIS_MIC_MODE=ptt` or `mic_mode=ptt`. In the default hands-free mode, the configured PTT key is also an immediate barge-in control: pressing it cuts current speech and records the next held-key utterance through the same Jarvis controller. This gives interruption behavior without unsafe automatic speaker-echo barge-in.

## Speech output and shutdown

**Kokoro Local is the default Jarvis speech-output engine.** Backtalk remains the microphone/speech-input and push-to-talk layer; it is not used as the desktop speech mouth. ElevenLabs remains an optional output engine, and the Jarvis voice bridge injects exactly one active mouth at a time with one deduplication/cancellation boundary.

Jarvis must never store or save the ElevenLabs API key in tracked files or committed configuration.\n\nCredential resolution is explicit: `ELEVENLABS_API_KEY` is accepted only as a runtime environment override; otherwise Jarvis reads the `Jarvis` / `ElevenLabs` entry from the OS credential store. Neither path writes the secret to tracked configuration, command-line arguments, or diagnostic logs.\n\nThe combined AI Provider / Voice Settings surface is available from the shared UI layer used by every UI build. Paste the ElevenLabs API key once, choose the configured/default voice, and use **SAVE & TEST VOICE**. The secret is stored through the Windows credential store via `keyring`; the JSON voice settings contain only non-secret voice/model identifiers.

The default free voice is **Kokoro 82M** with the `bm_lewis` voice, while the optional ElevenLabs path supports Conversational v3 and Flash v2.5 when a paid account is configured. The voice selector can load the voices available to the configured ElevenLabs account. Jarvis's response model is separately guided toward a calm, precise, discreetly formal dialogue style before speech synthesis.

The WebView is the audio sink: Jarvis passes only short-lived, browser-playable audio packets to the native UI, so normal speech playback requires no visible console. The Live-like path keeps the existing sentence-streamed mouth and cancellation boundary instead of introducing a second audio process.

ElevenLabs is an output engine only. It never becomes the agent planner or tool executor and never changes the OmniRoute-only brain boundary.

Before the voice listener begins live microphone work, Jarvis performs a speech-recognition preflight against the actual embedded Backtalk `warm()` path. A preflight failure disables only voice input and retries later; the Fullstack visualizer and text link remain available. This keeps ordinary STT/model/device initialization failures out of the desktop application's startup path.

The ElevenLabs audio workers are stopped and joined during Jarvis exit. The WebView audio queue is cleared as part of voice shutdown. This keeps the single speech-output path from racing desktop shutdown.

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
