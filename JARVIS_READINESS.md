# Jarvis Readiness

Run `python readiness.py` from the repository root to inspect whether the required runtime pieces for the Jarvis extensions are configured.

The readiness gate is intentionally diagnostic rather than invasive. It checks the Python runtime, Git, supported cloud-provider key presence, optional God’s Eye and browser dependencies, ElevenLabs configuration, the cloud coding CLI, the cloud multi-AI orchestration contract, and the universal tool-broker contracts.

The orchestration layer uses OmniRoute for cloud model routing, selects fast/smart/coding/vision/maintenance profiles, and can parallelize independent read-only specialist requests within a bounded worker pool. Repeated provider failures are cooled down and missing credentials produce redacted diagnostics.

The universal tool broker supplies an extensible policy-aware path for configured web/API adapters. Web access is HTTPS-only and requires an explicit host allowlist. Generic API access requires explicit endpoint/path allowlists and resolves credentials from named environment variables without returning them to model-visible results. New adapters must declare operations, map them to existing capabilities, and pass the repository test/release gate before activation.

Readiness never prints secret values, changes environment variables, grants permissions, installs software, performs Windows mutations, or changes the existing deny-by-default capability policy.

Windows system diagnosis and repair are separate readiness concerns: diagnosis is read-only; repair remains confirmation-gated and is verified after execution where deterministic verification exists.

`READY` means the required runtime checks pass. Optional integrations may still show `WARN`; those warnings identify features that need local setup, permissions, credentials, or optional dependencies before they can be exercised on a particular machine.

Self-coding can now recognize explicit tool-capability failures and produce a structured extension proposal. That proposal is a repository task, not automatic permission escalation; activation still requires a declared capability, policy approval, tests, and the normal release gate.

Hosted CI verifies imports, routing, concurrency, policy boundaries, deterministic dispatch contracts, and broker boundaries. It cannot certify actual microphone/speaker playback, ElevenLabs voice quality, mouse movement, browser interaction, camera permission, external account OAuth, or the effect of Windows repairs on a particular PC.
