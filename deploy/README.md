# Punkto — Docker Deployment

This directory contains reusable templates for running a Punkto node with Docker.
Each node runs two containers managed by Docker Compose.


## Deployment model

Punkto separates common software from node-local operation:

- `pwa/` and `relay/` are common public code.
- `deploy/` contains reusable templates and reference helpers; these files are
  not live production truth.
- `/config/punkto-node.yml` on each server is the node's personality.
- `/data` on each server is the node's persistent memory.
- `.env` and `secrets.env` are local overrides/secrets and must never be
  committed.

`punkto.xyz` is the reference deployment, not the whole system. The production
configuration for `punkto.xyz` is maintained on the nodes by the operator. Public
examples in Git should use documentation-safe placeholders such as
`example.org`. Prefer `node1` and `node2` for new reference node names; `app1`
and `app2` may appear as legacy/reference aliases in existing deploy history.

See [`docs/punkto-node.md`](../docs/punkto-node.md) and
[`docs/examples/punkto-node.example.yml`](../docs/examples/punkto-node.example.yml)
for the common-code/config/data model and generic example config.

## Related deployment docs

Once a node is running, these documents describe how to ship updates safely:

| Document | Purpose |
|---|---|
| [`DEPLOYMENT_RUNBOOK.md`](../DEPLOYMENT_RUNBOOK.md) | Step-by-step deploy procedure for server1 + app2, including rollback |
| [`DEPLOYMENT_SMOKE_TESTS.md`](../DEPLOYMENT_SMOKE_TESTS.md) | Manual + scripted post-deploy checks with pass/fail criteria |
| [`DEPLOYMENT_TROUBLESHOOTING.md`](../DEPLOYMENT_TROUBLESHOOTING.md) | Decision tree for common deployment failures |
| [`verify.sh`](./verify.sh) | Executable smoke-test script for CI/CD and manual post-deploy verification |

**TL;DR:** after every deploy, run `bash deploy/verify.sh <node-host> <expected-hard-marker>`.

## Structure

```
deploy/
  docker-compose.yml     — service definitions (web + relay)
  .env.example           — shared environment variable template
  server1/
    Caddyfile            — self-contained Caddy config for node1/server1 (punkto.xyz, node1, app1, www)
  app2/
    Caddyfile            — self-contained Caddy config for node2/app2 (node2, app2)
    .env.example         — app2-specific env template
```

## How it works

Each node runs two containers:

| Container | Image | Purpose |
|---|---|---|
| `web` | `ghcr.io/fisker1111/punkto-web` | Caddy — serves static PWA files + proxies relay API |
| `relay` | `ghcr.io/fisker1111/punkto-relay` | Python relay — atom store, peer sync |

- **Caddy** handles TLS certificates automatically via Let's Encrypt — no certbot or cron needed.
- **Relay data** persists in a named Docker volume (`punkto_relay_data`) across upgrades.
- **Configuration** is supplied via a `.env` file and a `Caddyfile` on the server (not baked into the image).

## Live nodes

| Node | Domains | Location |
|---|---|---|
| node1 | `punkto.xyz`, `www.punkto.xyz`, `node1.punkto.xyz`, `app1.punkto.xyz` | Reference primary node |
| node2 | `node2.punkto.xyz`, `app2.punkto.xyz` | Reference secondary node |

`server1`, `app1`, and `app2` are legacy/reference aliases that may remain in
existing files or DNS history. Prefer `node1`/`node2` in new docs and examples.


## Caddy template independence

Each node Caddyfile is self-contained and must validate independently. Do not
make one node deploy template depend on snippets or matchers defined only in
another node's Caddyfile. Keep the node1/node2 canonical hostnames and the
app1/app2 legacy aliases wired in their respective node templates.

## First deploy on a new node

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Create project folder and copy deploy files
mkdir -p ~/punkto
scp deploy/docker-compose.yml user@your-server:~/punkto/
scp deploy/server1/Caddyfile user@your-server:~/punkto/Caddyfile  # or app2/Caddyfile

# 3. SSH in and create .env
ssh user@your-server
cd ~/punkto
cat > .env << EOF
PUNKTO_VERSION=latest
PUNKTO_NODE_NAME=your-node-name
PUNKTO_PEERS=https://other-node.example.com
EOF

# 4. Start
docker compose up -d

# 5. Verify (from any internet-connected machine)
bash deploy/verify.sh your-domain.example.com "v0.46-hard-marker-YYYY-MM-DD-1"
# See ../DEPLOYMENT_SMOKE_TESTS.md for full pass/fail criteria
```

## Upgrade to a new version

```bash
# Pull latest images and restart
docker compose pull && docker compose up -d

# Or pin to a specific version — edit .env: PUNKTO_VERSION=v0.46
docker compose up -d
```

## Rollback

```bash
# Edit .env: PUNKTO_VERSION=v0.44
docker compose up -d
```

## Check node health

```bash
curl https://your-domain.example.com/health
curl https://your-domain.example.com/info
```

## Data persistence

Atoms are stored in the `punkto_relay_data` Docker volume and survive container upgrades.

```bash
# List volumes
docker volume ls | grep punkto

# Backup atoms before a major upgrade
docker run --rm -v punkto_relay_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/atoms-backup.tar.gz /data

# Restore
docker run --rm -v punkto_relay_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/atoms-backup.tar.gz -C /
```

## Configuration reference

Runtime environment overrides live in `.env` on the server. The broader node
configuration model is `/config/punkto-node.yml`; see the generic example in
`docs/examples/punkto-node.example.yml`.

| Variable | Default | Description |
|---|---|---|
| `PUNKTO_VERSION` | `latest` | Docker image tag to run |
| `PUNKTO_NODE_NAME` | `punkto-node` | Human-readable node name |
| `PUNKTO_PEERS` | _(empty)_ | Comma-separated peer relay URLs |
| `PUNKTO_BUFFER_ATOMS` | `10000` | Max atoms in rolling buffer |
| `PUNKTO_BUFFER_HOURS` | `168` | Max atom age in hours (7 days) |
| `PUNKTO_SYNC_INTERVAL` | `30` | Peer sync interval in seconds |

## Building images locally

```bash
# Build web image (Caddy + static PWA)
docker build -t punkto-web ./pwa

# Build relay image (Python)
docker build -t punkto-relay ./relay

# Test locally
docker compose -f deploy/docker-compose.yml up
```

## GitHub Actions — automated builds

Images are built and pushed automatically by `.github/workflows/docker.yml`:

- **Push to `main`** → builds and pushes `:latest`
- **Push tag `v0.46`** → builds and pushes `:v0.46` and `:latest`

Images are published to:
- `ghcr.io/fisker1111/punkto-web`
- `ghcr.io/fisker1111/punkto-relay`

No secrets need to be configured — the workflow uses `GITHUB_TOKEN` automatically.

## Useful commands

```bash
# View running containers
docker compose ps

# Follow logs
docker compose logs -f

# Relay logs only
docker compose logs -f relay

# Restart relay without downtime
docker compose restart relay

# Open relay shell (debug)
docker compose exec relay sh
```
