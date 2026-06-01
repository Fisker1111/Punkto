# Sync fast-forward and atom log plan

This document defines the public-readiness storage and sync model. The first durable storage step is implemented: accepted public atoms are appended to `/data/atoms.log.jsonl` and the relay rebuilds its runtime feed buffer from that log on startup. Cursor, SQLite, and generated-cache work remain incremental follow-ups.

## Three-step public-readiness plan

### PR A — define atom log fast-forward protocol

Document the model for durable atom storage, public reads, feed cursors, fast-forward catch-up, live stream handoff, and cache boundaries.

This PR is documentation-only. It does not change runtime code, relay behavior, PWA behavior, deployment files, or hard markers.

### PR B — implement append-only atom log and feed cursor

The append-only atom log is now implemented as the first durable storage step. Accepted atoms are appended once to `/data/atoms.log.jsonl`, the relay loads that log at startup, skips malformed JSONL lines, dedupes by `atom_id`, and rebuilds its bounded in-memory feed buffer from the durable log. Full cursor semantics remain future work beyond the current byte-offset compatibility behavior.

SQLite remains a future index/cache and must be rebuildable from the atom log.

### PR C — generate cacheable public read snapshots

Generate public feed and atom snapshots that can be cached at the edge while keeping writes, validation, health, node info, status, and live stream behavior dynamic.

## Core sync model

- **Atom log is durable memory.** The append-only log is the authoritative record of accepted atoms.
- **Stream is live flow.** The stream is for newly delivered atoms and continuity after a client has caught up.
- **Fast-forward is catch-up from a cursor.** Clients use a cursor to ask for atoms delivered after a known node-local position.
- **`atom_id` dedupes identity.** Clients use `atom_id` to identify the same atom across feeds, streams, snapshots, retries, and duplicate deliveries.
- **`log_seq` or cursor dedupes delivery.** Nodes use their delivery position to support ordered catch-up from that node.
- **DB is not the API.** Public HTTP endpoints define the sync contract; SQLite is an implementation detail.
- **Public reads should be cacheable where possible.** Feed snapshots and atom JSON can become static/cacheable once generated.
- **Writes remain dynamic and validated by the node.** Atom submission still requires live validation and append behavior.

## Separating Identity from Delivery

| Concept | Purpose | Scope |
|---|---|---|
| `atom_id` | Cryptographic identity of the atom content | Global — same on every node |
| `cursor` / `log_seq` | Position in a node's append-only log | Local — varies per node |

**Rules:**

- `atom_id` deduplicates identity — two atoms with the same `atom_id` are the same content, even if received via different paths
- `cursor`/`log_seq` deduplicates delivery — a client should not ingest the same atom twice from the same node
- A client that reconnects uses the highest `cursor` it has seen from that node to resume
- `atom_id` is derived from atom content (SHA-256 of canonical JSON without `sig`)
- `cursor` is a monotonically increasing integer assigned by the accepting node

## Intended endpoints

### 1. Snapshot/feed

```http
GET /feed?limit=100
```

Returns a recent public feed. This is the fallback when a client has no cursor, when a cursor is missing, or when a cursor cannot be used. The response should include atoms and enough delivery metadata for a client to continue with fast-forward or stream.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `since` | integer | `0` | Return atoms with `cursor > since` |
| `limit` | integer | `100` | Maximum atoms to return per response |

**Response (JSON array):**

```json
[
  {
    "cursor": 42,
    "atom_id": "abc123def456...",
    "atom": { /* full atom object */ }
  }
]
```

**Headers:**

- `X-Latest-Cursor`: the highest cursor currently on this node

**Notes:**

- If `since` is not provided, returns from the beginning (cursor 1)
- If `since` exceeds the node's latest cursor, returns an empty array
- The client should call repeatedly with the last received cursor until the response is empty
- The client should also track `X-Latest-Cursor` for use with `GET /stream`

### 2. Fast-forward

```http
GET /feed?since=<cursor>&limit=500
```

Returns atoms delivered after the supplied cursor, up to the requested limit. This is the catch-up path for clients that have previously seen a node-local delivery position.

### 3. Live stream

```http
GET /stream?since=<cursor>
```

Opens a long-lived HTTP connection that streams newly accepted atoms as they arrive. Clients can first fast-forward through `/feed?since=<cursor>&limit=500`, then switch to `/stream?since=<cursor>` using the newest returned cursor.

**Response:**

A Server-Sent Events (SSE) stream with `text/event-stream` content type:

```text
event: atom
data: {"cursor":42,"atom_id":"abc...","atom":{...}}

event: atom
data: {"cursor":43,"atom_id":"def...","atom":{...}}

event: heartbeat
data: {}
```

**Notes:**

- Heartbeat events are sent every 30 seconds to keep the connection alive
- `X-Latest-Cursor` header is set on initial connection response
- If the cursor is absent, stale, or unsupported, the node may fall back to recent stream/feed behavior rather than treating the cursor as atom identity

### 4. Atom lookup, future

```http
GET /atoms/<atom_id>.json
```

or the existing resolution path:

```http
GET /p/<atom_id>
```

A future atom lookup should resolve by atom identity, not delivery position. It can return the atom JSON directly or route through the existing public permalink path.

## Cursor rules

- A cursor is a node-local delivery position, not atom identity.
- A cursor may be a numeric `log_seq` or an opaque string.
- Clients dedupe atoms by `atom_id`, not by cursor alone.
- Nodes may return duplicate atoms safely; clients must tolerate duplicates.
- A missing cursor falls back to the recent feed.
- A stale, invalid, or unrecognized cursor may fall back to the recent feed or return a documented cursor error in a future API version.
- Clients can catch up from a cursor, store the newest returned cursor, then switch to the live stream.
- Cursor values are only meaningful for the node that issued them unless a future protocol explicitly defines cross-node cursor semantics.

## Storage direction

```text
/data/atoms.log.jsonl = append-only durable truth
/data/punkto.db = SQLite index/cache
```

### `/data/atoms.log.jsonl` — Append-Only Truth

The canonical durable record of every atom accepted by this node. The current implemented file stores one full atom JSON object per line.

```jsonl
{"punkto":"p:u07qsuustfsh","t":1780000000000,"x":"hello"}
{"punkto":"p:u07qskyuhbus","t":1780000001000,"relation":"root","x":"root"}
```

**Rules:**

- Accepted atoms are appended once to `/data/atoms.log.jsonl`.
- One full atom JSON object per line (JSONL format).
- The relay computes `atom_id` from each atom for dedupe; duplicate `atom_id`s are not appended again.
- The log is append-only — runtime buffer pruning must not rewrite it.
- Malformed JSONL lines are skipped and counted at startup instead of crashing the relay.
- Backups must include `/data/atoms.log.jsonl`; SQLite remains future rebuildable index/cache state.
- The atom log is the durable source of truth.

### `/data/punkto.db` — SQLite Index/Cache

A rebuildable index that mirrors the atom log for fast queries.

**Properties:**

- Full-text search on atom payloads
- Spatial queries by 3D geohash
- Board/ROOT/REPLY relationship queries
- Can be rebuilt from `/data/atoms.log.jsonl` at any time
- Loss of `punkto.db` is not data loss — it is index loss
- Feed state survives node restart because it is derived from the durable atom log
- `atom_id` prevents storing the same accepted atom as a distinct identity
- `log_seq` or an equivalent cursor records delivery order for that node

## Fast-Forward Flow

```text
Client                             Server
  |                                  |
  |-- GET /feed?since=42 ----------->|
  |                                  |--- Read atoms.log.jsonl from line 43
  |                                  |--- Slice [limit] atoms
  |<-- [cursor:43..142, atoms] ------|
  |<-- X-Latest-Cursor: 142 ---------|
  |                                  |
  |-- GET /feed?since=142 ---------->|
  |<-- [cursor:143..150, atoms] -----|
  |<-- X-Latest-Cursor: 150 ---------|
  |                                  |
  |-- GET /stream?since=150 -------->|
  |<-- SSE: atom, atom, heartbeat... |
```

## Cache Policy

### Live/Dynamic Endpoints — Do Not Cache

The following endpoints produce dynamic, time-sensitive responses and must **never** be cached by CDN, Cloudflare, or browser:

| Endpoint | Reason |
|---|---|
| `POST /atom` | Writes must be live-validated |
| `GET /feed?since=<cursor>` | Content changes with every new atom |
| `GET /stream` | Long-lived live stream |
| `GET /node/info` | Status changes (load, peers, uptime) |
| `GET /health` | Must reflect real-time health |
| `GET /status` | Operational status must be current |

### Cacheable Snapshots (Future)

Periodic static snapshots may be served from a CDN for cold-start clients:

| Resource | Cache | Description |
|---|---|---|
| Static PWA assets | Long-lived | `app.js`, `index.html`, images |
| `/public/feed-latest.json` | Moderate (1h+) | Generated feed snapshot |
| `/public/feed-000001.json` | Permanent | Versioned feed snapshot |
| `/public/atoms/<atom_id>.json` | Long-lived | Individual atom JSON snapshot |

These are **eventually consistent** snapshots, not substitutes for live `/feed` and `/stream` endpoints.

### Cloudflare and static public-read direction

The dynamic node remains responsible for:

- `POST /atom`
- Atom validation
- Appending accepted atoms to the durable log
- Live stream delivery
- Dynamic operational endpoints

Cloudflare can cache:

- Static PWA assets
- Generated public feed snapshots
- Future generated atom JSON snapshots

Do not blindly cache:

- `POST /atom`
- `/stream`
- `/health`
- `/node/info`
- `/status`

Future static snapshot paths:

```text
/public/feed-latest.json
/public/feed-000001.json
/public/atoms/<atom_id>.json
```

These snapshots allow public reads to become cheap and cache-friendly while the node keeps write validation and live sync dynamic.

## Future Work (Phase 8.1–8.9)

| Item | Description |
|---|---|
| Implement append-only atom log writer | Write atoms to `/data/atoms.log.jsonl` in the relay |
| Implement `/feed?since=<cursor>` | Serve atom log slices via HTTP |
| Implement `/stream?since=<cursor>` | SSE streaming endpoint |
| Rebuild SQLite from log on restart | Ensure index survives container restart |
| Add backup/restore for atom log | `cp /data/atoms.log.jsonl /backup/` |
| Add node doctor | Verify log integrity, cursor continuity, and index-to-log consistency |

See `TODO.md` Phase 8 for the full public-readiness roadmap.

## Deliberately unchanged in PR A

- No runtime code changes.
- No relay behavior changes.
- No PWA changes.
- No deployment file changes.
- No hard marker bump.
- No deploy action.
