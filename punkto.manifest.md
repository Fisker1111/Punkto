# Punkto Manifest (v0.2)

> Defines how a Punkto implementation behaves and interoperates.

---

## 1. Purpose

The manifest describes:

* how Punkto data is stored
* how it is exposed
* how nodes sync

---

## 2. Storage

Implementations must:

* store atoms as **append-only records**
* preserve original data (no mutation)
* allow sequential access

Recommended format:

* NDJSON (newline-delimited JSON)

---

## 3. Data Model

A Punkto atom contains:

| Field     | Type   | Required | Description                                     |
|-----------|--------|----------|-------------------------------------------------|
| `punkto`  | string | yes      | Canonical `p:` address (12-char 3D geohash)     |
| `t`       | int64  | yes      | Unix timestamp in milliseconds (13 digits)      |
| `payload` | string | yes      | Atom content                                    |
| `author`  | string | no       | Public key identifier (`ed25519:...`)           |
| `sig`     | string | no       | Signature — signs canonical atom without `sig`  |

---

## 4. Example Record

```json
{
  "punkto": "p:u4pruydqqvj3-9xk3",
  "t": 1745598371000,
  "author": "ed25519:abc123...",
  "sig": "base64:...",
  "payload": "wind: 12m/s"
}
```

---

## 5. Sync Model

Nodes should support:

* pull-based feed replication via `/feed?since=<cursor>`
* append-only storage (no rewrites)
* deduplication by `atom_id = SHA-256(canonical_atom_bytes_without_sig)`

See `punkto.sync.md` for the full replication model.

---

## 6. Canonical Form

All implementations must use the canonical Punkto form:

```
p:<spatial>-<id>
```

Where `<spatial>` is a 12-character Base32 3D geohash (interleaved lat+lon+alt).

See `punkto.md` for full canonical rules.

---

## 7. Atom Identity

Atom identity is derived, not stored:

```
atom_id = SHA-256(canonical_atom_bytes_without_sig)
```

Canonical JSON rules: keys sorted lexicographically, no whitespace, UTF-8 encoding, `sig` field excluded.

`atom_id` is never embedded in the atom and must never be trusted from external input.

---

## 8. Signature

The `sig` field signs the canonical atom without `sig`:

```
sig = sign(canonical_atom_bytes_without_sig, private_key)
```

Signed atoms are preferred. Unsigned atoms are permitted in v0.1 for local-first usage.

---

## 9. Compatibility

Punkto is compatible with the Punkti protocol:

* `punkto` field maps to Punkti `h` (Base32 3D geohash, 4–12 characters)
* `t` field maps to Punkti `t` (Unix milliseconds, int64)

A Punkto atom at 12-character spatial precision is a valid Punkti atom.

---

## 10. Changelog

| Version | Changes |
|---------|---------|
| v0.1 | Initial manifest. |
| v0.2 | Field names aligned: `timestamp` → `t` (Unix ms int64), `signature` → `sig`. Canonical form updated to v0.2. Atom identity, signature, and compatibility sections added. |

---

## 11. Status

Draft v0.2
