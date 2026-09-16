# Jarvis External Integrations

Jarvis can use selected capabilities from the requested external projects without making them hard runtime dependencies.

## Active bridges

**Archify** — cataloged as the architecture-visualization skill. Jarvis can invoke the Archify skill when the `skills` CLI/agent environment is present; the core Windows executable does not require Node or Archify to start.

**Hindsight** — exposed through `HindsightMemoryBridge`. Set `JARVIS_HINDSIGHT_URL` to an explicitly authorized Hindsight HTTP service. The bridge supports bounded `retain` and `recall` requests and never stores credentials in Jarvis configuration.

**OpenClaude** — exposed through `OptionalAgentLauncher` as an optional external coding-agent harness. Jarvis only detects and queries an explicitly installed executable and never runs a shell command string.

**go-modern-guidelines** — cataloged as guidance for Go projects. It is advisory and does not change Jarvis's Python runtime.

**scientific-agent-skills** — cataloged as an optional research skill library. It remains outside the core startup path so scientific-specific dependencies cannot break the desktop application.

## Windows-only boundary

`omarchy` and `radiant` are retained as platform references rather than bundled into the Windows executable. They are not startup dependencies.

## Safety and failure behavior

External integrations are opt-in. Missing tools, missing environment variables, unavailable servers, invalid JSON, and external command failures are surfaced as integration-level errors instead of preventing Jarvis from launching.

No external integration bypasses Jarvis capability policy, confirmation, emergency-stop, self-coding verification, credential brokering, or browser restrictions.
