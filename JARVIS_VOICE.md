# Jarvis voice

The preferred high-quality cloud voice for the Jarvis setup is ElevenLabs.

## Default setup

During the `backtalk` setup, choose **ElevenLabs** rather than the built-in Kokoro voice. The backtalk maintainer documents the natural ElevenLabs path and identifies **Tarquin** as the voice used in the project author's videos.

Do not store an ElevenLabs API key in this repository. On Windows, provide the key through the supported `ELEVENLABS_API_KEY` environment variable or the credential mechanism supported by the installed backtalk version.

## Reliability

The voice setup must:

1. Verify the ElevenLabs credential before completing setup.
2. Select the requested Tarquin voice by looking it up in the ElevenLabs voice library rather than hard-coding an unknown voice ID.
3. Perform an actual speech test before declaring voice setup complete.
4. Keep the existing Kokoro voice configured as the automatic fallback so a temporary cloud failure does not make the assistant silent.
5. Never print the API key or write it into tracked files.

The fullstack-agent installer should read this file before configuring backtalk's voice. It should never claim the Jarvis voice is working until the real speech test succeeds.
