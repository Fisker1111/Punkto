# Punkto Node Specification (v0.1)

> A Punkto node stores, serves, and optionally shares Punkto atoms.

All Punkto nodes are nodes.

Some nodes may expose a PWA.
Some nodes may allow public sharing.
Some nodes may be private, local, or offline-first.

Capabilities differ, but the node model is the same.

---

## 1. Purpose

A Punkto node exists to:

* receive Punkto atoms
* validate basic structure
* store atoms append-only
* expose atoms through simple HTTP endpoints
* support synchronization with other nodes

A node does not define truth.
A node stores and replicates records.

---

## 2. Core Principle

> Nodes are equal. Capabilities are optional.

A node may be:

* local
* personal
* public
* hosted
* mobile
* edge
* sensor-based
* AI-operated

No node is inherently authoritative.

---

## 3. Capabilities

Nodes advertise optional capabilities through configuration and `/info`.

Example capability flags:

```txt
EnablePWA=true
EnableShare=true
EnableWrite=true
EnableSync=true
EnableAI=true
```

### Capability meanings

| Capability    | Meaning                                                            |
| ------------- | ------------------------------------------------------------------ |
| `EnablePWA`   | Node serves a browser-based Punkto interface                       |
| `EnableShare` | Node exposes public/shareable views                                |
| `EnableWrite` | Node accepts new atoms through `POST /atom`                        |
| `EnableSync`  | Node supports feed-based synchronization                           |
| `EnableAI`    | Node allows AI clients to read/write through documented interfaces |

Capabilities do not change canonical Punkto identity.

---

## 4. Storage Model

Nodes should store atoms as append-only records.

Recommended v0.1 format:

```txt
atoms.ndjson
```

Each line is one atom.

Nodes must not rewrite previously stored atoms.

---

## 5. Atom Record

A minimal atom record contains:

```json
{
  "punkto": "p:u4pruydqqvj-42m-9xk3",
  "timestamp": "2026-04-25T10:00:00Z",
  "author": "ed25519:abc123...",
  "signature": "sig:xyz...",
  "payload": "wind: 12m/s"
}
```

### Required fields

* `punkto`
* `timestamp`
* `payload`

### Recommended fields

* `author`
* `signature`

For v0.1, unsigned local records may exist, but signed records are preferred.

---

## 6. Canonical Rule

Nodes must use the canonical Punkto form for storage and equality.

Canonical form:

```txt
p:<spatial>-<z>-<id>
```

A node must not silently rewrite canonical identifiers.

Derived forms such as `punkto://...` or web URLs may be accepted at API edges, but must resolve to exactly one canonical Punkto before storage.

---

## 7. Minimal HTTP API

A v0.1 node should expose:

```txt
GET  /health
GET  /info
GET  /feed
GET  /feed?since=<cursor>
POST /atom
GET  /punkto/<canonical>
```

---

## 8. Endpoint: `GET /health`

Returns basic node status.

Example response:

```json
{
  "status": "ok"
}
```

---

## 9. Endpoint: `GET /info`

Returns node metadata and capabilities.

Example response:

```json
{
  "name": "punkto-node-01",
  "version": "0.1",
  "protocol": "punkto",
  "protocolVersion": "0.1",
  "capabilities": {
    "EnablePWA": true,
    "EnableShare": true,
    "EnableWrite": true,
    "EnableSync": true,
    "EnableAI": false
  },
  "endpoints": [
    "/health",
    "/info",
    "/feed",
    "/atom",
    "/punkto/<canonical>"
  ]
}
```

---

## 10. Endpoint: `POST /atom`

Accepts a Punkto atom.

Example request:

```json
{
  "punkto": "p:u4pruydqqvj-42m-9xk3",
  "timestamp": "2026-04-25T10:00:00Z",
  "author": "ed25519:abc123...",
  "signature": "sig:xyz...",
  "payload": "wind: 12m/s"
}
```

Example response:

```json
{
  "status": "accepted",
  "cursor": "000000000001",
  "punkto": "p:u4pruydqqvj-42m-9xk3"
}
```

If `EnableWrite=false`, the node must reject writes.

Example:

```json
{
  "error": "writes_disabled"
}
```

---

## 11. Endpoint: `GET /feed`

Returns atoms in append order.

Example response:

```json
{
  "cursor": "000000000003",
  "atoms": [
    {
      "punkto": "p:u4pruydqqvj-42m-9xk3",
      "timestamp": "2026-04-25T10:00:00Z",
      "payload": "wind: 12m/s"
    }
  ]
}
```

### Incremental sync

```txt
GET /feed?since=000000000003
```

Returns atoms appended after the cursor.

---

## 12. Endpoint: `GET /punkto/<canonical>`

Returns atoms for one canonical Punkto.

Example:

```txt
GET /punkto/p:u4pruydqqvj-42m-9xk3
```

Example response:

```json
{
  "punkto": "p:u4pruydqqvj-42m-9xk3",
  "atoms": [
    {
      "timestamp": "2026-04-25T10:00:00Z",
      "payload": "wind: 12m/s"
    }
  ]
}
```

---

## 13. Sharing

If `EnableShare=true`, a node may expose human-friendly public URLs.

Example:

```txt
https://node.example/p/u4pruydqqvj/42m/9xk3
```

Public share URLs are derived views.

They must resolve back to canonical Punkto form before lookup.

If `EnableShare=false`, the node may still support canonical API access depending on configuration.

---

## 14. PWA Mode

If `EnablePWA=true`, the node may serve a Punkto web interface.

The PWA should allow users to:

* view nearby Punktos
* create local atoms
* submit atoms to the node
* inspect canonical IDs on demand
* sync when connectivity is available

The PWA is optional.

A node without a PWA is still a valid node.

---

## 15. Synchronization

If `EnableSync=true`, nodes should sync using feed-based pull replication.

Basic sync model:

1. Node A asks Node B for `/feed?since=<cursor>`
2. Node B returns newer atoms
3. Node A validates and appends accepted atoms

Nodes should tolerate:

* partial feeds
* duplicate atoms
* out-of-order timestamps
* unavailable peers

Append order is local to each node.

Timestamp order is informational.

---

## 16. Validation Rules

A node should reject atoms when:

* `punkto` is missing
* `punkto` does not use canonical `p:` form
* `timestamp` is missing
* `payload` is missing
* JSON is malformed

A node may reject atoms when:

* signature is invalid
* payload is too large
* author is blocked
* writes are disabled

---

## 17. Error Format

Errors should use a simple JSON structure:

```json
{
  "error": "invalid_punkto",
  "message": "Punkto must use canonical p: form."
}
```

Common errors:

* `invalid_json`
* `invalid_punkto`
* `missing_timestamp`
* `missing_payload`
* `writes_disabled`
* `sync_disabled`
* `not_found`

---

## 18. Non-goals for v0.1

Punkto nodes v0.1 do not require:

* user accounts
* global search
* moderation
* blockchain
* token systems
* global peer discovery
* complex databases
* guaranteed consensus

---

## 19. Guiding Idea

> A Punkto node is not the source of truth.
>
> It is a place where spatial records can live, be read, and be replicated.

---

## 20. Status

Draft v0.1 — minimal node behavior
