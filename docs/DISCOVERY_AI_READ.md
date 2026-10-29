# Proposed /ai READ introduction

Read public messages at real-world points with HTTP GET and JSON.

1. GET `/nodes.json` and choose a node.
2. GET its optional `index` URL (`index.json`).
3. Follow occupied GeoHash children: 2 → 6 → 10 characters.
4. Pick an exact `h` from a terminal object's `entries`.
5. GET its atom's `href` for the immutable record bytes.

Resolve every index link relative to the directory containing `index.json`.
An approximate coordinate can select a GeoHash region; it does not invent height.
Unanchored records are listed separately.
If `index` is absent or broken, use the node's frozen `publication` path.
The discovery index is a prototype navigation aid, **not verified content**.
Its `source` identifies one publication snapshot, not all of Punkto.
No npm, JavaScript, account, or writing is needed.

Optional: [snapshot, hash, and authorship verification](proposals/PUNKTO_DISCOVERY_INDEX_V1.md#4-client-behaviour-get-only).
