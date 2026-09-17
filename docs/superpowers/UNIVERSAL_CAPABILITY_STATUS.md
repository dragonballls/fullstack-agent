# Universal Capability Integration Status

**Status: implemented on the canonical `main` branch.**

The universal capability layer is part of the current Jarvis profile. The repository contains the policy-aware capability catalog, guarded tool broker, computer/browser operations, file and system operations, scheduling/workflows, phone/device adapters, self-coding integration, location/God's Eye context, and Windows-maintenance integration used by Jarvis.

## Current verification

Canonical `main` is currently at commit `41bd9db9c8ee86e906e8e64b74c04824dc56e546`.

The current Jarvis full release gate for that commit passed the six-environment regression matrix (Ubuntu and Windows with Python 3.11, 3.12, and 3.13), compilation and complete unit-test execution, Windows-maintenance tests, pinned Fullstack component acquisition, native dependency checks, single-file `Jarvis.exe` packaging, frozen visualizer smoke testing, packaged native-host smoke testing, and artifact publication.

The repository also has dedicated tests for capability policy, universal capabilities, the tool broker, integrations, workflows, computer use, accounts, hand control, voice, location/God's Eye, phone devices, self-coding, self-update, and Windows maintenance.

## Important distinction

This status describes repository and release readiness. It does not claim that machine-specific resources are already authorized or physically working on every computer. Microphone/speaker hardware, camera permissions, browser installations, cloud/provider credentials, OAuth grants, Android connection state, and the effects of Windows maintenance actions remain environment-specific and are intentionally handled through readiness checks, capability policy, confirmation gates, and explicit degraded states.

The precise Life360/family-member live-location feature discussed in earlier development was not promoted into the verified Jarvis product. Generic user-authorized location/God's Eye context remains supported; historical location branches must not be treated as an active implementation requirement.

## Historical plans and branches

Files under `docs/superpowers/plans/` and old feature branches are development history. Their unchecked planning boxes or older branch names do not mean the current canonical implementation is unfinished. The source of truth is the code on `main` plus the passing release gate and release artifact associated with it.
