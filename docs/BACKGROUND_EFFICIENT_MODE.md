# Jarvis background-efficient mode

`JarvisBackgroundRuntime` provides the lifecycle contract for a desktop host.

- `start()` starts the local wake listener.
- `minimize()` enters low-overhead presentation mode without stopping voice or an active hand-control runtime.
- `restore()` resumes foreground presentation components.
- `stop()` stops the voice listener and hand-control runtime cleanly.

The final native desktop host must connect its window minimize/restore/close callbacks to these methods. This repository is the Jarvis integration/source layer and does not contain the native desktop shell itself.
