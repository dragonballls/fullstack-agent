# Hand-control implementation status

The Jarvis hand-control subsystem is implemented on `feature/jarvis-hand-control-v2` and proposed for `main` in PR #19.

Implemented: optional loopback webcam bridge; local browser-side MediaPipe tracking; one-finger pointer movement with dead-zone smoothing; pinch click; pinch-hold drag; two-finger bounded scrolling; debounced fist pause; open-palm resume; explicit Stop/Esc shutdown; tracking-loss watchdog; capability-gated desktop dispatch; degraded lifecycle states; deterministic headless tests; and documentation.

The feature is disabled until explicitly started. Core Jarvis startup does not require a webcam or camera/vision dependency.

Final completion gates: all six QOL CI jobs for Windows/Ubuntu Python 3.11-3.13 must pass, the PR must merge cleanly into `main`, and physical webcam behavior must be tested on the target Windows machine because CI cannot exercise the user's camera hardware.