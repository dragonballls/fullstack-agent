# Jarvis Windows download

## The Windows product

The supported Windows product is **one file: `Jarvis.exe`**.

That executable contains the Jarvis runtime and the embedded Fullstack Agent presentation layer used for the living face and voice experience. The existing guarded Jarvis runtime remains the single planner/tool execution path; the embedded upstream voice and visualizer components do not introduce a second brain.

## Download

Use the `Jarvis.exe` asset attached to a verified GitHub Release. There is no Windows ZIP to extract and no source bundle required for normal use.

## What is inside the executable

The release build embeds the pinned Fullstack Agent components used for the face, voice I/O, optional hand-control presentation assets, and memory integration. The build also includes the Jarvis quality-of-life capabilities, self-coding subsystem, account integrations, God’s Eye/location layer, and Windows maintenance layer that are part of this repository.

At startup, Jarvis opens its native Fullstack visualizer window. It must never silently fall back to the old 640-by-118 Tk chat bar.

## Machine-specific setup

The executable cannot honestly bundle or pre-authorize things that belong to the user or machine. Live cloud requests still require the configured Jarvis model gateway/credential; microphone, speaker, and camera features require Windows permissions and working hardware; account integrations require the user's provider authorization; and self-coding requires a configured repository/backend.

Those are runtime capability gates, not reasons to ship a second installer. When an optional device or service is unavailable, Jarvis keeps the main application running and reports the degraded capability instead of replacing the Fullstack interface.

## Development build

For repository developers only, `scripts\build-jarvis-exe.ps1` produces the same single-file `dist\Jarvis.exe` layout used by the release pipeline. `scripts\start-jarvis.ps1` launches that executable without opening a persistent PowerShell console.

The upstream multi-repository `start.bat` remains in the source tree for compatibility with the original project, but it is not the Jarvis Windows product launcher.
