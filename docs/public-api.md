# Punkto Public API

> **Cache policy:** See [docs/cache-cloudflare.md](cache-cloudflare.md) for the full cache and CDN policy definition.


> This document describes all public HTTP endpoints exposed by a Punkto node's relay service. These endpoints form the public API surface for clients, tools, peer nodes, and monitoring systems.
>
> **Status:** Live — describes the current implementation.

**Base URL:** The relay listens on port `8000` internally. In production it is served behind Caddy reverse proxy at:

- `https://node1.punkto.xyz` — Punkto Reference Node 1
- `https://node2.punkto.xyz` — Punkto Reference Node 2
- `https://node1.punkto.xyz` — Legacy alias for Node 1
- `https://node2.punkto.xyz` — Legacy alias for Node 2
- `https://punkto.xyz` — Primary domain (Punkto Reference Node 1)

**Content-Type:** All JSON responses use `application/json`. The status page uses `text/html`.

---

## Endpoint Summary

| Method | Path | Response Type | Description |
|--------|------|---------------|-------------|
| `GET` | `/health` | JSON | Minimal health check |
| `GET` | `/info` | JSON | Legacy node summary |
| `GET` | `/node/info` | JSON | Full public-safe node config + status |
| `GET` | `/status` | HTML | Human-readable public node status page |
| `GET` | `/latest` | JSON | Recent publicly-served atoms, newest first |
| `GET` | `/feed` | JSON | Cursor-based atom feed for sync |
| `GET` | `/p/<atom_id>` | HTML | HTML page for a single atom (if served) |
| `GET` | `/` | HTML | Relay root landing page |
| `POST` | `/atom` | JSON | Submit a new atom |

---

## `GET /health`

Minimal health check endpoint. Returns a lightweight JSON response indicating the relay is alive and responding.

### Response

**HTTP 200 OK**

```json
{
  "status": "ok",
  "node": "Punkto Reference Node 1",
  "buffer_size": 3
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"ok"` if the relay is running |
| `node` | string | The node's configured name |
| `buffer_size` | integer | Number of atoms currently held in the in-memory buffer |

### Example

```bash
curl https://node1.punkto.xyz/health
```

**Purpose:** Load balancer health checks, monitoring systems (uptime robot, Prometheus blackbox), deployment verification.

**Cache policy:** Never cache. Must return real-time status.

---

## `GET /info`

Legacy node summary endpoint. Returns node identity, capabilities, and configuration. Superseded by `/node/info` but maintained for backward compatibility.

### Response

**HTTP 200 OK**

```json
{
  "node": "Punkto Reference Node 1",
  "version": "v0.1",
  "peers": ["https://node2.punkto.xyz"],
  "buffer_size": 3,
  "buffer_oldest_t": 1748700000000,
  "buffer_atoms_max": 10000,
  "buffer_hours_max": 72,
  "latest_limit": 100,
  "sync_interval": 30,
  "serving": {
    "serve_recent": true,
    "serve_recent_hours": 24,
    "serve_pinned": true,
    "serve_archive": false,
    "pinned_atoms": []
  },
  "acceptance": {
    "accept_recent_hours": 24,
    "trusted_backfill_count": 0
  },
  "capabilities": ["write", "latest", "feed", "sync"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `node` | string | Node name |
| `version` | string | Relay software version |
| `peers` | array[string] | Configured peer node URLs |
| `buffer_size` | integer | Current atom count |
| `buffer_oldest_t` | integer (ms) | Timestamp of oldest atom in buffer |
| `buffer_atoms_max` | integer | Maximum atoms before pruning |
| `buffer_hours_max` | integer | Maximum age in hours before pruning |
| `latest_limit` | integer | Maximum atoms in `/latest` response |
| `sync_interval` | integer (seconds) | Peer sync interval |
| `serving` | object | Live-forward serving policy |
| `acceptance` | object | Live-forward acceptance policy |
| `capabilities` | array[string] | Endpoint capabilities |

### Example

```bash
curl https://node1.punkto.xyz/info
```

**Purpose:** Quick node discovery and capability advertisement. Used by peer nodes during sync to learn policy and configuration.

**Cache policy:** Short-lived cache (30s).

---

## `GET /node/info`

Full public-safe node configuration and identity. Returns identity, config status, storage stats, policy, and sync state. This is the canonical node information endpoint for production use.

### Response

**HTTP 200 OK**

```json
{
  "node": {
    "name": "Punkto Reference Node 1",
    "version": "v0.1",
    "fingerprint": "4f6b...a1c2",
    "node_fingerprint": "4f6b...a1c2"
  },
  "config": {
    "loaded": true,
    "source": "/config/punkto-node.yml"
  },
  "peers": ["https://node2.punkto.xyz"],
  "buffer": {
    "size": 3,
    "oldest_t": 1748700000000,
    "atoms_max": 10000,
    "hours_max": 72,
    "latest_limit": 100
  },
  "storage": {
    "mode": "append_only_log",
    "log_path": "/data/atoms.log.jsonl",
    "log_loaded": true,
    "log_lines": 3,
    "corrupt_lines": 0
  },
  "serving": {
    "serve_recent": true,
    "serve_recent_hours": 24,
    "serve_pinned": true,
    "serve_archive": false,
    "pinned_atoms": []
  },
  "acceptance": {
    "accept_recent_hours": 24,
    "trusted_backfill_count": 0
  },
  "capabilities": ["write", "latest", "feed", "sync"],
  "sync": {
    "peers": ["https://node2.punkto.xyz"],
    "interval": 30
  },
  "policy_stats": {
    "old_rejected": 0
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `node.name` | string | Human-readable node name |
| `node.version` | string | Relay software version |
| `node.fingerprint` | string | Node identity fingerprint (from node key) |
| `node.node_fingerprint` | string | Alias for backward compatibility |
| `config.loaded` | boolean | Whether YAML config was loaded |
| `config.source` | string | Config file path |
| `peers` | array[string] | Configured peer node URLs |
| `buffer.*` | object | In-memory buffer state |
| `storage.*` | object | Append-only log persistence state |
| `serving.*` | object | Live-forward serving policy |
| `acceptance.*` | object | Live-forward acceptance policy |
| `sync.*` | object | Peer sync configuration and state |
| `policy_stats` | object | Node policy counters |

### Security

The following fields are **never** exposed in `/node/info`:

- `private_key` / node private key material
- `.env` values or environment secrets
- Database connection strings
- API tokens or passwords
- Raw atom content dumps

### Example

```bash
curl https://node1.punkto.xyz/node/info
```

**Purpose:** Client/tool discovery, deployment verification, status monitoring, node identity validation.

**Cache policy:** Short-lived cache (30s). Not suitable for aggressive caching.

---

## `GET /status`

Human-readable public node status page rendered as HTML. Designed for operators, curious users, and quick visual verification of node health.

### Response

**HTTP 200 OK** with `Content-Type: text/html`.

The page includes:

- Node name and identity
- Config loaded status
- Data flow section showing `/feed` and `/latest` endpoints
- Recent atom feed preview (up to LATEST_LIMIT atoms)
- Serving and acceptance policy summary
- Storage statistics
- Peer node links
- Public endpoint list with URLs
- No secrets, no private keys, no sensitive data

### Security

The `/status` page must **never** contain:

- `private_key` or raw key material
- Environment variables
- Database credentials
- Internal network details
- Token or session data

If the page would render any of these, it is a bug.

### Example

```bash
curl -s https://node1.punkto.xyz/status | head -20
```

**Purpose:** Quick visual node health check, operator dashboard, public transparency page.

**Cache policy:** Short-lived cache (30s).

---

## `GET /latest`

Returns the most recently accepted atoms that are publicly served, ordered from newest to oldest by atom timestamp (`t`).

### Query Parameters

None. The atom count is fixed by the node's `LATEST_LIMIT` configuration (default: 100).

### Response

**HTTP 200 OK**

```json
{
  "atoms": [
    {
      "punkto": "p:u07qskymnmud",
      "t": 1748700000000,
      "content": "Reply to board...",
      "parent_id": "d84d...5b94",
      "f": "user123",
      "x": "reply text",
      "atom_id": "abc..."
    }
  ],
  "served_at": 1748700123456,
  "node": "Punkto Reference Node 1",
  "buffer_size": 3,
  "buffer_oldest_t": 1748690000000
}
```

| Field | Type | Description |
|-------|------|-------------|
| `atoms` | array[object] | List of atom objects |
| `atoms[].punkto` | string | Canonical 3D geohash address |
| `atoms[].t` | integer (ms) | Atom creation timestamp |
| `atoms[].atom_id` | string | Content-derived atom ID (SHA-256) |
| `atoms[].*` | various | Other atom fields (content, f, x, parent_id, etc.) |
| `served_at` | integer (ms) | Server time when response was generated |
| `node` | string | Node name |
| `buffer_size` | integer | Total atoms in buffer |
| `buffer_oldest_t` | integer (ms) | Oldest atom timestamp in buffer |

### Serving Policy

The response only includes atoms that pass the **live-forward serving policy**:

- Atoms with `t` within `serve_recent_hours` (default: 24h) of now
- Atoms whose `atom_id` appears in `pinned_atoms`
- All atoms if `serve_archive=true`

### Example

```bash
curl https://node1.punkto.xyz/latest
```

**Purpose:** Quick recent atom feed for UI preview, monitoring, and client initial state.

**Cache policy:** Short-lived cache (10–30s). Not suitable for long-lived caching.

---

## `GET /feed`

Cursor-based atom feed for sync. Returns atoms after a given cursor position (byte offset into `/data/atoms.log.jsonl`). Designed for efficient client and peer node catch-up.

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `since` | integer | `0` | Return atoms with log position > `since` (byte offset) |

### Response

**HTTP 200 OK**

```json
{
  "atoms": [
    {
      "punkto": "p:u07qskymnmud",
      "t": 1748700000000,
      "content": "...",
      "atom_id": "abc..."
    }
  ],
  "cursor": 614
}
```

| Field | Type | Description |
|-------|------|-------------|
| `atoms` | array[object] | List of atoms with `cursor > since` |
| `cursor` | integer | New cursor (byte offset to resume from) |
| `buffer_underflow` | boolean | Present if buffer was pruned and `since` is now before oldest offset |

### Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| `400` | `invalid_cursor` | `since` parameter is not a valid integer |

### Sync Protocol

1. Client calls `GET /feed` without `since` to get initial state
2. Client records the `cursor` value from response
3. Client calls `GET /feed?since=<cursor>` to get new atoms
4. Repeat until response is empty (`atoms` is `[]`)
5. The cursor is a byte offset into the append-only log, not an atom count

### Example

```bash
# Initial fetch
curl https://node1.punkto.xyz/feed

# Incremental fetch
curl 'https://node1.punkto.xyz/feed?since=614'
```

**Purpose:** Client sync, peer node replication, efficient catch-up after disconnection.

**Cache policy:** Never cache. Dynamic response that changes with every new atom.

---

## `GET /p/<atom_id>`

Renders a single atom's HTML page. Allows direct linking to a specific atom by its `atom_id`.

### Path Parameters

| Param | Type | Description |
|-------|------|-------------|
| `atom_id` | string | The SHA-256 content hash of the atom (URL-encoded) |

### Response

**HTTP 200 OK** with `Content-Type: text/html` if the atom is found and publicly served.

The page includes:

- Atom punkto address (3D geohash)
- Atom content and metadata
- Timestamp
- Author identity (`f` field)
- Link back to map view

### Error Responses

| Status | Description |
|--------|-------------|
| `404` | Atom not found or not publicly served |

### Example

```bash
curl https://node1.punkto.xyz/p/abc123def456
```

**Purpose:** Direct permalink to an atom for sharing, debugging, or reference.

---

## `GET /`

Relay root landing page. Provides links to all public endpoints.

### Response

**HTTP 200 OK** with `Content-Type: text/html`.

Simple HTML page showing:

- Relay version
- Node name
- Atom count
- Links to `/latest`, `/info`, `/health`

### Example

```bash
curl https://node1.punkto.xyz/
```

**Purpose:** Quick human verification that the relay is running.

---

## `POST /atom`

Submit a new atom to the node. Atoms must be valid JSON objects with required fields.

### Request

**Content-Type:** `application/json`

**Body (JSON object):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `punkto` | string | ✅ | Canonical 3D geohash address (e.g., `p:u07qskymnmud`) |
| `t` | integer | ✅ | Atom creation timestamp in milliseconds since epoch |
| `content` | string | — | Atom content / payload text |
| `f` | string | — | Author identity / handle |
| `x` | string | — | Signed message / signature |
| `parent_id` | string | — | For REPLY atoms: the `atom_id` of the parent ROOT atom |
| `relation` | string | — | Relationship type (e.g., `"reply"`) |
| `*` | any | — | Any additional fields are preserved as-is |

**Size limit:** 64 KB (`MAX_BODY_BYTES`).

### Response

**HTTP 201 Created** on success:

```json
{
  "atom_id": "abc123...",
  "status": "accepted",
  "punkto": "p:u07qskymnmud"
}
```

**HTTP 200 OK** if the same atom was already accepted (duplicate):

```json
{
  "atom_id": "abc123...",
  "status": "already_accepted",
  "punkto": "p:u07qskymnmud"
}
```

### Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| `400` | `invalid_json` | Body is not valid JSON or not a JSON object |
| `400` | `invalid_punkto` | `punkto` field missing or invalid format |
| `400` | `empty_body` | Request body is empty |
| `400` | `invalid_length` | Content-Length is missing or invalid |
| `413` | `payload_too_large` | Body exceeds 64 KB |
| `422` | `atom_too_old` | Atom timestamp is older than `accept_recent_hours` policy |
| `422` | `invalid_punkto` | Punkto address fails validation |
| `400` | (reply validation) | REPLY atom references a parent that doesn't exist or has wrong location |
| `404` | `not_found` | Only `POST /atom` is allowed — other paths return 404 |
| `429` | `rate_limited` | Too many `POST /atom` requests from this client — see Rate Limiting below |

### Rate Limiting

`POST /atom` is rate limited per client IP to protect the public buffer from flooding. By default a client may submit at most **30 POSTs per 60 seconds**; exceeding this returns:

```json
{ "ok": false, "error": "rate_limited" }
```

with HTTP status `429`. Limits are configurable per node via `PUNKTO_RATE_LIMIT_MAX_POSTS` and `PUNKTO_RATE_LIMIT_WINDOW_SECONDS`. The limiter is in-memory and per-node (it resets on restart). Read endpoints (`/health`, `/status`, `/node/info`, `/feed`, `/latest`) are **not** rate limited.

### Acceptance Policy

The node applies a **live-forward acceptance policy** by default:

- Atoms with `t` within the last `accept_recent_hours` (default: 24h) are **accepted**
- Atoms with `t` older than the window are **rejected** with `atom_too_old`
- Trusted backfill peers may bypass this limit

### Duplicate Handling

Atoms are deduplicated by `atom_id` (SHA-256 of canonical JSON without `sig`/`x` field). If the same atom is posted again, the node returns `200` with `"status": "already_accepted"` and does **not** append a duplicate to the log.

### REPLY Atom Validation

Atoms with `parent_id` (REPLY atoms) undergo additional validation:

- The parent atom must exist in the node's buffer
- The REPLY must use the **same punkto address** as the parent ROOT atom
- If either check fails, the atom is rejected with an error description

## 9. Error Response Format

All error responses (except HTML paths) use a consistent JSON format:

```json
{
  "error": "error_code",
  "message": "Human-readable description of the problem"
}
```

| HTTP Status | Description |
|-------------|-------------|
| `400` | Malformed request (invalid JSON, missing fields, etc.) |
| `404` | Endpoint or resource not found |
| `413` | Request body too large |
| `422` | Semantic validation failure (atom too old, invalid punkto address) |
| `429` | Rate limited (too many `POST /atom` requests from this client) |
| `500` | Internal server error |

---

## 10. Appendix: Deprecated Endpoints

### `GET /info`

Legacy node summary. Superseded by `/node/info`. Maintained for backward compatibility with existing tools. Will be removed in a future version.

---

## 11. Appendix: HTTP Headers

### Request Headers (POST /atom)

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | ✅ | Must be `application/json` |
| `Content-Length` | ✅ | Must match the body size in bytes |

### Response Headers

| Header | Description |
|--------|-------------|
| `Content-Type` | `application/json` or `text/html` |
| `Access-Control-Allow-Origin` | CORS header for browser clients |
| `Cache-Control` | Cache policy hint |

---

## 12. Appendix: Version History

| API Version | Relay Version | Changes |
|-------------|---------------|---------|
| 1.0 | v0.1 | Initial API: /health, /info, /latest, /feed, /atom |
| 1.1 | v0.1 | Added /node/info, /status, /p/<id> |
| 1.2 | v0.1 | Added live-forward policy to /info and /node/info, config_loaded support |

### Cache Policy Reference

See [docs/cache-cloudflare.md](cache-cloudflare.md) for the full cache policy, Cloudflare guidance, and Caddy header configuration.
