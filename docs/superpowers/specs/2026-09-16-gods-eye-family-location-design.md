# God’s Eye Authorized Family Location Integration

## Status
Approved direction for implementation on `feature/persistent-workflows`.

## Goal
Add an optional family-location overlay to God’s Eye that can display authorized family-member locations, report source/update freshness, and follow a selected member as new authorized location updates arrive.

## Provider boundary
Jarvis must not reverse-engineer, scrape, bypass, or impersonate Life360 APIs, authentication, private endpoints, or access controls. The integration exposes a provider-neutral `FamilyLocationProvider` interface and a Life360 adapter contract that accepts data from an authorized/official bridge or other permitted source. When no compliant Life360 data source is configured, the feature reports unavailable instead of fabricating locations.

## Data model
`FamilyLocation` contains stable member identifier, display name, latitude, longitude, accuracy meters when available, source name, observed-at timestamp, provider freshness timestamp when available, and sharing/availability state. It never stores credentials or private authentication artifacts.

## Runtime
Expose read-only family-location operations through the existing capability-aware runtime. Family-location reads must remain separate from current-device location writes. Any provider connection/setup operation goes through the existing account/confirmation boundary.

## God’s Eye surface
Provide list/get/refresh operations for authorized family members and a follow-state controller. The map surface receives structured markers rather than direct provider UI scraping. A followed member is re-centered only when a newer authorized location update is received. Stale data remains visible but is labeled stale with its timestamp; absence or paused sharing is not converted into a live location.

## Natural language
Recognize deterministic forms such as `where is <family member>`, `show <family member> on God’s Eye`, `show my family`, `follow <family member>`, and `stop following`. Ambiguous names must not guess.

## Persistence
Persist only provider configuration needed to select the authorized source and member aliases. Do not persist tokens, session cookies, browser profiles, or raw location history by default. A lightweight selected-follow target may persist only as a non-secret preference.

## Failure handling
Provider outages, revoked access, unavailable sharing, stale updates, malformed data, and unknown members are reported as non-fatal provider states. God’s Eye and the rest of Jarvis continue operating.

## Testing
Use TDD. Cover normalization, malformed payload rejection, stale-state handling, member resolution/ambiguity, follow-state transitions, refresh behavior, and runtime capability/confirmation boundaries. Include a provider contract test using deterministic fixtures so CI never depends on Life360 network access or a real family account.

## Compatibility
The feature is optional and lazy. No new third-party dependency is required for import or baseline tests. Existing God’s Eye location behavior remains unchanged when no family provider is configured.
