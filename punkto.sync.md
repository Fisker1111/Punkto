# Punkto Sync — Peer Discovery and Feed Replication

> Draft proposal v0.2 — revised after peer review

---

## 1. Problem

Punkto nodes need to replicate atoms across the network without a central registry.

Global peer discovery is a non-goal for v0.1 (`punkto.node.md §18`).
This proposal covers the minimal mechanism needed for a small, intentional network.

---

## 2. Atom Identity

Each atom has a stable identity derived from its content:

```
atom_id = hash(canonical_atom_bytes)
```

Where `canonical_atom_bytes` is the atom serialized to canonical JSON (keys sorted, no whitespace).

**Rules:**

- `atom_id` is computed locally — it is never transmitted
- Two atoms at the same `punkto` and `t` are not duplicates unless their content is identical
- Nodes use `atom_id` to detect and skip duplicates during sync
- Recommended hash: SHA-256 (first 16 bytes as hex for compactness)

---

## 3. Peer Declaration

Each node declares its known peers in the `/info` response.

```json
{
  "node": "app1.punkto.xyz",
  "version": "0.2",
  "capabilities": ["write", "sync"],
  "peers": [
    "https://app2.punkto.xyz"
  ]
}
```

**Rules:**

- `peers` is an optional array of HTTPS base URLs
- A node with no peers omits the field or returns `[]`
- Peers are configured manually via the `PUNKTO_PEERS` environment variable
- A node does not auto-discover or auto-add peers

**Environment variable:**

```
PUNKTO_PEERS=https://app2.punkto.xyz,https://app3.punkto.xyz
```

---

## 4. Client Bootstrap

A PWA or client bootstraps from one known node URL (hardcoded or user-saved).

```
1. Client connects to DEFAULT_NODE_URL
2. Calls GET /info → reads peers[]
3. Peer hints are shown to the user — client does not add peers automatically
4. User decides which peers to trust and enable
5. Client syncs /feed from each approved node
```

No node is trusted more than another.
Peer hints from `/info` are advisory — the client does not blindly follow them.
The user or node operator controls which peers are active.

---

## 5. Feed Replication (Node to Node)

Each node with `sync` capability periodically pulls from its configured peers.

```
1. Node A reads PUNKTO_PEERS list
2. For each peer URL:
   a. Load last known cursor from sync_state.json
   b. GET <peer>/feed?since=<cursor>
   c. For each received atom:
      - Validate as if it were a local write (see punkto.node.md §16)
      - Compute atom_id = hash(canonical_atom_bytes)
      - If atom_id already known — skip
      - Otherwise append to local atoms.ndjson
   d. Save new cursor to sync_state.json
3. Repeat on interval (suggested: 60s)
```

**Cursor storage** (`sync_state.json`):

```json
{
  "https://app2.punkto.xyz": 1024,
  "https://app3.punkto.xyz": 512
}
```

Cursors are byte offsets as defined in `punkto.node.md §14`.
Cursors are stable because `atoms.ndjson` is append-only.

---

## 6. Loop Safety

When two nodes peer with each other (app1 ↔ app2), atoms flow in both directions.
Without deduplication, atoms loop forever.

**Prevention:**

- Every node deduplicates by `atom_id` before appending
- An atom already present in `atoms.ndjson` is never appended again
- Cursors ensure only new bytes are fetched per sync cycle
- No TTL or hop counter is needed — `atom_id` is sufficient

---

## 7. Validation

Every atom received from a peer is validated using the same rules as local writes.

Nodes must reject pulled atoms when:

- `punkto` is missing or not in canonical `p:` form
- `t` (timestamp) is missing
- JSON is malformed

Nodes may reject pulled atoms when:

- Signature is invalid
- Payload is too large
- Author is blocked

There is no relaxed validation mode for peer data.

---

## 8. Conflict Handling

There are no conflicts. Atoms are immutable and append-only.

- Duplicate atoms are detected by `atom_id` (hash of canonical atom bytes) and silently skipped
- Out-of-order timestamps are accepted
- Each node maintains its own append order

---

## 9. Topology

Peers form a manually configured mesh, not a tree or ring.

```
app1 ──── app2
  \        /
   app3 ──
```

Each node lists its direct peers. Indirect discovery (reading peers-of-peers) is optional and out of scope for v0.1.

---

## 10. Non-Goals (v0.1)

- Automatic peer discovery
- Peer-of-peer crawling
- Push / webhook replication
- Conflict resolution
- Guaranteed delivery
- Gossip protocol

---

## 11. Summary

Punkto Sync v0.1 uses manually configured peer lists and pull-based feed replication.

Nodes do not discover the global network.
Nodes do not push data.
Nodes do not resolve conflicts.

Each node periodically pulls append-only feeds from known peers, validates received atoms identically to local writes, deduplicates by `atom_id`, and appends new valid atoms to local storage.

| Component         | Mechanism                                         |
|-------------------|---------------------------------------------------|
| Atom identity     | `atom_id = hash(canonical_atom_bytes)`            |
| Node identity     | `PUNKTO_NODE_NAME` env var → `/info`              |
| Peer list         | `PUNKTO_PEERS` env var → `/info`                  |
| Client discovery  | Bootstrap from one URL → read peers[] as hints    |
| Peer trust        | User-controlled — no automatic peer adoption      |
| Replication       | Pull `/feed?since=<cursor>` on interval (60s)     |
| Cursor storage    | Byte offset per peer in `sync_state.json`         |
| Deduplication     | By `atom_id` before append                        |
| Validation        | Same rules as local writes — no relaxed mode      |
| Conflict handling | None needed (immutable append-only)               |

---

## Changelog

- **v0.2** — Peer review revisions: introduced `atom_id` for deduplication, added peer trust rules (no blind adoption), explicit loop safety section, validation parity with local writes, stronger summary
- **v0.1** — Initial draft

---

*Punkto Sync — draft v0.2*
