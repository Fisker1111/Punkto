# Punkto Node Specification (v0.2)

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
| `EnableAI`    | Discovery hint: node welcomes AI clients (not a gate)              |

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
  "punkto": "p:u4pruydqqvj3-9xk3",
  "t": 1745598371000,
  "author": "ed25519:abc123...",
  "sig": "base64:...",
  "payload": "wind: 12m/s"
}
```

### Fields

| Field     | Type    | Required | Description                                        |
|-----------|---------|----------|----------------------------------------------------||
| `punkto`  | string  | yes      | Canonical `p:` address                             |
| `t`       | int64   | yes      | Unix timestamp in milliseconds (13 digits)         |
| `payload` | string  | yes      | Atom content                                       |
| `author`  | string  | no       | Public key identifier (`ed25519:...`)              |
| `sig`     | string  | no       | Signature of canonical atom bytes without `sig`    |

For v0.1, unsigned atoms are allowed. Signed atoms are preferred.

---

## 6. Atom Identity and Signature

### Identity

Each atom has a stable identity derived from its content:

```
atom_id = SHA-256(canonical_atom_bytes_without_sig)
```

**Canonical JSON rules:**
- Keys sorted lexicographically
- No whitespace
- UTF-8 encoding
- The `sig` field is excluded

`atom_id` is computed locally. It is never stored inside the atom and must never be trusted from external input.

### Signature

The signature covers the atom **without the `sig` field**:

```
sig = sign(canonical_atom_bytes_without_sig, private_key)
```

Verification must reconstruct canonical JSON without `sig` before checking.

---

## 7. Canonical Rule

Nodes must use the canonical Punkto form for storage and equality.

Canonical form:

```txt
p:<spatial>-<id>
```

Where `<spatial>` is a 12-character Base32 3D geohash.

A node must not silently rewrite canonical identifiers.

Derived forms such as `punkto://...` or web URLs may be accepted at API edges, but must resolve to exactly one canonical Punkto before storage.

---

## 8. Minimal HTTP API

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

## 9. Endpoint: `GET /health`

Returns basic node status.

Example response:

```json
{
  "status": "ok"
}
```

---

## 10. Endpoint: `GET /info`

Returns node metadata and capabilities.

Example response:

```json
{
  "node": "punkto-node-01",
  "version": "0.2",
  "capabilities": ["write", "sync"],
  "peers": ["https://node2.example.com"]
}
```

See `punkto.sync.md` for peer declaration rules.

---

## 11. Endpoint: `POST /atom`

Accepts a Punkto atom.

Example request:

```json
{
  "punkto": "p:u4pruydqqvj3-9xk3",
  "t": 1745598371000,
  "author": "ed25519:abc123...",
  "payload": "wind: 12m/s"
}
```

Example response:

```json
{
  "status": "accepted",
  "cursor": 1024,
  "punkto": "p:u4pruydqqvj3-9xk3"
}
```

If `EnableWrite=false`, the node must reject writes:

```json
{
  "error": "writes_disabled"
}
```

---

## 12. Endpoint: `GET /feed`

Returns atoms in append order.

Example response:

```json
{
  "cursor": 1024,
  "atoms": [
    {
      "punkto": "p:u4pruydqqvj3-9xk3",
      "t": 1745598371000,
      "payload": "wind: 12m/s"
    }
  ]
}
```

### Incremental sync

```txt
GET /feed?since=1024
```

Returns atoms appended after the cursor. Cursor is a byte offset into `atoms.ndjson`.

---

## 13. Endpoint: `GET /punkto/<canonical>`

Returns atoms for one canonical Punkto.

Example:

```txt
GET /punkto/p:u4pruydqqvj3-9xk3
```

Example response:

```json
{
  "punkto": "p:u4pruydqqvj3-9xk3",
  "atoms": [
    {
      "t": 1745598371000,
      "payload": "wind: 12m/s"
    }
  ]
}
```

---

## 14. Sharing

If `EnableShare=true`, a node may expose human-friendly public URLs.

Example:

```txt
https://node.example/p/u4pruydqqvj3/9xk3
```

Public share URLs are derived views.

They must resolve back to canonical Punkto form before lookup.

---

## 15. PWA Mode

If `EnablePWA=true`, the node may serve a Punkto web interface.

The PWA should allow users to:

* view nearby Punktos
* create local atoms
* submit atoms to the node
* inspect canonical IDs on demand
* sync when connectivity is available

The PWA is optional. A node without a PWA is still a valid node.

---

## 16. Synchronization

If `EnableSync=true`, nodes should sync using feed-based pull replication.

See `punkto.sync.md` for the full replication model.

Basic sync model:

1. Node A asks Node B for `/feed?since=<cursor>`
2. Node B returns newer atoms
3. Node A validates and appends accepted atoms

Nodes should tolerate:

* partial feeds
* duplicate atoms (deduplicated by `atom_id`)
* out-of-order timestamps
* unavailable peers

---

## 17. Validation Rules

A node must reject atoms when:

* `punkto` is missing
* `punkto` does not use canonical `p:` form
* `t` is missing
* `payload` is missing
* JSON is malformed

A node may reject atoms when:

* `sig` is present but invalid
* payload is too large
* author is blocked
* writes are disabled

---

## 18. Error Format

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
* `missing_t`
* `missing_payload`
* `writes_disabled`
* `sync_disabled`
* `not_found`

---

## 19. Non-goals for v0.1

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

## 20. Guiding Idea

> A Punkto node is not the source of truth.
>
> It is a place where spatial records can live, be read, and be replicated.

---

## 21. Changelog

| Version | Changes |
|---------|---------|
| v0.1 | Initial specification. |
| v0.2 | Field names aligned: `timestamp` → `t` (Unix ms int64), `signature` → `sig`. Canonical form updated to v0.2 (`p:<spatial>-<id>`). Atom identity and signature section added (§6). Cursor defined as byte offset. `EnableAI` clarified as discovery hint. |

---

## 22. Status

Draft v0.2
