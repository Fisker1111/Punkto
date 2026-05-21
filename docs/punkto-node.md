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

Required top-level config sections:

- `node`
- `admin`
- `serving_policy`
- `bootstrap`
- `moderation`
- `retention`

## Node identity

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

This PR does **not** implement genesis insertion or runtime serving behavior.

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

Peer sources should be config-controlled:

- **seed nodes**: built-in or configured bootstrap nodes
- **discovered peers**: learned from network later
- **blocked nodes**: never use
- **user-added peers**: operator configured

Principles:

- bootstrap should be config-driven
- adding peers should not automatically imply trust
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
- expose read-only `/node/info` with a public-safe node config summary
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
