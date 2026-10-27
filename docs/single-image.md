# One image, one node, one origin

The root Dockerfile bundles the Punkto PWA with the conservative Punkti 0.6-draft
store, mesh and API. The PWA is an application of the protocol; the node treats
its signed JSON as opaque content. No application semantics enter the mesh.
The separate `node/Dockerfile` and `docker-compose.node.yml` remain available
for operators who do not need the UI.

## Quick start

```sh
cp punkto-config.example.yml config.yml
mkdir -p data
# Set an image reference published by CI, preferably repository@sha256:…
export PUNKTO_IMAGE='ghcr.io/fisker1111/punkto@sha256:REPLACE_WITH_PUBLISHED_DIGEST'
docker compose -f docker-compose.punkto.yml up -d
```

Open http://localhost:8000. No released tag or digest is asserted here. CI builds
amd64 and arm64 images on version tags or manual dispatch. For a local build:
`docker build -t punkto:local .`, then use `PUNKTO_IMAGE=punkto:local`.
The entrypoint initializes the data volume and drops permanently to uid/gid
10001 before starting the HTTP service. The configured web directory must exist.

## Configuration reference

Environment overrides YAML, which overrides defaults. `config.yml` is mounted
read-only as `/config/punkto-node.yml`. All keys below are operator configuration;
subscriptions specify the protocol's spatial admission policy.

| Key | Default / meaning |
| --- | --- |
| `node.name` | `punkti-node`, public local display name, not identity |
| `node.public_url` | empty; externally reachable HTTP(S) origin |
| `node.description` | empty; public operational description |
| `node.operator_contact` | empty; local, not published |
| `network.listen_host` | `0.0.0.0` |
| `network.listen_port` | `8000`; match Compose port mapping |
| `network.advertise_url` | empty; callback origin, overrides public URL |
| `network.peers` | `[]`; explicit mesh peer origins |
| `network.sync_interval_seconds` | `30` |
| `subscriptions` | `[{}]` accepts all; `[]` accepts nothing |
| `subscriptions[].xy_lo`, `xy_hi` | null; inclusive/exclusive XY prefix bounds |
| `subscriptions[].z_min`, `z_max` | null; inclusive/exclusive canonical decimal Z bounds |
| `storage.data_path` | `/data`, one writer per directory |
| `logging.level` | `info`; debug, info, warning, error |
| `branding.display_name` | `Punkti Node`; public UI/about label |
| `web.enabled` | `true`; node-only examples explicitly use false |
| `web.root` | `/srv/pwa`; absolute existing directory when enabled |
| `web.spa_fallback` | `false`; when true, client routes under `/p/` get the PWA, other unknown paths 404 |

Overrides: `PUNKTO_NODE_CONFIG`, `PUNKTO_HOST`, `PUNKTO_PORT`, `PUNKTO_NODE_NAME`,
`PUNKTO_PEERS` (comma-separated), `PUNKTO_DATA_DIR`, `PUNKTO_SYNC_INTERVAL`,
`PUNKTO_LOG_LEVEL`, `PUNKTO_WEB_ROOT`, `PUNKTO_WEB_ENABLED` (0/false/no/off disable).
Build version and revision come from image build arguments, not operator identity.

## Routes

| Path | Purpose |
| --- | --- |
| `/`, `/index.html`, JS, CSS, assets | Bundled static PWA, GET/HEAD |
| `/p/<id>` | PWA exact link, with SPA fallback enabled |
| `/api/hello`, `/api/pull`, `/api/push`, `/api/sync` | Same protocol operations under deployment alias |
| `/api/health`, `/api/ready`, `/api/node/info` | Operational aliases |
| `/hello`, `/pull`, `/push`, `/sync` | Unchanged native peer routes |
| `/health`, `/ready`, `/node/info` | Native operational routes and healthcheck |

Unknown `/api` paths never serve HTML. Static paths stay confined to the web root.
HTML, JavaScript and JSON use no-store; images/fonts cache for one hour.
The PWA publishes signed L4 JSON inside signed L3 envelopes via `/api/push`, and
reads all cursor pages from `/api/pull`. It verifies envelopes and L4 signatures,
skipping invalid/foreign payloads with a client counter. There are no browser
seed nodes or legacy relay endpoints. Publishing requires an existing identity.
The new `punkto-v06` IndexedDB cache isolates old relay atoms; localStorage
identity/recovery keys remain intact. Existing relay data is not migrated.

## TLS and multiple nodes

The container listens plain HTTP on one port. Terminate TLS at Caddy, Traefik,
or a cloud load balancer and forward the whole origin, including native peer
routes. HTTPS is required for browser crypto/geolocation except on localhost.
Set each instance's public/advertised origin and `network.peers` to the other
instances' origins. Each needs its own data directory. The same image works on
any domain without rebuilds. Peer synchronization belongs to the node, never
to the browser. Map tile providers still require internet access.

## Backup, restore, upgrade and rollback

Stop the container with `docker compose -f docker-compose.punkto.yml stop` before
copying the entire `data/` directory. Preserve `atoms.jsonl`, `meta.json` (store
epoch), and `cursors.json` together, plus your `config.yml`. Restore into an empty
data directory and start with the same pinned image. Do not run two writers
against one directory. Browser identities are separate: export recovery words
or a key backup from Settings.

Before upgrading, save the current image digest and take a stopped backup.
Change `PUNKTO_IMAGE` to the reviewed new digest, then `docker compose -f
docker-compose.punkto.yml pull` and `docker compose -f docker-compose.punkto.yml
up -d`. Check `/health`, `/ready`, `/api/node/info` build revision, and browser
publish/read behavior. To roll back, restore the previous digest; if storage
compatibility changed, restore the matching stopped backup as well. Allow the
configured 60-second graceful shutdown window for persistence.
