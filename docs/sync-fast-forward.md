# Sync fast-forward and atom log plan

This document defines the intended public-readiness storage and sync model before implementation. It is a plan for the node API and persistence behavior, not a runtime change.

## Three-step public-readiness plan

### PR A — define atom log fast-forward protocol

Document the model for durable atom storage, public reads, feed cursors, fast-forward catch-up, live stream handoff, and cache boundaries.

This PR is documentation-only. It does not change runtime code, relay behavior, PWA behavior, deployment files, or hard markers.

### PR B — implement append-only atom log and feed cursor

Add the durable append-only atom log and make feed delivery cursor-aware. Accepted atoms should be appended once to the durable log, exposed through a recent snapshot/feed, and available through fast-forward from a node-local cursor.

SQLite remains an index/cache and must be rebuildable from the atom log.

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

## Intended endpoints

### 1. Snapshot/feed

```http
GET /feed?limit=100
```

Returns a recent public feed. This is the fallback when a client has no cursor, when a cursor is missing, or when a cursor cannot be used. The response should include atoms and enough delivery metadata for a client to continue with fast-forward or stream.

### 2. Fast-forward

```http
GET /feed?since=<cursor>&limit=500
```

Returns atoms delivered after the supplied cursor, up to the requested limit. This is the catch-up path for clients that have previously seen a node-local delivery position.

### 3. Live stream

```http
GET /stream?since=<cursor>
```

Starts a live stream after the supplied cursor. Clients can first fast-forward through `/feed?since=<cursor>&limit=500`, then switch to `/stream?since=<cursor>` using the newest returned cursor.

If the cursor is absent, stale, or unsupported, the node may fall back to recent stream/feed behavior rather than treating the cursor as atom identity.

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

Storage rules:

- Accepted atoms are appended once to `/data/atoms.log.jsonl`.
- The atom log is the durable source of truth.
- `/data/punkto.db` is an index/cache for serving and querying.
- SQLite can be rebuilt from the atom log.
- Feed state survives node restart because it is derived from the durable atom log.
- `atom_id` prevents storing the same accepted atom as a distinct identity.
- `log_seq` or an equivalent cursor records delivery order for that node.

## Cloudflare and static public-read direction

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

## Deliberately unchanged in PR A

- No runtime code changes.
- No relay behavior changes.
- No PWA changes.
- No deployment file changes.
- No hard marker bump.
- No deploy action.
