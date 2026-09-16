# Jarvis webcam hand control

Jarvis can optionally use a webcam for hands-free pointer control through the existing guarded computer-control layer. It is disabled until explicitly started.

## Controls

- One raised finger: move the Windows pointer.
- Pinch and release: left click.
- Pinch and hold: press-and-drag; releasing the pinch releases the button.
- Two fingers moving vertically: bounded scrolling.
- Closed fist held briefly: pause immediately after debounce.
- Open palm held briefly: resume after pause.
- `Esc` or **Stop hand control**: stop the bridge and release any held mouse button.

The browser sends only normalized hand coordinates/gesture state to the loopback bridge at `127.0.0.1:8795`. Camera frames are processed by the browser-side tracker; they are not uploaded by Jarvis's hand-control server.

The local bridge has a watchdog. If hand samples stop arriving, Jarvis releases any held button and disables hand control rather than leaving a drag active.

The feature is optional and isolated. A missing camera, denied browser permission, missing tracking script, or failed local bridge becomes a degraded state without preventing Jarvis core startup.

The tracker uses the existing `barehands`/MediaPipe browser approach instead of adding a second local vision engine. The physical webcam privacy indicator and normal Windows camera permissions remain in control of camera access.
