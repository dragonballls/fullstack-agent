# Jarvis UI Build System

## Purpose

Jarvis now has a persistent UI build catalog that lets multiple presentation builds coexist without replacing the existing Fullstack desktop host.

The base layer remains authoritative:

- the existing Fullstack visualizer
- the existing Jarvis command bar
- the existing voice, hands, backend, permissions, updater, and agent runtime

A UI build is an additive presentation overlay. Switching builds changes only that overlay.

## Storage

On Windows builds are stored under:

`%LOCALAPPDATA%\Jarvis\ui-builds\`

Each build has its own directory:

`<build-id>\manifest.json`
`<build-id>\style.css`
`<build-id>\index.html`
`<build-id>\script.js`

There is no hard-coded build-count limit. The practical limit is available local storage.

Active-build state and rollback history are stored in `state.json`.

## Built-in builds

The first launch seeds:

- `workspace-default` — current UI, unchanged
- `minimal-command` — original visualizer plus command bar, with the optional workspace overlay hidden
- `status-hud` — current UI plus a small non-interactive status HUD

Built-ins are protected and cannot be overwritten or deleted.

## Creating a build

Open **UI BUILDS** in Jarvis and choose **NEW**. A build has an ID, name, version, description, CSS, optional HTML markup, and optional JavaScript.

Markup is deliberately restricted from embedding scripts, frames/objects, inline event handlers, or `javascript:` URLs.

Saved builds are inactive until selected.

## Switching and rollback

Selecting **USE** activates a build immediately. The previous active build is recorded in rollback history.

**ROLLBACK** returns to the previous valid build. If history is exhausted, Jarvis returns to `workspace-default`.

If a selected build's runtime script throws during activation, Jarvis removes that build's presentation layer and automatically rolls back to the previous build.

If a persisted active build fails during startup, Jarvis also rolls it back instead of allowing the optional UI layer to prevent the base Jarvis interface from loading.

## Design rule

New UI work should be implemented as a new build or an update to a non-protected build rather than replacing the Fullstack host. This makes experimentation reversible and keeps the core agent independent from presentation changes.
