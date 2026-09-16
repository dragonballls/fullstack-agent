# Jarvis Workflows and Family God’s Eye

## Named workflows

Save the last supported task with `remember that as <name>`. Later, including after a restart, invoke it with `do my <name>`, `run my <name>`, `do <name>`, or `run <name>`.

Workflows are stored locally and contain only approved operation names plus JSON arguments. Protected operations still require the current Jarvis capability policy and confirmation state at execution time.

Default store: `~/.jarvis/workflows.json`. Override with `JARVIS_WORKFLOW_STORE`.

## Family God’s Eye

The family-location layer accepts normalized data from an authorized provider bridge. Configure `JARVIS_LIFE360_BRIDGE_URL` to an HTTP(S) JSON bridge that you are authorized to use.

Supported commands:

- `where is <family member>`
- `show <family member> on God’s Eye`
- `show my family`
- `follow <family member>`
- `stop following`

Locations include provider/update freshness and sharing state. A followed member is recentered only when a newer authorized update arrives.

The Life360 adapter intentionally does not scrape private application endpoints or bypass authentication or sharing controls. A real Life360 account/feed must provide the authorized bridge data; CI uses fixtures instead.
