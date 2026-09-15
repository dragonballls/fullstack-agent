# Jarvis Readiness

Run `python readiness.py` from the repository root to inspect whether the required runtime pieces for the Jarvis extensions are configured.

The readiness gate is intentionally diagnostic rather than invasive. It checks the Python runtime, Git, supported cloud-provider key presence, optional God’s Eye and browser dependencies, ElevenLabs configuration, and the availability of a supported cloud coding CLI.

It never prints secret values, changes environment variables, grants permissions, installs software, or changes the existing deny-by-default capability policy.

`READY` means the required runtime checks pass. Optional integrations may still show `WARN`; those warnings identify features that need local setup, permissions, credentials, or optional dependencies before they can be exercised on a particular machine.
