# Punkto — Docker Deployment

This directory contains everything needed to run a Punkto node with Docker.

## Structure

```
deploy/
  docker-compose.yml   — service definitions (web + relay)
  .env.example         — environment variable template
  node1/
    Caddyfile          — Caddy config for node1
    .env.example       — node1-specific env template
  node2/
    Caddyfile          — Caddy config for node2
    .env.example       — node2-specific env template
```

## How it works

Each node runs two containers:

| Container | Image | Purpose |
|---|---|---|
| `web` | `ghcr.io/fisker1111/punkto-web` | Caddy — serves static PWA + proxies relay API |
| `relay` | `ghcr.io/fisker1111/punkto-relay` | Python relay — atom store + peer sync |

Caddy handles Let's Encrypt TLS automatically. No certbot or cron needed.

## First deploy on a new node

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Copy deploy files to the server
scp -r deploy/ user@your-server:~/punkto/
scp deploy/node1/Caddyfile user@your-server:~/punkto/Caddyfile

# 3. SSH into the server
ssh user@your-server
cd ~/punkto

# 4. Create .env from example
cp .env.example .env
nano .env   # set PUNKTO_VERSION, PUNKTO_NODE_NAME, PUNKTO_PEERS

# 5. Start
docker compose up -d

# 6. Check logs
docker compose logs -f
```

## Upgrade to a new version

```bash
# Pull latest and restart
docker compose pull && docker compose up -d

# Or pin to a specific version
PUNKTO_VERSION=v0.46 docker compose pull && docker compose up -d

# Or edit .env: PUNKTO_VERSION=v0.46
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

Atoms are stored in a named Docker volume (`relay_data`) and survive container upgrades and restarts. **Never delete this volume** on a production node.

```bash
# List volumes
docker volume ls | grep punkto

# Backup atoms before a major upgrade
docker run --rm -v punkto_relay_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/atoms-backup.tar.gz /data
```

## Node configuration

Each node reads its config from a `.env` file in the same directory as `docker-compose.yml`:

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
# Build web image
docker build -t punkto-web ./pwa

# Build relay image
docker build -t punkto-relay ./relay

# Test locally with docker compose (uses local builds)
docker compose -f deploy/docker-compose.yml up
```

## GitHub Actions

Images are built and pushed automatically by `.github/workflows/docker.yml`:

- Push to `main` → builds `:latest`
- Push tag `v0.46` → builds `:v0.46` and `:latest`

No secrets need to be configured — the workflow uses `GITHUB_TOKEN` automatically.

## Removing old bare-metal setup

Once Docker is running and verified, the old setup can be removed:

```bash
# Stop and disable old services
systemctl stop punkto-relay
systemctl disable punkto-relay

# Remove old nginx site config
rm /etc/nginx/sites-enabled/punkto
nginx -t && systemctl reload nginx

# (Optional) Uninstall nginx if no longer needed
apt remove nginx
```
