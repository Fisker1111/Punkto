# Punkto Sync — Peer Discovery and Feed Replication

> Draft proposal v0.1 — for peer review

---

## 1. Problem

Punkto nodes need to replicate atoms across the network without a central registry.

Global peer discovery is a non-goal for v0.1 (`punkto.node.md §18`).
This proposal covers the minimal mechanism needed for a small, intentional network.

---

## 2. Peer Declaration

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

## 3. Client Bootstrap

A PWA or client bootstraps from one known node URL (hardcoded or user-saved).

```
1. Client connects to DEFAULT_NODE_URL
2. Calls GET /info → reads peers[]
3. Stores all known nodes in local IndexedDB
4. Syncs /feed from each known node
5. User may add additional node URLs manually
```

No node is trusted more than another. The client assembles a local atom set from all peers.

---

## 4. Feed Replication (Node to Node)

Each node with `sync` capability periodically pulls from its configured peers.

```
1. Node A reads PUNKTO_PEERS list
2. For each peer URL:
   a. Load last known cursor from sync_state.json
   b. GET <peer>/feed?since=<cursor>
   c. Validate each atom (see punkto.node.md §16)
   d. Append accepted atoms to local atoms.ndjson
   e. Save new cursor to sync_state.json
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

---

## 5. Conflict Handling

There are no conflicts. Atoms are immutable and append-only.

- Duplicate atoms (same `punkto` + `t`) are silently skipped
- Out-of-order timestamps are accepted
- Each node maintains its own append order

---

## 6. Topology

Peers form a manually configured mesh, not a tree or ring.

```
app1 ──── app2
  \        /
   app3 ──
```

Each node lists its direct peers. Indirect discovery (reading peers-of-peers) is optional and out of scope for v0.1.

---

## 7. Non-Goals (v0.1)

- Automatic peer discovery
- Peer-of-peer crawling
- Push / webhook replication
- Conflict resolution
- Guaranteed delivery
- Gossip protocol

---

## 8. Summary

| Component         | Mechanism                              |
|-------------------|----------------------------------------|
| Node identity     | `NODE_NAME` env var → `/info`          |
| Peer list         | `PUNKTO_PEERS` env var → `/info`       |
| Client discovery  | Bootstrap from one URL → read peers[]  |
| Replication       | Pull `/feed?since=<cursor>` on interval |
| Cursor storage    | Byte offset per peer in sync_state.json |
| Conflict handling | None needed (immutable append-only)    |

---

*Punkto Sync — draft v0.1*
