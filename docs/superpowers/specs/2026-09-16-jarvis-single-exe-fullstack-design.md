# Jarvis Single-EXE Fullstack Design

**Goal:** Replace the current minimal Tk launcher with a verified Windows executable that presents the original Fullstack Agent experience—living face, voice, and optional hands—while preserving the existing guarded Jarvis cloud brain and capability layer.

## Root cause

The current Windows executable is built from `scripts/jarvis_desktop.pyw`, whose UI is explicitly a 640x118 Tk chat bar with the hard-coded startup text `Jarvis is ready.`. The current packaging workflow only collects the Jarvis integration packages and therefore cannot contain the upstream Fullstack Agent's separate voice/face/hands components.

## Architecture

`Jarvis.exe` is the single distributable artifact. On build, the release workflow retrieves pinned upstream snapshots of `backtalk`, `ai-visualizer`, `barehands`, and `ai-memory-vault` and embeds the needed source/assets into the PyInstaller executable.

At runtime, the executable:

1. Creates the existing `JarvisRuntime` and `AgentOrchestrator`; this remains the only brain/tool execution path.
2. Starts the original `ai-visualizer` server contract in-process and hosts its faces in a native `pywebview` window, avoiding a second user-installed application.
3. Uses the upstream `backtalk` microphone/voice components for local speech capture, VAD, STT, waveform/status signals, and TTS, but replaces the upstream Claude brain boundary with an adapter to the existing Jarvis orchestrator so Jarvis remains OmniRoute-backed.
4. Exposes the existing guarded hand-control runtime through the same executable; enabling hand control remains explicit and fails closed when unavailable.
5. Stores user configuration and runtime state under `%LOCALAPPDATA%\\Jarvis`, never beside the executable, and keeps credentials outside tracked/bundled configuration.

The executable may use the user's existing default browser only for explicitly requested external web pages. The normal Jarvis presentation is native and does not depend on a browser tab.

## Packaging

The release workflow must pin upstream component commits, install all Windows runtime dependencies needed by the embedded voice/UI modules, build with PyInstaller `--onefile --windowed`, run static/import checks, run the complete regression suite, start the packaged executable on a Windows runner, verify the embedded visualizer endpoint, and confirm the process remains alive after initialization.

The GitHub Release should publish the verified `Jarvis.exe` directly as the primary Windows asset. Source ZIPs remain development/recovery artifacts and are not the user-facing Windows download.

## Failure handling

If an optional hardware integration is unavailable, Jarvis remains usable through its text/cloud path and the visualizer shows a clear degraded state rather than opening the old Tk fallback. If a required startup component fails, the executable writes a sanitized log under `%LOCALAPPDATA%\\Jarvis\\logs` and displays a native error dialog; it must never silently substitute the old compact chat bar.

## Verification boundary

Hosted CI can verify imports, packaging, process startup, embedded visualizer serving, and non-hardware unit tests. It cannot prove a particular user's microphone, speakers, webcam, GPU driver, cloud credential, account OAuth, or external browser profile. Local machine readiness remains a separate gate, but those machine-specific dependencies must not cause the packaged executable to regress into the old tiny Tk launcher.
