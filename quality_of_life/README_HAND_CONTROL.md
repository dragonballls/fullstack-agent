# Jarvis webcam hand control

Jarvis can optionally use a webcam for hands-free pointer control through the existing guarded computer-control layer.

## Controls

- Point with one raised finger: move the pointer.
- Pinch and release: left click.
- Closed fist: immediately pause hand control.
- `Esc` or **Stop hand control**: immediately stop the bridge.

The tracker sends only normalized hand coordinates and gesture state to the local loopback bridge at `127.0.0.1:8795`. The browser never receives or sends desktop-control credentials.

The feature is optional and isolated. If camera permission, MediaPipe loading, or the local bridge fails, Jarvis's core systems continue normally.

The webcam tracker uses the existing `barehands`/MediaPipe approach instead of adding a second local vision engine.
