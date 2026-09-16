# Jarvis

A cloud-routed Jarvis-style agent with local wake-word voice activation, guarded computer control, self-coding, and explicit external-account integrations.

## Brain

**OmniRoute only.** Claude Code and a Claude subscription are not required by the Jarvis profile and are not valid fallback brains.

## Voice

Jarvis can remain always listening locally after microphone permission is granted. A local wake-word detector listens for the supported `hey_jarvis` model. Ambient speech does not create an AI request. Repeated detections are debounced and only one active voice session is allowed.

The conversational path is:

`local microphone -> local wake word -> speech transcript -> Jarvis orchestration -> OmniRoute -> existing tools/permissions -> speech output`

ElevenLabs and Kokoro are speech-output engines only.

The base QOL dependencies stay unchanged. Optional Windows voice dependencies are listed in `quality_of_life/voice_requirements.txt`.

## Accounts & Services

Jarvis supports a unified, scoped account model for multiple identities per provider. Current service contracts include Google, Microsoft, GitHub, YouTube, Instagram, and generic web services.

Accounts use explicit OAuth/user consent rather than passwords. Credentials and refresh tokens remain behind a runtime credential broker and are never committed, logged, or returned as model-visible results.

Read operations can be authorized by scope. Mutating, destructive, financial, and security-sensitive operations require confirmation by default. When more than one account matches, Jarvis must select by explicit account label or ID instead of guessing.

Provider APIs are preferred when they support the requested operation. Browser automation is a bounded fallback behind the existing browser/domain and permission controls. Unsupported operations are reported honestly rather than guessed.

See `quality_of_life/README_ACCOUNTS.md` for the current account integration contract.

## Existing Jarvis capabilities

- Guarded Windows mouse/keyboard/window/app control
- Local webcam hand control
- Browser automation
- Screen and clipboard access
- Saved locations and God’s Eye context
- Windows diagnostics and maintenance
- Cloud multi-AI routing through OmniRoute
- Guarded autonomous self-coding with verification and rollback
- Multi-account OAuth/service integration

Capabilities remain deny-by-default where required, and external accounts never bypass local safety policy.

## Setup

For the Jarvis profile, use `JARVIS_SETUP.md`. The legacy `fullstack-agent.md` file is retained for the upstream fullstack-agent workflow and is not the Jarvis runtime/setup contract.

## Verification

The repository uses GitHub Actions for QOL, integration, self-coding, and Windows-maintenance regression gates. Real microphone, speaker, browser-login, OAuth-consent, and third-party account behavior still require testing on the target Windows machine.

## License

Licensed under the GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later). See `LICENSE` for the complete terms.
