# Jarvis download and release contract

## What this repository is

`dragonballls/fullstack-agent` contains the Jarvis integration layer: cloud routing, guarded computer/browser/system capabilities, self-coding, accounts, voice contracts, God’s Eye, Windows maintenance, and webcam hand control.

It is **not** currently a standalone native Windows `.exe`. The upstream fullstack stack also consists of separately maintained sibling components such as memory, voice, face, and optional hands. A ZIP of this repository alone must not pretend those external components are bundled.

## Supported downloadable artifact

The repository now has a `Jarvis full release gate` GitHub Actions workflow. A successful run produces `Jarvis-Source-Bundle.zip` containing the repository source needed for the Jarvis integration layer.

The bundle is built only after the complete unittest suite, Windows-maintenance tests, Python compilation checks, and a post-extraction bundle integrity check pass on the release gate.

Tagged releases (`vMAJOR.MINOR.PATCH`) publish the same verified source bundle to the GitHub release automatically.

## Background-efficient desktop behavior

Desktop hosts can use `JarvisBackgroundRuntime` for minimize/restore lifecycle integration. Minimize enters a low-overhead presentation state: foreground-only rendering, animation, timers, and polling can be suspended while local voice wake listening remains alive and an explicitly active hand-control runtime is not stopped. Restore resumes the foreground presentation layer. Quit calls `stop()` and shuts down the background services.

This is **resource reduction, not zero-resource execution**. Active microphone listening and active hand tracking necessarily consume some CPU/RAM. The integration layer exposes these lifecycle semantics without claiming that this source repository contains the final native desktop window implementation.

## Runtime requirements that cannot be certified by hosted CI

A downloaded bundle still requires the machine-specific pieces that the code intentionally does not fake:

- a supported Python runtime (3.11–3.13 is the tested range);
- a configured cloud model gateway/credential for live AI requests;
- user-granted microphone/camera permissions for voice or hand control;
- the actual Windows desktop/browser environment for computer-control behavior;
- provider credentials and user consent for account integrations;
- a configured repository and supported cloud coding backend before self-coding can run.

The readiness command is the authoritative local diagnostic:

```text
python readiness.py
```

`READY` means the required local checks passed. Optional integrations may still report `WARN`; those warnings are not silently converted into success.

## Why there is no fake `.exe`

Packaging a small Python diagnostic into an executable would not make the complete Jarvis assistant standalone. The runtime intentionally depends on user configuration, guarded capabilities, external cloud services, and optional hardware. The release system therefore publishes the verified source bundle rather than labeling an incomplete wrapper as the full Jarvis application.
