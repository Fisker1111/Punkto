# Self-host a Punkti node

This image ships **punkti-mesh/0.6-draft**, an unfrozen Layer-3 Mesh reference.
It does not implement the production Pilot relay API. Carrier, wire, signatures,
validation and MID semantics are unchanged. `carrier.py` and `spatial.py` are
byte-identical to the experimental originals. Mesh additions are operational
hooks, configurable bind/advertise origins and http(s) peer origins only.

## First start

Requires Docker with Compose. From this repository:

```sh
mkdir -p node-config node-data
cp node-config.example.yml node-config/punkto-node.yml
# Edit node-config/punkto-node.yml as needed.
docker compose -f docker-compose.node.yml up -d
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8000/node/info
```

The image must first have been published by a version tag or manual workflow.
For a local build, uncomment the `build` alternative in the Compose file and run
`docker compose -f docker-compose.node.yml up -d --build`.
The generic image has no built-in peers or domain names. The default configuration
accepts all spatial records but exchanges nothing until peers are configured.
Compose publishes port 8000 on all host interfaces. For localhost-only access,
change its port mapping to `127.0.0.1:8000:8000`.

The entrypoint creates/owns the configured data directory as UID/GID 10001 and
then drops privileges before execing Python. The service runs non-root. Mount the
config read-only and the data directory read-write. Custom paths must also be
mounted persistently and made accessible to UID 10001. One process owns each data
directory; never share a volume between running nodes. Startup ownership changes
apply to that dedicated data directory only.

## Configuration

The complete, commented canonical schema is in
[`node-config.example.yml`](../node-config.example.yml). Copy it without removing
comments. The following is the complete configuration with field guidance:

```yaml
node:
  name: alice-node              # Local display label, not atom/protocol identity.
  public_url: ""                # Public http(s) origin, or derive from bind address.
  description: ""               # Public operational text.
  operator_contact: ""          # Local only; never included in /node/info.
network:
  listen_host: 0.0.0.0          # IPv4 address or hostname to bind.
  listen_port: 8000             # Change Compose mapping if changing this port.
  advertise_url: ""             # Override public_url for peer callbacks.
  peers: []                     # Exact origins; no credentials/path/query/fragment.
  sync_interval_seconds: 30     # First attempt after 2s, then interval after completion.
subscriptions:                 # Omit = global; [] = accept nothing.
  - xy_lo: null                # Inclusive 1–12 character XY lower bound.
    xy_hi: null                # Exclusive XY upper bound; null = unbounded.
    z_min: null                # Inclusive canonical decimal Z string, or unbounded.
    z_max: null                # Exclusive canonical decimal Z string, or unbounded.
storage:
  data_path: /data             # Durable volume, one writer.
logging:
  level: info                  # debug, info, warning, error; stdout event lines.
branding:
  display_name: Punkti Node    # Public status display label only.
```

Validate without binding a socket or creating storage:

```sh
python3 -m pip install -r node/requirements.txt
python3 -m punkti_node --check-config --config node-config.example.yml
# Or using the image/config mount:
docker compose -f docker-compose.node.yml run --rm node --check-config
```

For direct execution use Python 3.12 and
`python -m punkti_node --config node-config/punkto-node.yml`.
The container entrypoint initializes volume permissions even for check-config;
the Python check itself only validates configuration. Missing explicit config,
unknown keys, invalid bounds and invalid origins fail startup clearly.

### Local-only versus protocol-visible

| Setting/data | Visibility and effect |
| --- | --- |
| node.name, description, public_url; branding.display_name | Operationally public via `/node/info`; no effect on atom identity or signatures |
| operator_contact | LOCAL-ONLY configuration; not exposed by info |
| listen_host, listen_port | LOCAL-ONLY binding; used to derive advertised origin if unset |
| advertise_url | PROTOCOL-VISIBLE callback origin in `/sync`; public_url is fallback |
| peers | PROTOCOL-VISIBLE `/hello` hints and operational info; only configured peers can request callbacks |
| subscriptions | PROTOCOL-VISIBLE `/hello`; admission and spatial synchronization scope |
| data_path, logging.level, sync interval | LOCAL-ONLY; data path never exposed in info |
| epoch | PROTOCOL-VISIBLE store incarnation/cursor binding; stable across restart |
| build, counts, metrics, config basename | Operationally public; not atom truth |

Never place credentials in URLs, node descriptions or labels. These operational
endpoints are unauthenticated and public-safe by field selection. Protect the
listening interface according to your deployment. TLS termination belongs to an
operator-managed reverse proxy. The image serves HTTP internally.

### Rename or rehost

Change `node.name`, `branding.display_name` or `node.description` and recreate the
container; no image rebuild is needed. To rehost, update DNS/TLS/reverse proxy and
`network.advertise_url` or `node.public_url`, then update other nodes' configured
peer origins. Preserve the data volume. Atoms, their IDs and store epoch remain
unchanged. Advertise precedence is `network.advertise_url`, then `node.public_url`,
then the listen origin (0.0.0.0 derives to 127.0.0.1). Set a reachable origin for
remote peers; a derived loopback URL is only useful on the same host.

### Peers and bootstrap

Use explicit origins such as `https://alice.example` or `http://node-b:8000`.
Trailing slashes, paths, credentials, queries, fragments and non-http(s) schemes
are rejected. Peers should configure each other because `/sync` callbacks require
the caller's advertised origin to be locally configured. Two containers on one
Docker network can advertise `http://node-a:8000` and `http://node-b:8000` and use
these as reciprocal peers. Do not use container loopback to reach another node.

There is no hard-coded bootstrap and discovered hints are not automatically
trusted/connected. Use only compatible draft Mesh peers, not legacy relay URLs.
The worker calls `sync_known()` first after two seconds, then after each configured
interval. Connection failures are logged; the process stays alive and retries.
Local admission and serving continue while peers are unavailable. A malformed peer
response can abort that sync cycle; the next cycle still runs. Request timeout is
five seconds per outbound request. Large catch-ups or many offline peers can make
a cycle longer than its interval.

For isolated operation set `peers: []`, restrict the published port to localhost
(or omit `ports` entirely for container-network-only access), and restrict inbound
access. An empty peer list prevents outgoing sync but does not disable incoming
`/push` and `/pull` on reachable interfaces.

### Spatial subscriptions

Omitting `subscriptions` means one global subscription. Explicit `subscriptions:
[]` means **accept nothing**, including opaque candidates. It does not purge
records already admitted. Multiple entries form a union. Each entry intersects
its h and z constraints. Bounds are lower-inclusive and upper-exclusive.

Global:

```yaml
subscriptions:
  - {}                         # All authenticated locations and unknown carriers.
```

A bbox-style lexicographic h range:

```yaml
subscriptions:
  - xy_lo: gggh
    xy_hi: gggj
```

These are intervals in the reference's provisional **3D** spatial hash, not
latitude/longitude rectangles in ordinary 2D geohash. A geographic bounding box
may require multiple ranges; no bbox-to-range conversion is supplied here.

Altitude window, optionally intersected with an h range:

```yaml
subscriptions:
  - xy_lo: g
    xy_hi: h
    z_min: "50"
    z_max: "150"
```

Altitude comes from the authenticated 12-character spatial address, never from
an application's `x` payload. Unknown carriers have no authenticated location and
are accepted only by a global subscription. Unknown L4 payloads remain opaque and
are preserved byte-for-byte. Unverified candidates retain the reference's bound
of 128 entries; the valid log is append-only and needs operator capacity planning.

## Operations and persistence

`GET /health` is liveness: HTTP 200 with service/version while the server responds.
`GET /ready` is readiness: 200 only after load/start, with a writable directory and
no durable write failure; otherwise 503 with reasons. A durable write failure is
logged and readiness remains failed until repair/restart. Liveness intentionally
stays 200; Compose's healthcheck is liveness, so monitor `/ready` separately.
`GET /node/info` reports public node/branding fields, software/protocol/build,
subscriptions, configured peers, epoch, counts, metrics and config-loaded state.
The config path is a basename only. These three endpoints are operational, not
new Mesh protocol operations. The existing `/hello`, `/push`, `/pull`, `/sync`
routes retain their semantics.

Volume contents:

* `atoms.jsonl`: append-only wrappers containing address (or null), SHA-256 and
  base64 raw record; each admission flushes and fsyncs before returning success.
* `meta.json`: stable epoch and creation time, atomically written and directory-fsynced.
* `cursors.json`: pull and push checkpoints, atomically replaced/fsynced after
  pull/push, sync cycles and shutdown. Entries are `[key, value]` pairs; tuple keys
  become lists (two components for pull, three for push, as in the reference).

Replay uses the unchanged admission validator with persistence suspended, restores
valid and candidate stores in log order, and preserves bytes exactly. Historical
records are replayed globally even if today's subscription is narrower. Duplicate
and malformed lines are ignored and counted with a warning; malformed cursor files
restart synchronization from null. Torn final lines are separated before appending.
Corruption/duplicates clear saved local cursors. Malformed metadata or an existing
log with missing metadata fails startup instead of silently inventing an epoch.
After corruption, restore a consistent backup: ignored lines can invalidate remote
sequence cursors, even though local cursor files are reset. There is no automatic
compaction, retention, corruption repair or epoch rotation.

SIGTERM/SIGINT request graceful shutdown: finish the in-flight sync, stop HTTP,
persist cursors and close storage. Normal shutdown exits 0. Compose allows 60s;
large syncs or slow clients may require a longer grace period. Logs go to stdout.

### Backup and restore

Stop the container to obtain a consistent snapshot of all three files:

```sh
docker compose -f docker-compose.node.yml stop
tar -czf punkt-node-backup.tgz node-data node-config
docker compose -f docker-compose.node.yml start
```

To restore, stop the service, replace the entire data/config directories from the
same backup and restart. Do not merge logs or mix cursor/meta files from different
snapshots. Retain the same directory ownership or let the root entrypoint initialize
it. Do not run two live copies of one store incarnation. Check readiness, counts
and epoch after restore.

### Upgrade, rollback and image verification

Back up first. Pin a reviewed version or preferably an immutable registry digest:

```sh
export PUNKTO_NODE_IMAGE=ghcr.io/fisker1111/punkto-node@sha256:REPLACE_WITH_REVIEWED_DIGEST
docker compose -f docker-compose.node.yml pull
docker compose -f docker-compose.node.yml up -d
curl -fsS http://localhost:8000/node/info
docker image inspect "$PUNKTO_NODE_IMAGE" --format '{{json .RepoDigests}} {{json .Config.Labels}}'
docker compose -f docker-compose.node.yml exec node sh -c 'grep -E "^Uid|^Gid" /proc/1/status'
```

The UID/GID check should show `10001 10001` for PID 1 (the service process; a bare
`docker compose exec` shell itself still runs as root because the image entrypoint
is what drops privileges). Compare the info build version/revision
and OCI labels with the reviewed release SHA; a tag alone can move. The build image
field is empty unless `PUNKTO_BUILD_IMAGE` is supplied by the operator; the container
cannot discover its own registry digest. Use registry/inspect evidence for digest
verification. Roll back by selecting the previous digest and recreating. Restore
its consistent backup if a future release changes storage compatibility; the draft
protocol and storage are not promised frozen.

The `Node image` workflow tests the original 27-test suite and operational suite,
then builds amd64/arm64. Only `v*` tag pushes and manual dispatch publish. Release
tags produce semver/sha tags and `latest`; prerelease tags (containing `-`) and
manual dispatch do not move `latest`. Manual dispatch produces `preview`/sha.
There is no main-branch push trigger. A manual run may be selected on any branch;
review its exact SHA before use.

## Environment overrides

Precedence: **ENV > YAML > defaults**. Compose intentionally has no environment
block. To override container settings, explicitly pass variables with `docker run
-e` or a separate Compose override. A host shell variable alone is not passed
through Compose, except `PUNKTO_NODE_IMAGE`, which selects the image.

| Variable | Overrides |
| --- | --- |
| PUNKTO_NODE_CONFIG | Config file path, including CLI `--config` |
| PUNKTO_HOST | network.listen_host |
| PUNKTO_PORT | network.listen_port |
| PUNKTO_NODE_NAME | node.name |
| PUNKTO_PEERS | network.peers, comma-separated origins; empty clears peers |
| PUNKTO_DATA_DIR | storage.data_path |
| PUNKTO_SYNC_INTERVAL | network.sync_interval_seconds |
| PUNKTO_LOG_LEVEL | logging.level |
| PUNKTO_BUILD_VERSION | Software/build display version; default 0.6.0-draft.1 or image build version |
| PUNKTO_BUILD_REVISION | Build revision display; image build revision by default |
| PUNKTO_BUILD_IMAGE | Optional operator-provided image/digest display |

## The same image at punkto.xyz

[`node-config.punkto-xyz.example.yml`](../node-config.punkto-xyz.example.yml) is a
public-safe future instantiation. Copy it to `node-config/punkto-node.yml`, arrange
DNS/TLS and a reverse proxy from `https://punkto.xyz` to port 8000, configure compatible
reciprocal peers, and run the same generic image and Compose file. It contains no
secrets and does not assume existing production nodes speak this draft. No domain,
branding, seed list or operator-specific identity is baked into the image.

## Release evidence

The Founder-review record for the first published draft image (image digest, CI
run, two-node proof, restart and isolation evidence) is
[`node-release-evidence.md`](node-release-evidence.md).
