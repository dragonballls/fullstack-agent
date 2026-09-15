# Jarvis voice

The preferred high-quality cloud voice for the Jarvis setup is ElevenLabs.

## Default setup

During the `backtalk` setup, choose **ElevenLabs** rather than the built-in Kokoro voice. The backtalk maintainer documents the natural ElevenLabs path and identifies **Tarquin** as the voice used in the project author's videos.

Do not store an ElevenLabs API key in this repository. On Windows, provide the key through the supported `ELEVENLABS_API_KEY` environment variable or the credential mechanism supported by the installed backtalk version.

## Jarvis quality + latency profile

Prioritize a natural, consistent speaking voice without adding unnecessary generation latency:

- Prefer an ElevenLabs low-latency model supported by the installed backtalk release when it offers the required voice quality.
- Start around **stability 0.50**, **similarity 0.75**, **style 0**, and **speed 1.0**, then audition and adjust by ear.
- Keep speaker boost off when the extra similarity is not needed because it adds processing cost; enable it only when the actual voice test benefits.
- Do not hard-code a voice ID. Look up the requested voice in the account's voice library so stale IDs cannot silently select the wrong voice.

These are starting points, not a claim that one setting is universally optimal. The real speech audition remains the authority for the final configuration.

## Reliability

The voice setup must:

1. Verify the ElevenLabs credential before completing setup.
2. Select the requested Tarquin voice by looking it up in the ElevenLabs voice library rather than hard-coding an unknown voice ID.
3. Perform an actual speech test before declaring voice setup complete.
4. Keep the existing Kokoro voice configured as the automatic fallback so a temporary cloud failure does not make the assistant silent.
5. Never print the API key or write it into tracked files.
6. Preserve the existing push-to-talk/open-listening mode selected during setup; orchestration speed improvements must not silently change microphone behavior.

The fullstack-agent installer should read this file before configuring backtalk's voice. It should never claim the Jarvis voice is working until the real speech test succeeds.
