# Jarvis self-update design

## Goal
When verified Jarvis self-coding changes reach `main`, the installed Windows `Jarvis.exe` should automatically move to the corresponding CI-built executable without requiring a manual reinstall.

## Flow
1. Self-coding works in a clean Git clone and runs the configured verification suite.
2. A successful pass may publish to `main` only when the remote `main` still equals the verified baseline, preventing accidental overwrites of concurrent changes.
3. The Windows release gate builds a one-file `Jarvis.exe`, smoke-tests it, and publishes the successful executable to a rolling GitHub `latest` release.
4. The installed executable periodically checks the public `latest` release metadata and compares the release commit identifier with its embedded/current build identifier.
5. Before replacement, the updater downloads `Jarvis.exe` to a temporary file and verifies its SHA-256 against the release asset digest recorded by the workflow.
6. The running app launches a hidden temporary updater command, exits, and the updater waits for the old process to disappear before atomically replacing the executable and relaunching it.
7. Failed downloads, mismatched hashes, missing assets, or replacement errors leave the currently running version untouched.

## Compatibility and guardrails
- The final downloadable release remains one `Jarvis.exe` file.
- No visible PowerShell or console window is required for normal updates.
- Existing runtime, voice, visualizer, hand-control, memory, permissions, and self-coding contracts remain unchanged.
- Self-coding never bypasses tests or remote-`main` concurrency checks.
- Update polling is disabled in smoke-test mode and can be configured by environment variables for diagnostics.
- The updater only accepts HTTPS GitHub release URLs for the configured repository.

## Verification
Unit tests cover release parsing, update eligibility, SHA-256 verification, update command construction, and safe failure behavior. The Windows release gate additionally verifies that the packaged executable starts and that the embedded visualizer becomes ready before publishing the rolling release.
