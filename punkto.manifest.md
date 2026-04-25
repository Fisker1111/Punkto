# Punkto Manifest (v0.1)

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

* store Punktos as **append-only records**
* preserve original data (no mutation)
* allow sequential access

Recommended format:

* NDJSON (newline-delimited JSON)

---

## 3. Data Model

A Punkto record should contain:

* `punkto` → canonical identifier
* `timestamp` → ISO8601
* `author` → public key
* `signature` → cryptographic signature
* `payload` → message content

---

## 4. Example Record

```json
{
  "punkto": "p:u4pruydqqvj-42m-9xk3",
  "timestamp": "2026-04-25T10:00:00Z",
  "author": "ed25519:abc123...",
  "signature": "sig:xyz...",
  "payload": "wind: 12m/s"
}
```

---

## 5. Sync Model

Nodes should support:

* HTTP-based replication
* range requests for incremental sync
* pull-based synchronization

No global coordination required.

---

## 6. Validation

Implementations must:

* validate Punkto format
* verify signatures
* reject malformed records

---

## 7. Interoperability

A Punkto-compatible system must:

* accept valid Punkto identifiers
* expose data in a standard format
* allow replication with other nodes

---

## 8. No Central Authority

* no global registry
* no ownership system
* no required identity provider

Trust is derived from signatures.

---

## 9. Deployment

A Punkto node may be:

* local (device)
* edge (sensor, drone)
* server (hosted)

All are equal in the network.

---

## 10. Status

Draft v0.1 — implementation baseline
