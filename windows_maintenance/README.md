# Windows Maintenance

Optional, Windows-only PC maintenance for the installed Jarvis agent.

## Safe capabilities

- Diagnose CPU, memory, disk, GPU, network, Windows update services, problem devices, and recent System errors.
- List running processes and identify **eligible user applications** that are high-memory or unresponsive.
- Protect Windows/system/security processes, Jarvis/agent processes, the foreground process, and protected system paths.
- Stop an explicitly requested user application only after verifying the PID and process name.
- Inspect startup entries and disable only reversible current-user `Run` entries, so an application such as Steam can be prevented from launching automatically without disabling services or scheduled tasks.
- Restore a previously removed user startup entry.
- Scan Windows system files without repair.
- Run DISM/SFC remediation or Winsock reset only with an explicit confirmation supplied by the caller; these are high-risk operations.

The subsystem never accepts arbitrary PowerShell from the model, never persists secrets, and isolates failures so one broken Windows check does not take down the agent.
