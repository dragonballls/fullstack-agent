# Jarvis download and release contract

## What this repository is

`dragonballls/fullstack-agent` contains the Jarvis integration layer: cloud routing, guarded computer/browser/system capabilities, self-coding, accounts, voice contracts, God’s Eye, Windows maintenance, and webcam hand control.

The Windows desktop experience is packaged as a native `Jarvis.exe`. The executable is a presentation host around the existing guarded Jarvis runtime; it does not replace or bypass the capability policy, confirmation gates, or orchestrator.

## Supported downloadable artifacts

The `Jarvis full release gate` GitHub Actions workflow verifies the complete test suite and builds a native Windows package on `windows-latest` with PyInstaller. The verified Windows artifact is `Jarvis-Windows.zip`, containing `Jarvis.exe`.

The same workflow continues to produce `Jarvis-Source-Bundle.zip` for source-based development and recovery.

Tagged releases (`vMAJOR.MINOR.PATCH`) publish both verified downloads to the GitHub release automatically.

## Windows runtime

For the packaged application, extract `Jarvis-Windows.zip` and run `Jarvis.exe`. No persistent PowerShell window is required.

For development builds from a local clone, run `scripts\build-jarvis-exe.ps1` to produce `dist\Jarvis.exe`. The supported convenience launcher `scripts\start-jarvis.ps1` starts that packaged executable.

`start.bat` is retained for the upstream fullstack-agent multi-repository stack and is not the Jarvis runtime launcher.

The desktop host intentionally presents only a compact chat bar and delegates requests to the existing guarded `JarvisRuntime` and `AgentOrchestrator`. It does not create a second tool executor or bypass confirmation and capability policy.

## Runtime requirements that cannot be certified by hosted CI

A packaged executable still depends on machine- and account-specific pieces that the code intentionally does not fake:

- a configured cloud model gateway/credential for live AI requests;
- user-granted microphone/camera permissions for voice or hand control;
- the actual Windows desktop/browser environment for computer-control behavior;
- provider credentials and user consent for account integrations;
- a configured repository and supported cloud coding backend before self-coding can run;
- any external browser binaries required by the selected browser automation configuration.

The readiness command remains the authoritative local diagnostic for a source checkout:

```text
python readiness.py
```

`READY` means the required local checks passed. Optional integrations may still report `WARN`; those warnings are not silently converted into success.

## What the executable does and does not imply

`Jarvis.exe` means the Windows presentation host and its Python runtime are packaged together. It does **not** mean cloud credentials, user OAuth consent, browser profiles, microphone/camera access, or third-party services have been bundled or pre-authorized.
