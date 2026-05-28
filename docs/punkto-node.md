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

Human-readable node operator config. Intended to be future Node Admin editable. Contains:

- `/config/punkto-node.yml`

Operators should copy the generic example from
`docs/examples/punkto-node.example.yml` to `/config/punkto-node.yml` on their
server, then edit it for their own domain, hostnames, public URL, node name,
operator contact, storage paths, and seed nodes. The repository example uses
`example.org` values only; live production configs such as punkto.xyz's private
node config must stay outside Git.

The operator config is public/non-secret node personality and policy. It may
include domains, hostnames, public URLs, serving preferences, and bootstrap peer
URLs. Secrets, credentials, private keys, admin tokens, and production-only
private config values must stay outside Git.

### `/data`

Persistent node state: node identity, database, and local memory. Durable node
state includes:

- node database
- node identity key
- sync state
- node-local serving metadata
- pinned/archive/block state

`/data` must survive container restarts and image upgrades. Losing `/data` means
losing local node memory and may create a new node identity if the node key is
not restored.

### `/logs`

Optional diagnostics and troubleshooting logs.

Suggested host mounts:

```yaml
./punkto-config:/config
./punkto-data:/data
./punkto-logs:/logs
```

## Reference deployment naming

Punkto.xyz is the first reference deployment, but Punkto is not tied to the
`punkto.xyz` domain. Public node software should be deployable by any operator
on any domain.

Preferred reference naming is `node1`, `node2`, and so on, for example
`node1.example.org` and `node2.example.org`. The older `app1` and `app2` names
are legacy/reference aliases from the first punkto.xyz deployment and may remain
in old deploy docs or Caddy files; new examples should prefer `node1`/`node2`.

An operator in Nairobi, Brazil, or any other deployment environment can set
their own values for `core.domain_dns`, `core.hostnames`, `core.public_url`,
`operator.node_name`, and `network.seed_nodes` in `/config/punkto-node.yml`.

## Node config file

Primary operator config path:

- `/config/punkto-node.yml`

Operators should start by copying the checked-in generic example to their host
mount and editing it there:

```bash
mkdir -p ./punkto-config ./punkto-data ./punkto-logs
cp docs/examples/punkto-node.example.yml ./punkto-config/punkto-node.yml
```

This file controls **node policy and identity metadata**, not protocol validity
of Punki/atoms. Protocol truth remains in the atom/Punkti record; serving
behavior is a node-local policy choice.

The generic example uses these top-level operator-oriented sections:

- `core` — DNS domain, hostnames, and public URL for the deployment
- `roles` — whether the deployment serves web, relay, and database-sharing roles
- `network` — seed node URLs used for bootstrapping/sync policy
- `operator` — public node/operator display metadata and contact field
- `storage` — persistent paths such as `/data`, database, and node key path
- `serving` — high-level serving preferences such as recent, pinned, and archive

Current relay builds may also understand an earlier runtime schema with
`node`, `admin`, `serving_policy`, `bootstrap`, `moderation`, and `retention`.
Extra top-level fields from the generic example are tolerated by the current
loader and should be treated as operator/future-facing fields unless a runtime
release explicitly wires them into behavior. Missing optional fields must not be
fatal; safe defaults are used.

`/config/punkto-node.yml` is intended to be public/non-secret. Do not put
secrets, credentials, admin tokens, private node keys, or real private
production config in it if that file may be committed or shared. The node key
lives under `/data/node-key.json` by default and is persistent node state, not a
Git-tracked example.

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
