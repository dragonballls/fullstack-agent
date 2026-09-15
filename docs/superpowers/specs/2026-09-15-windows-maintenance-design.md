# Windows Maintenance Safety Design

**Goal:** Give the installed Jarvis agent a safe Windows maintenance capability for diagnostics, background-process cleanup, startup prevention, and guarded repair operations without coupling it to the existing QOL, God’s Eye, OmniRoute, voice, or self-coding implementations.

## Safety contract

- Read-only diagnostics never mutate the machine.
- Process cleanup protects Windows/system processes, security tooling, Jarvis/agent processes, the foreground application, and processes running from protected system locations.
- A process is only eligible for cleanup when it is an ordinary user application and resource evidence is sufficient; vague "clean everything" language never authorizes killing processes.
- Startup prevention only changes reversible per-user startup entries supported by the adapter. It does not disable Windows services, scheduled tasks, drivers, antivirus, or system startup components.
- Mutations are policy-gated, explicitly attributable to a user request, and verified after execution.
- High-risk repairs such as DISM/SFC remediation or Winsock reset are never inferred from vague requests; they require an explicit confirmation hook.
- Maintenance failures are contained per check/action and never abort the base agent.
- Non-Windows hosts import the package successfully and report unsupported operations instead of crashing.

## Capability surface

The subsystem supports: `diagnose`, `list_processes`, `recommend_cleanup`, `stop_process`, `list_startup`, `disable_startup`, `restore_startup`, `system_file_scan`, `system_file_repair`, and `network_reset`.

The natural-language facade recognizes common requests such as "diagnose my PC", "what is using my RAM", "clean up background apps", "stop Steam and stop it from starting with Windows", and "repair Windows". It creates structured actions rather than executing arbitrary shell commands.
