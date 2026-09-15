# Universal Capability Integration Status

The universal capability layer is being integrated incrementally on `feature/windows-maintenance-v5`.

Implemented in this phase:

- Typed capability and risk catalog.
- Browser discovery and aliases, including Opera GX and Edge.
- Structured browser URL launching without shell execution.
- Guarded filesystem read/write/copy/move/delete operations.
- Installed Windows application inventory and confirmed uninstall with post-action verification.
- Guarded process and Windows service inspection/control.
- Structured system inspection and allowlisted user settings.
- Bounded delayed background scheduling.
- Natural-language intents for browser, files, applications, processes, and system inspection.
- Runtime registration of the new capability families.

The implementation is not considered complete until exact-head GitHub Actions verification is green and unsupported physical-device behavior is explicitly separated from hosted-CI guarantees.
