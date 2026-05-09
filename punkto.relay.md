# Punkto Relay — Flow TV Architecture for the Live Network

> Draft v0.1 — Three roles: relay, client, archive

---

## 1. Purpose

Punkto is **spatial first** and, by default, **flow-shaped**.

Users experience space as it is *now*: what's near them, what just happened, what's currently being said about a place. Atoms flow past — like a TV broadcast tuned to a coordinate. Miss it, lose it (from the default view).

This document specifies the architectural split that makes Flow TV practical at scale and operationally sound for community-run nodes:

| Role | Stores | Purpose | Cost profile |
|---|---|---|---|
| **Relay** | Rolling buffer (recent atoms only) | Forward live atoms between peers and to clients | Tiny — runs on a Raspberry Pi or a $5 VPS |
| **Client** | User's local slice (IndexedDB) | The user's lived experience of the network | User device; user-owned |
| **Archive** | Full historical atom store, indexed | Time-range queries, search, bulk export | Heavy I/O — operational expense |

The protocol layer (atom format, atom_id, canonical JSON, signatures, peer mesh) is unchanged. This is a **deployment model** spec, not a protocol revision.

---

## 2. Design Principle

> The free public good is **the live flow**.
>
> Personal history lives on personal devices.
>
> Long-term searchable archive is **the only thing that's hard to operate** — and therefore the only thing that can be commercialized without violating the protocol's principles.

This makes relays cheap to run anywhere (Nairobi, Tórshavn, anywhere with a phone and a power outlet), keeps user data on user devices, and creates a clean line for sustainability without compromise.

---

## 3. The Relay Role

### 3.1 Responsibilities

A relay node:

- Accepts `POST /atom` from clients
- Forwards new atoms to its configured peers (via existing `/feed` pull or push notification)
- Serves `GET /latest` to clients — returns a small, recent slice of the flow
- Maintains a **rolling buffer** of recent atoms (oldest atoms drop off as new ones arrive)
- Optionally serves `GET /feed?since=<cursor>` for backward compatibility (within buffer range)
- **Does not** maintain a queryable historical index
- **Does not** support time-range queries beyond the buffer window

### 3.2 Buffer parameters

A relay's buffer is bounded by either size or time, whichever the operator chooses:

| Parameter | Env var | Default | Notes |
|---|---|---|---|
| Max atoms | `PUNKTO_BUFFER_ATOMS` | `10000` | Hard cap on stored atom count |
| Max age | `PUNKTO_BUFFER_HOURS` | `168` (7 days) | Atoms older than this drop off |
| Storage | `PUNKTO_DATA_DIR` | `./data/` | `atoms.ndjson` is rotated when limits exceeded |

When either limit is exceeded, the oldest atoms are removed from disk. The relay does not keep a historical archive.

### 3.3 The `/latest` endpoint

The core relay endpoint. Returns a single small packet containing the most recent atoms in the buffer.

```
GET /latest
```

Response:

```json
{
  "atoms": [
    {"punkto": "p:u07qsuustfsh", "t": 1745598371000, "f": "alice", "x": "hello"},
    {"punkto": "p:u07qskyuhbus", "t": 1745598375000, "f": "bob",   "x": "world"}
  ],

  "served_at": 1745598400000,
  "node": "app1.punkto.xyz",
  "buffer_size": 312,
  "buffer_oldest_t": 1744993600000
}
```

**Rules:**

- Returns up to `PUNKTO_LATEST_LIMIT` atoms (default `100`)
- Sorted by `t` descending (newest first) — clients can reverse if they prefer
- Includes `served_at` so clients can detect drift
- Includes `buffer_oldest_t` so clients know how far back the relay can see
- No pagination — clients call `/latest` repeatedly; in steady state most calls return only a handful of new atoms

### 3.4 Optional: streaming endpoint

For real-time delivery, relays MAY expose:

```
GET /stream    (Server-Sent Events)
```

Each event is a single atom:

```
event: atom
data: {"punkto":"p:u07qsuustfsh","t":1745598371000,"f":"alice","x":"hello"}

```

Clients that don't support SSE fall back to polling `/latest` on an interval (recommended: 10–30s).

### 3.5 What the relay does NOT do

- No historical search (`GET /feed?since=very_old_cursor` returns empty if the cursor is below the buffer)
- No time-range queries (`?from=t1&to=t2`)
- No author search (`?author=alice`)
- No geographic filtering (`?bbox=...`)
- No full-text search

These are archive-role concerns.

---

## 4. The Client Role

### 4.1 Responsibilities

A client (PWA, mobile app, CLI):

- Periodically polls `/latest` (or subscribes to `/stream`) from one or more relays
- Maintains its own local store of every atom it has witnessed (IndexedDB in browsers, SQLite or NDJSON locally)
- Provides UI for: live flow view, local-history view, search within local archive
- Routes writes (`POST /atom`) using client-side load balancing (see `punkto.sync.md` §5b)
- **Owns its history** — the user's local DB is *their* archive

### 4.2 Local storage model

The client's local DB is **the user's personal Punkto archive**. It contains:

- Every atom the user has witnessed (via /latest polling)
- Every atom the user has authored
- Optional: every atom they've explicitly bookmarked

The local DB is structured for the user's needs, not the network's. Schema is implementation-defined (e.g., IndexedDB with indexes on `punkto`, `t`, `f` for the PWA).

### 4.3 What this enables

- **"Show me everything I've seen at this place"** → instant local query, no network calls
- **"Show me my own history"** → instant local query
- **"Show me last 7 days of public flow"** → already in local DB from polling
- **Offline-first** — the user's experience continues even when no relay is reachable

### 4.4 What requires the archive role

- **"Show me everything anyone said at this place over the last 5 years"** → goes beyond user's local DB and beyond relay buffers; this is an archive query

---

## 5. The Archive Role (Optional, Possibly Paid)

### 5.1 Responsibilities

An archive node:

- Subscribes to one or more relays and ingests their `/latest` stream continuously
- Persists every atom it sees into a real database (Postgres, SQLite, ClickHouse, etc.)
- Builds indexes for: time ranges, geographic bounding boxes, author, full-text payload
- Exposes query endpoints not available on relays
- May charge for queries, bulk exports, or analytics

### 5.2 Archive endpoints (suggested)

```
GET /archive/feed?from=<t1>&to=<t2>            time-range query
GET /archive/at?punkto=<canonical>&radius=<m>  geographic + altitude query
GET /archive/author?key=<pubkey>&from=<t>      author history
GET /archive/search?q=<text>                   payload full-text
GET /archive/export?from=<t>&to=<t>            bulk dump (CSV/NDJSON)
```

Auth and pricing model are operator-defined. The protocol is permissive.

### 5.3 Trust and verification

Archive operators are not part of the trusted relay mesh. Their results are advisory. Clients SHOULD:

- Re-verify `atom_id` of every atom returned by an archive (canonical SHA-256 check)
- Re-verify `sig` if present
- Treat archive results as untrusted until locally verified

The archive cannot forge atoms because identity is content-addressed. It can, however, omit or reorder them.

### 5.4 Decentralization

Multiple independent archives MAY exist. Different operators serve different geographies, languages, time periods, or specialty queries. No archive is canonical. Clients choose which to trust.

---

## 6. Compatibility with `punkto.sync.md`

Relay-mode replication is **strictly compatible** with the existing pull-based mesh sync model (`punkto.sync.md` §6) — but with bounded retention.

When a relay pulls `/feed?since=<cursor>` from a peer:

- Atoms within the peer's current buffer are returned normally
- A request for a cursor *below* the peer's buffer floor returns:
  ```json
  {"atoms": [], "cursor": <peer_buffer_floor>, "buffer_underflow": true}
  ```
- The puller advances its cursor to the buffer floor and resumes from there
- Atoms from before the buffer floor are **lost from the relay mesh** (but may exist in archive nodes)

This is the core trade-off of Flow TV: the live network is bounded, the historical record requires a separate, deliberate archival operation.

---

## 7. Migration Path

### 7.1 Current state

The current `pwa/node.py` implementation:

- Stores all atoms forever in `atoms.ndjson` (unbounded growth)
- Loads all atom IDs on every sync (`load_all_atom_ids()`) — quadratic cost
- No buffer rotation
- No `/latest` endpoint

### 7.2 Phase 1 — relay-mode (small change)

1. Add `/latest` endpoint returning recent atoms (configurable limit)
2. Add buffer rotation logic — drop oldest atoms when limits exceeded
3. Replace `load_all_atom_ids()` full scan with an in-memory `set` populated at startup
4. Document `PUNKTO_BUFFER_ATOMS` and `PUNKTO_BUFFER_HOURS` env vars

Result: app1 and app2 become real relays with bounded resource usage. No protocol change.

### 7.3 Phase 2 — client-side archive (medium change)

1. PWA stores all witnessed atoms in IndexedDB (already partial — extend coverage)
2. UI default switches to "recent flow" view (last 7 days)
3. Add "my history" view using local IndexedDB
4. Add "this place" view filtered by current geohash3d prefix

Result: users see the Flow TV experience by default; their personal archive lives on their device.

### 7.4 Phase 3 — first archive node (large change, optional)

1. Spin up a separate `archive.punkto.xyz` (or community-run equivalent)
2. Ingest from relays continuously
3. Persist to Postgres + indexes
4. Expose archive endpoints
5. Offer free tier (limited queries) and paid tier (unlimited, exports, analytics)

Not urgent. Only needed when historical search becomes a real user demand.

---

## 8. Non-Goals

This spec does **not** cover:

- Push-based replication (nodes still pull from peers)
- Auto-discovery of archive nodes (clients are configured manually or via seed lists)
- Cryptographic proofs of archive completeness (Merkle commitments are future work)
- Federation between archives (each archive is independent)
- Standardized archive query language (each archive defines its own)

---

## 9. Operational Recommendations

### 9.1 Running a relay

Minimum spec for a community relay:

- 1 vCPU, 512 MB RAM, 1 GB disk
- Python 3.9+
- Public HTTPS endpoint
- Open port 443 (or 80 with TLS termination upstream)

With default buffer (10K atoms, 7 days), disk usage stays under 100 MB. Memory under 100 MB. CPU near-idle except during sync bursts.

### 9.2 Running a client

The PWA already runs on any modern browser. A native client SHOULD:

- Use SQLite or equivalent embedded store
- Sync from at least 2 relays for redundancy
- Keep client-side data forever (or until user explicitly purges)
- Encrypt the local DB at rest if storing private data

### 9.3 Running an archive

Non-trivial. Recommended only for:

- Universities / research projects
- Civic tech organizations
- Commercial operators with a sustainability plan

Archive operators should publish:

- Their retention policy (do they keep everything? for how long?)
- Their relay sources (which relays they ingest from)
- Their pricing / access model
- Their identity / accountability

---

## 10. Status

Draft v0.1 — initial proposal

## 11. Changelog

| Version | Changes |
|---|---|
| v0.1 | Initial proposal: three-role architecture (relay / client / archive); rolling buffers; `/latest` endpoint; migration path from current full-storage model. |

---

## 12. Guiding Idea

> The protocol stores forever.  
> Relays carry the now.  
> Clients keep what they witnessed.  
> Archives serve those who ask.

Four layers, four roles, four cost profiles. Cleanly separable. None centralizable. All open-source-able.
