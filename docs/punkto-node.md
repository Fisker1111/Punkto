# Punkto Deployable Node Model

## Purpose

Punkto should be runnable by independent operators in many countries and hosting environments, without requiring a central host.

This model treats a deployable Punkto node as three long-lived components plus a container image:

- Docker image is software.
- Persistent mounted volumes are node memory.
- Config file is node personality.
- Database is node history/state.
- Node identity must survive restarts.

The image may be upgraded frequently, while identity, policy, and history must remain stable across restarts and upgrades.

## Operator promise

A Punkto node operator should be able to:

- clone this repository or use a published image
- mount `/config` and `/data` (and optionally `/logs`)
- start with Docker Compose
- upgrade image versions without losing identity/data/config
- understand what the node serves and why

Mental model:

- Docker image = software
- `/config` = node personality
- `/data` = node memory
- `/logs` = diagnostics


## Common code, node config, and node data

Punkto is public-good node software. The repository should hold the common
software and public documentation needed for anyone to run a node, while each
operator keeps their own node personality, persistence, and secrets outside Git.

Core principle:

- **Code is common and public.**
- **Config is node-specific.**
- **Data is node-specific and persistent.**
- **Secrets are never committed.**
- **`punkto.xyz` is the reference deployment, not the whole system.**
- **Anyone should be able to run a Punkto node on their own domain.**

### Git/repository model

These repository paths are common project assets:

| Path | Role | Commit policy |
|---|---|---|
| `pwa/` | Common web app served by nodes | Commit shared app code only |
| `relay/` | Common relay/node code | Commit shared relay behavior only |
| `deploy/` | Reusable deployment templates and historical/reference deploy helpers | Commit generic templates; do not treat as live truth |
| `docs/` | Public documentation | Commit operator-facing docs |
| `docs/examples/punkto-node.example.yml` | Generic example node config | Safe to commit because it uses `example.org` and no secrets |

The code in `pwa/` and `relay/` is common to the network. Operators should not
need a private fork just to run a different node name, domain, peer set, storage
path, or serving policy. Those choices belong in node-local config.

### Node-local files

These files belong on each node host, not as production truth in the repository:

| Node-local path | Meaning | Git policy |
|---|---|---|
| `/config/punkto-node.yml` | Operator config: the node's personality | Do not commit live production copies |
| `/data/node-key.json` | Persistent node identity | Never commit |
| `/data/punkto.db` or equivalent | Local atom data and node state | Never commit |
| `.env` / `secrets.env` | Local environment overrides and secrets | Never commit |

`/config` is the node's **personality**: public URL, hostnames, operator label,
roles, seed nodes, storage paths, and serving policy. Changing `/config` changes
how that node presents itself and participates in the network.

`/data` is the node's **memory**: node identity, local atom database, sync state,
and durable node-local state. `/data` must survive container rebuilds, image
upgrades, and restarts. Deleting or replacing `/data/node-key.json` changes node
identity. Deleting the local database removes that node's local history.

`.env` and `secrets.env` are local operational inputs. They may contain image
tags, credentials, tokens, or emergency overrides. They are node-local and must
not be committed.

### Public node endpoints

Every node should expose a small set of public read-only status endpoints:

| Path | Audience | Format | Purpose |
|---|---|---|---|
| `/status` | Humans/operators/readers | HTML | Human-readable public node status page |
| `/node/info` | Clients/tools | JSON | Public-safe node status/config/API summary |
| `/health` | Load balancers/monitors | JSON | Tiny health check |
| `/feed` | Clients/readers | JSON | Public atom feed for data-flow visibility and sync |
| `/latest` | Clients/readers | JSON | Recent public atoms, newest first |

`/status` is public but read-only. It may explain the node's public URL,
identity fingerprint, software version, config-loaded state, roles, serving
policy, peers, feed stats, public data-flow endpoints, health, and a compact
recent public atom preview using only the same safe public fields as
`/node/info` plus public feed metadata. It must not expose secrets, private
keys, `.env` values, local tokens, raw database dumps, server logs, or write
controls.

Configuration changes are done by the node operator on the server, normally over
SSH by editing node-local config and restarting/reloading the service. The web
can explain the node; SSH controls the node.

### Reference deployment names

Use `node1` and `node2` as preferred reference names in public examples and new
operator docs. The older names `app1` and `app2` may still appear as
legacy/reference aliases in existing deployment history, DNS, scripts, or live
ops notes; avoid introducing them as the primary model for new documentation.

### `punkto.xyz` boundary

`punkto.xyz` is the reference deployment for the project. It is not the entire
system and should not be hard-coded as the only valid Punkto deployment target.
Production config for `punkto.xyz` is maintained on the nodes by the operator and
must not be committed as live truth. Public examples in Git should use
`example.org` or other documentation-safe placeholders.

Deploy templates in this repository are reusable starting points, not an
authoritative snapshot of what is currently running in production. When docs,
examples, and live nodes differ, operators should treat live node-local files as
the production source of truth and the repository as common code plus reusable
documentation/templates.

## Persistent directory model

Deployable nodes should use persistent host mounts for:

- `/config`
- `/data`
- `/logs`

### `/config`

Human-readable node config. Intended to be future Node Admin editable. Contains:

- `/config/punkto-node.yml`

### `/data`

Durable node state, including:

- node database
- node identity key
- sync state
- node-local serving metadata
- pinned/archive/block state

### `/logs`

Optional diagnostics and troubleshooting logs.

Suggested host mounts:

```yaml
./punkto-config:/config
./punkto-data:/data
./punkto-logs:/logs
```

## Node config file

Primary config path:

- `/config/punkto-node.yml`

This file controls **node policy and identity metadata**, not protocol validity of Punki/atoms. Protocol truth remains in the atom/Punkti record; serving behavior is a node-local policy choice.

Current documentation example top-level sections:

- `core` — DNS domain, hostnames, and public URL
- `roles` — which node roles are enabled
- `network` — seed nodes and peer bootstrap inputs
- `operator` — public operator labels/contact metadata
- `storage` — persistent data, atom log, database, and node-key paths
- `serving` — node-local serving policy switches
- `acceptance` — node-local live-forward acceptance/backfill policy

A generic example lives at `docs/examples/punkto-node.example.yml`. It uses
`example.org`, `node1`, and `node2` intentionally so it is safe to commit and
safe for operators to copy before editing.

### Live-forward acceptance and serving config

Punkto nodes are live-forward by default, closer to an old public IRC flow than a full public archive. The relay may durably store more atoms than it normally serves. Operators configure two related but separate policies:

```yaml
serving:
  serve_recent_hours: 24
  serve_pinned: true
  serve_archive: false
  pinned_atoms: []

acceptance:
  accept_recent_hours: 24
  trusted_backfill_nodes:
    - https://node1.example.org
    - https://node2.example.org
```

Policy meanings:

- `acceptance.accept_recent_hours` limits normal public `POST /atom` submissions by the claimed atom timestamp (`t`). If an atom claims to be older than the window, the relay rejects it with `atom_too_old`. Old atoms are not trusted merely because they claim an old time.
- `acceptance.trusted_backfill_nodes` lists public peer node URLs that may backfill older atoms during relay sync. Trusted backfill affects acceptance only; it does not make the atom's claimed time the node's delivery time.
- `serving.serve_recent_hours` limits normal `/feed` and `/latest` responses to recent public flow. The durable atom log can still contain older accepted atoms.
- `serving.serve_pinned` and `serving.pinned_atoms` allow specific atom IDs, including future genesis atoms, to remain served outside the normal recent window.
- `serving.serve_archive` is reserved for explicit future archive nodes. It should remain `false` unless an operator intentionally enables archive behavior in a future version.

The current relay stores accepted atoms as atom-only JSONL in `/data/atoms.log.jsonl`. It does not inject relay metadata into the signed/canonical atom before computing `atom_id`. A future envelope/index can add node-local `seen_t` and `log_seq` metadata outside the canonical atom; until then, serving policy uses the best available atom timestamp while the append-only log remains durable truth.

## Conversation model: ROOT/REPLY atoms

Punkto public conversations are modeled as boards rooted at one exact real-world
point. A ROOT atom starts a board, and REPLY atoms join the board only by
explicit parent/root atom ids, not by proximity. Replies must copy the root
location tuple exactly and must not move the board.

See `docs/protocol-root-reply.md` for the documentation-first protocol model,
future fields, exact-location rule, orphan reply behavior, and examples. This is
design documentation only; current relay validation, storage, sync, and PWA UI
behavior are unchanged.

## Node identity

Persistent atom log path:

- `/data/atoms.log.jsonl`
- override with `PUNKTO_ATOM_LOG_PATH=/path/to/atoms.log.jsonl`
- backup/restore procedures must include this file; it is the durable source of accepted public atoms
- SQLite remains a future rebuildable index/cache, not the authoritative storage layer

Persistent node identity path:

- `/data/node-key.json`
- override with `PUNKTO_NODE_KEY=/path/to/node-key.json`

Boot behavior model:

- First boot:
  - create node key if missing
  - persist key JSON to `/data/node-key.json`
  - log `Created new node identity` + public fingerprint
- Later boot:
  - load the same key from disk
  - log `Loaded existing node identity` + fingerprint
  - never silently rotate
- Corrupt/invalid key file:
  - fail safe with operator-facing error
  - do not overwrite or delete the existing file automatically

Current relay key file shape:

```json
{
  "version": 1,
  "key_alg": "sha256-secret-v1",
  "created_at": "2026-05-21T00:00:00Z",
  "public_key": "...",
  "private_key": "...",
  "fingerprint": "node:ab12cd34ef56"
}
```

Notes:
- Relay currently uses a minimal persisted node identity mechanism (`sha256-secret-v1`) for continuity because backend Ed25519 key deps are not yet wired in relay runtime.
- Fingerprint is deterministic from public key and safe for logs/status.
- Node identity is relay/node scope only and must not be mixed with PWA user identity keys.

Identity principles:

- If the key changes, this is a **new node identity**.
- Trust and future verification depend on stable node identity.
- Node key is distinct from user/device identity key used in the PWA.

## Serving policy model

Nodes may store more records than they actively serve.

Definitions:

- **stored**: node has the record locally
- **served**: node exposes record via normal feed/API/sync
- **pinned**: node intentionally keeps and serves the record
- **archive**: node stores for history, but may not show/serve by default
- **blocked**: node refuses to serve the record
- **stale/cold**: node has aged the record out of normal serving

A record cannot demand permanent service. The operator policy decides whether a stored record is served, pinned, archived, blocked, or aged out.

Current relay behavior:

- Normal public `POST /atom` accepts only recent atoms according to `acceptance.accept_recent_hours`.
- Sync from URLs listed in `acceptance.trusted_backfill_nodes` may accept older atoms as backfill; non-trusted peers are held to the same recent acceptance window as public clients.
- `/feed` and `/latest` serve recent atoms according to `serving.serve_recent_hours`, plus pinned atom IDs when `serving.serve_pinned` is enabled.
- `serving.serve_archive=false` means normal public feed endpoints are not a full old archive, even though `/data/atoms.log.jsonl` remains the durable internal record.


## Node-local metadata

Node-local serving metadata (conceptual) should include:

- `serve_state`:
  - `served`
  - `not_served`
  - `blocked`
- `serve_class`:
  - `genesis`
  - `pinned`
  - `recent`
  - `archive`
  - `stale`
  - `cold`
  - `blocked`
- `retention`:
  - `forever`
  - `days:N`
  - `policy`
  - `manual`

Important boundary:

- This metadata is node-local.
- It is not necessarily part of the signed Punkti record.
- Different nodes may make different serving choices for the same record.

## Node types

Conceptual node profiles:

- **flow node**: serves recent/hot Punktis
- **archive node**: keeps deeper history
- **community node**: pins/serves local or community-approved Punktis
- **private node**: restricted/private operator use
- **registry node**: future identity/node trust registry responsibilities
- **official Punkto node**: serves public flow plus genesis/pinned records

## Genesis Punkti policy

Future permanent genesis Punkti concept (from Omni Teater):

- Title: **Punkto begins here**
- Body: **First public Punkti from Omni Teater. A coordinate in reality can carry meaning.**

Target serving policy for genesis record(s):

- `serve_state: served`
- `serve_class: genesis`
- `retention: forever`

Policy intent:

- official Punkto nodes should always serve genesis records
- client DB reset should not remove genesis from the network
- genesis records should be inserted/served through normal node feed later

This PR does **not** implement genesis insertion. Runtime serving can keep configured genesis atom IDs visible by listing their `atom_id`s in `serving.pinned_atoms` while `serving.serve_pinned` is enabled.

## Node Admin UI (future)

A future Node Admin UI should read/write node config and display node state.

### Responsibility split

**PWA Settings (user scope):**

- user/device identity
- local app state
- user key

**Node Admin (operator scope):**

- node identity
- node URL
- serving policy
- peer/bootstrap policy
- persistence
- moderation
- archive/retention
- disk/storage
- node health

### Node Admin dashboard should show

- node name
- public URL
- node fingerprint
- operator contact
- node type
- serving policy summary
- storage usage
- known peers
- sync status
- stored/served/pinned/archive counts
- blocked authors/nodes
- admin actions

## Bootstrap and peers

Punkto uses an **IP-first bootstrap model**: DNS/HTTPS are useful convenience layers, but Punkti node sync must not require domain ownership, Cloudflare, app stores, or any central service. A node endpoint is how to reach a node; `node_id` / fingerprint is who the node is. Trust must be attached to node identity and local operator policy, not to DNS alone.

See `docs/ip-first-bootstrap.md` for the full endpoint-vs-identity model, bootstrap sources, config-vs-learned-peer split, sync/discovery flow, security notes, and future implementation fields.

Peer sources should be config-controlled:

- **seed nodes**: built-in or configured bootstrap nodes, including DNS/HTTPS URLs or `IP:port` endpoints
- **discovered peers**: learned from `/node/info` or future peer exchange
- **learned peer cache**: future `/data/known-peers.json` network memory
- **blocked nodes**: never use
- **user-added peers**: operator configured manually by URL, `IP:port`, or imported peer record

Principles:

- bootstrap should be config-driven
- DNS is optional naming, not a protocol requirement
- IP:port endpoints are valid for node sync
- adding peers should not automatically imply trust
- `trusted_backfill_nodes` should refer to node identity where possible in future, not only DNS names
- node trust and reputation are future work

## Security and safety principles

- Do not trust nodes blindly.
- Atom/Punkti signatures matter more than node trust.
- Node identity supports operator/network reputation, not atom validity by itself.
- Unsigned Punktis may be allowed in early phases, but must be labeled honestly.
- Admin interface must not be public by default.
- Config examples must not include real secrets.
- Node key must be persisted and protected.

## Future implementation roadmap

### Phase 1

- docs and example config

### Phase 2 (started)

- relay loads `/config/punkto-node.yml` (or `PUNKTO_NODE_CONFIG` override) with safe defaults
- expose read-only `/status` as a human public node status page with public data-flow links, feed health stats, and a compact newest-public-atoms preview
- expose read-only `/node/info` with a public-safe node config summary
- keep `/health` as a tiny health check
- keep `/feed` and `/latest` visible as public read-only atom data endpoints without exposing raw database dumps or server logs
- relay creates/loads `/data/node-key.json` (or `PUNKTO_NODE_KEY` override) with stable fingerprint continuity
- `/node/info` includes public node identity fields only:
  - `node_fingerprint`
  - `node_key_alg`
  - `node_identity_loaded`
  - `node_identity_created_at`

### Phase 3

- node-local serving metadata
- policy engine marks records served/pinned/archive/stale

### Phase 4

- genesis Punkti seed
- official nodes always serve genesis records

### Phase 5

- basic Node Admin UI
- config/state visible
- safe policy edits

### Phase 6

- verified node identities
- trust registry
- archive proofs
- proof-of-service later

---

## See Also

- [Fresh Ubuntu Install Guide](fresh-install-ubuntu.md) — Step-by-step guide from fresh server to running node
