# Jarvis Readiness

Run `python readiness.py` from the repository root to inspect whether the required runtime pieces for the Jarvis extensions are configured.

The readiness gate is intentionally diagnostic rather than invasive. It checks the Python runtime, Git, supported cloud-provider key presence, optional God’s Eye and browser dependencies, ElevenLabs configuration, the cloud coding CLI, and the Jarvis multi-AI orchestration contract.

The orchestration layer uses OmniRoute for cloud model routing, selects fast/smart/coding/vision/maintenance profiles, and can parallelize independent read-only specialist requests within a bounded worker pool. Repeated provider failures are cooled down and missing credentials produce redacted diagnostics.

Readiness never prints secret values, changes environment variables, grants permissions, installs software, performs Windows mutations, or changes the existing deny-by-default capability policy.

Windows system diagnosis and repair are separate readiness concerns: diagnosis is read-only; repair remains confirmation-gated and is verified after execution where deterministic verification exists.

`READY` means the required runtime checks pass. Optional integrations may still show `WARN`; those warnings identify features that need local setup, permissions, credentials, or optional dependencies before they can be exercised on a particular machine.

Hosted CI verifies imports, routing, concurrency, policy boundaries, and deterministic dispatch contracts. It cannot certify actual microphone/speaker playback, ElevenLabs voice quality, mouse movement, browser interaction, camera permission, or the effect of Windows repairs on a particular PC.
