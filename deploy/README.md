# Punkto — Docker deployment (single-image)

This directory contains reusable templates for running a Punkto node with Docker.
The current reference architecture runs one combined container per node.

## Deployment model

Punkto separates common software from node-local operation:

- `pwa/` and `punkti_node/` are common public code bundled into one runtime image.
- `deploy/` contains reusable templates and reference helpers; production truth lives on each node.
- `/config/punkto-node.yml` on each server is the node personality.
- `/data` on each server is persistent node memory.
- `.env` and `secrets.env` are local overrides/secrets and must never be committed.

`punkto.xyz` is the reference deployment, not the whole system. Public examples in Git should use safe placeholders such as `example.org`.

See [`docs/punkto-node.md`](../docs/punkto-node.md) and
[`docs/examples/punkto-node.example.yml`](../docs/examples/punkto-node.example.yml)
for the common-code/config/data model and generic config.

## Current architecture (reference truth)

Each node runs one container:

| Service | Image | Purpose |
|---|---|---|
| `app` | `ghcr.io/fisker1111/punkto@sha256:<digest>` | Combined runtime: serves PWA, serves static publication, validates/submits Punkti |

Key properties:

- **Single origin**: PWA, `/submit`, and `/publication/*` are served by the same node origin.
- **Static-first reads**: browser reads publication objects from `/publication` (no dynamic read API required).
- **Persistent volume**: `/data` stores both node state and publication output and survives restarts.
- **Digest-pinned deploys**: deployment must use image digests, never floating `:latest` for production.

## Canonical CI workflow

The only canonical image workflow is:

- `.github/workflows/punkto-image.yml`

It runs protocol/vector tests and browser static-E2E checks before publishing the combined image and records the published image digest in the workflow summary.

## Related deployment docs

Once a node is running, these documents describe how to ship updates safely:

| Document | Purpose |
|---|---|
| [`DEPLOYMENT_RUNBOOK.md`](../DEPLOYMENT_RUNBOOK.md) | Step-by-step deploy procedure for node1 + node2, including rollback |
| [`DEPLOYMENT_SMOKE_TESTS.md`](../DEPLOYMENT_SMOKE_TESTS.md) | Manual + scripted post-deploy checks with pass/fail criteria |
| [`DEPLOYMENT_TROUBLESHOOTING.md`](../DEPLOYMENT_TROUBLESHOOTING.md) | Decision tree for common deployment failures |
| [`verify.sh`](./verify.sh) | Executable smoke-test script for CI/CD and manual post-deploy verification |

**TL;DR:** after every deploy, run `bash deploy/verify.sh <node-host> <expected-hard-marker>`.

## Structure

```
deploy/
  docker-compose.yml     — single-service compose (combined Punkto image)
  .env.example           — legacy env template (historical; prefer digest pin via PUNKTO_IMAGE)
  node1/
    Caddyfile            — node1 reverse-proxy/TLS reference (historical Caddy-side config)
  node2/
    Caddyfile            — node2 reverse-proxy/TLS reference (historical Caddy-side config)
    .env.example         — node2-specific env template
```

## First deploy on a new node

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Create project folder and copy deploy files
mkdir -p ~/punkto
scp deploy/docker-compose.yml user@your-server:~/punkto/
scp deploy/.env.example user@your-server:~/punkto/.env.example

# 3. SSH in and configure digest + node config
ssh user@your-server
cd ~/punkto
cp .env.example .env
cat > .env << 'ENVEOF'
PUNKTO_IMAGE=ghcr.io/fisker1111/punkto@sha256:<reviewed-digest>
ENVEOF

# 4. Provide node config and data dir
mkdir -p data
cp /path/to/your/punkto-node.yml config.yml

# 5. Start
docker compose pull
docker compose up -d --force-recreate

# 6. Verify (from any internet-connected machine)
bash deploy/verify.sh your-domain.example.com "hard-marker-YYYY-MM-DD-N"
```

## Upgrade to a new version

```bash
# 1) Edit .env and set PUNKTO_IMAGE to the new reviewed digest
# 2) Pull + recreate
docker compose pull && docker compose up -d --force-recreate
```

## Rollback (digest-pinned)

```bash
# 1) Edit .env and set PUNKTO_IMAGE to the previous reviewed digest
# 2) Pull + recreate
docker compose pull && docker compose up -d --force-recreate
```

Rollback is always an explicit digest change, not a floating tag.

## Check node health

```bash
curl https://your-domain.example.com/health
curl https://your-domain.example.com/node/info
curl https://your-domain.example.com/publication/root.json
```

## Data persistence

Node state and publication data are persisted in `./data` mounted to `/data`.
The same directory survives container restarts/upgrades.

```bash
# Inspect local persistent data directory
ls -la ./data

# Backup persistent data before major upgrades
tar czf punkto-data-backup.tar.gz data

# Restore
mkdir -p data
tar xzf punkto-data-backup.tar.gz
```

## Useful commands

```bash
# View running services
docker compose ps

# Follow logs
docker compose logs -f app

# Recreate from current pinned digest
docker compose up -d --force-recreate

# Open shell in container
docker compose exec app sh
```

### Cache and CDN policy

See [docs/cache-cloudflare.md](../docs/cache-cloudflare.md) for Cloudflare/CDN policy.
