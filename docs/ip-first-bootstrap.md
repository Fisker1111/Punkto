# IP-first bootstrap model

## Status

This is protocol and operator design documentation. It defines the intended Punkto bootstrap model and does not imply that every field or endpoint described here is implemented today.

Punkto may use DNS and HTTPS as a friendly public service layer, but Punkti must not require DNS, HTTPS, Cloudflare, app stores, or any central service. Bootstrap must survive when a node is reachable only by IP address and port.

Core principle:

- Punkto can use DNS/HTTPS for convenience.
- Punkti node sync must work with `IP:port + node_id`.
- DNS is optional naming.
- HTTPS is recommended for public web/PWA convenience.
- `node_id` / fingerprint is node identity.
- Atom signatures and local trust policy are the trust layer.
- Bootstrap must survive without DNS.

## Endpoint vs identity

A node has at least two separate concepts:

| Concept | Meaning | Examples |
|---|---|---|
| `endpoint` | How to reach a node right now | `https://node1.punkto.xyz`, `http://197.33.23.33:7777`, `http://192.168.1.50:7777` |
| `node_id` | Who the node is | `node:abc123...` |

Rules:

- A URL is reachability, not identity.
- DNS names can change ownership or point to different machines.
- IP addresses can change, be reassigned, or be unreachable from some networks.
- `node_id` / fingerprint is the stable node identity operators and clients remember.
- Trust must not depend on DNS alone.
- When a configured endpoint returns a different `node_id` than expected, the node/client should treat that as an identity change and apply local policy before trusting it.

Current `/node/info` exposes the node fingerprint in `node.fingerprint` and the backwards-compatible `node_fingerprint` alias. Future docs may standardize the public field name as `node_id`, but the identity concept is the same: a stable fingerprint for the node key.

## DNS is optional

DNS and HTTPS are recommended for public web-facing nodes because they are easier for people to type, easier for browsers to access, and easier to secure with normal certificates.

They are not protocol requirements:

- `IP:port` is valid for Punkti node sync.
- Ordinary users and small node operators do not need to own a domain.
- A small operator should be able to run a node with only a public IP address and an open port.
- A local/LAN node may be reachable as `http://192.168.1.50:7777` for local sync.
- Community/bootstrap nodes may help users find reachable nodes.
- DNS is convenience naming, not a trust root and not a required bootstrap dependency.

## Bootstrap sources

A node/client may discover initial or additional peers from several sources. None of these sources should automatically imply trust.

Possible bootstrap sources:

1. Built-in seed list shipped with the software.
2. `/config/punkto-node.yml` `network.seed_nodes` entries chosen by the operator.
3. `/data/known-peers.json` learned peer cache.
4. Manual peer add by `IP:port` or URL.
5. QR/imported peer record.
6. Peers learned from `/node/info` or a future `/peers` endpoint.
7. DNS/HTTPS discovery when available.

Bootstrap source priority is local policy. A hardened node may use only explicit operator-configured seeds. A casual node may also use learned peers and community seed lists.

## Config vs learned peers

`/config/punkto-node.yml` is operator intent. It tells the node where to start and which peers the operator intentionally named.

`/data/known-peers.json` is learned network memory. It records peers discovered while running, including last-seen metadata and trust state, and may be rebuilt over time.

| File | Purpose | Persistence | Git policy |
|---|---|---|---|
| `/config/punkto-node.yml` | Operator intent and starting seeds | Persistent config mount | Do not commit live production copies |
| `/data/known-peers.json` | Learned peer cache/network memory | Persistent data mount | Never commit live data |

Future structured config example:

```yaml
network:
  seed_nodes:
    - url: "https://node1.punkto.xyz"
      node_id: "node:abc123..."
    - url: "http://197.33.23.33:7777"
      node_id: "node:def456..."
```

Future learned peer cache example:

```json
[
  {
    "url": "http://197.33.23.33:7777",
    "node_id": "node:def456...",
    "last_seen": "2026-06-02T12:00:00Z",
    "source": "manual",
    "trusted": false
  }
]
```

A learned peer can be useful without being trusted. For example, a node may use an untrusted peer as a reachability hint, fetch signed atoms, dedupe by `atom_id`, and still apply local signature, age, and trust policy before serving or accepting data.

## Sync/discovery flow

Basic IP-first sync and discovery flow:

1. Node/client starts with configured seeds.
2. It tries reachable endpoints, including DNS names and/or `IP:port` URLs.
3. It reads `GET /node/info` from each reachable endpoint.
4. It verifies or records the returned node identity (`node.fingerprint`, `node_fingerprint`, or future `node_id`).
5. It pulls `GET /feed` or `GET /feed?since=<cursor>`.
6. It may learn peer hints from `/node/info` or a future `/peers` endpoint.
7. It stores useful peers in `/data/known-peers.json`.
8. It continues syncing with a node-local cursor for each endpoint/identity.
9. It dedupes globally by `atom_id`, not by URL or cursor.

Cursor reminder:

- `cursor` is node-local delivery position.
- `atom_id` is global atom identity.
- A changed endpoint may still be the same node if the `node_id` is unchanged.
- The same endpoint may be a different node if the `node_id` changes.

## Trust model

Punkto bootstrap separates reachability, identity, and trust:

| Layer | Meaning | Trust rule |
|---|---|---|
| URL / endpoint | How to connect | Useful but not trusted by itself |
| `node_id` / fingerprint | Which node answered | Stable identity to verify, remember, and apply policy to |
| Atom/Punkti signatures | Whether atom content is signed by the claimed author/device | Primary content authenticity layer |
| Local/operator policy | Which nodes/sources get special treatment | The actual trust decision |

Trust principles:

- URL is reachability.
- `node_id` is identity.
- Trust is local/operator policy.
- `trusted_backfill_nodes` should refer to node identity where possible in future, not only DNS names.
- DNS/HTTPS may assist discovery and transport security, but must not be the only trust root.
- Do not trust bootstrap lists blindly.
- Do not assume an `IP:port` node is trusted merely because it is reachable.

## Security notes

- Plain HTTP over `IP:port` is acceptable for basic node transport only if atom signatures and node identity are verified by the syncing node/client.
- HTTPS is still recommended for browser/PWA access, public web nodes, and protection against passive network observers.
- Browser security rules may limit HTTP/IP usage from an HTTPS-loaded PWA because of mixed-content restrictions and secure-context requirements.
- Node-to-node sync can be more flexible than browser clients because a backend relay can choose its own transport policy.
- DNS names, HTTPS certificates, and CDN configuration can improve usability and transport security, but they do not replace node identity and signed data validation.
- Bootstrap sources are hints. Treat them as untrusted until local policy says otherwise.

## Future implementation notes

The following are future design items unless already implemented elsewhere:

- `node_id` in `network.seed_nodes` structured config entries.
- `/data/known-peers.json` learned peer cache.
- `/peers` endpoint for explicit peer exchange.
- Signed node records binding `node_id`, endpoints, capabilities, and timestamps.
- QR peer import for offline/manual bootstrap.
- Manual peer add in operator tools.
- Trust levels for peers and backfill permissions.
- `last_seen`, source, capabilities, and reachability metadata for peers.
- Policy that pins trust to `node_id` and treats endpoint changes as normal but identity changes as security-relevant.

These notes are intentionally documentation-only. They do not change relay behavior, PWA behavior, config parsing, deployment, or runtime trust policy.
