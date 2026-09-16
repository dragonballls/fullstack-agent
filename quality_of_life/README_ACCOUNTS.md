# Jarvis Accounts & Services

Jarvis can be extended with multiple external identities without making provider credentials part of the agent's prompt, repository, or logs.

## Account model

Each connected identity is represented by non-secret metadata: provider, account ID, display label, and authorization state. Multiple identities for the same provider are supported. When more than one connected account matches a request, Jarvis requires an explicit account label or ID instead of guessing.

Passwords are never collected by Jarvis. Account connection uses the provider's OAuth authorization flow and user consent. OAuth client IDs are configuration values; client secrets and refresh/access tokens belong in the external credential/token broker.

## Permission model

Connecting an account does not grant unrestricted control. A service operation must match:

1. the requested provider,
2. the selected account identity,
3. the local Jarvis account grant,
4. the provider OAuth scope, and
5. the existing capability/confirmation policy.

Read operations can be granted without per-call confirmation. Write, destructive, financial, and security-sensitive actions remain confirmation-gated by default.

## API-backed services

The current adapter contracts include representative read operations for:

- Google: Gmail profile metadata, Calendar event reads, and Drive file listing.
- Microsoft: signed-in profile, Outlook mail reads, Calendar reads, and OneDrive root listing through Microsoft Graph.
- YouTube: authenticated channel metadata through the YouTube Data API.
- GitHub: existing repository authorization/fork support.

Provider permissions are intentionally narrow. For example, Google publishes distinct OAuth scopes for Gmail, Calendar, Drive, Docs, Sheets, Slides, and other APIs; Jarvis should request only the scopes required for an operation. Microsoft Graph similarly exposes delegated permissions per resource. See the providers' current documentation before enabling additional scopes.

## Browser fallback

Some services expose capabilities that are not represented by an API adapter. Jarvis may use the existing browser-control subsystem as a bounded fallback when a user has explicitly enabled browser control and approved the target domain/action. Browser automation does not silently convert an existing browser login into unrestricted account authorization; the normal browser and account policy still applies.

An unsupported API operation is reported as unsupported rather than being guessed.

## Provider setup

Google requires an OAuth client configuration with a client ID supplied through `JARVIS_GOOGLE_CLIENT_ID`. Microsoft uses `JARVIS_MICROSOFT_CLIENT_ID` and its authorization-code flow. Hosted CI verifies these interfaces with mocked credentials; it cannot sign into a user's real accounts.

Real account connection remains an end-user step because the provider consent screen and account selection belong to the user. Revoked consent or expired credentials must produce a reauthorization state rather than silently retrying or falling back to another account.

## OmniRoute remains the brain

These services are tools and identities available to Jarvis. They do not introduce Claude Code or another model runtime. Jarvis's model routing remains OmniRoute-only.
