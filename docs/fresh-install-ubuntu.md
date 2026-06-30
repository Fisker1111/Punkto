# Fresh Ubuntu Install Guide

> Deploy a Punkto node on a fresh Ubuntu 24.04 LTS server.
>
> Ubuntu 22.04 LTS should also work, but this guide targets 24.04.

## Overview

This guide walks from a fresh Ubuntu server to a running, verified Punkto node.

Two paths are documented:

| Path | DNS required? | HTTPS required? | Best for |
|------|---------------|-----------------|----------|
| **DNS/HTTPS** (recommended) | Yes | Yes | Public web node with browser/PWA access |
| **IP:port** (minimal) | No | No | Punkti-only node sync; browser access limited |

See [docs/ip-first-bootstrap.md](ip-first-bootstrap.md) for the philosophical model:
> DNS and HTTPS are convenience layers, not protocol requirements.

---

## 1. Requirements

| Requirement | Detail |
|------------|--------|
| Server | Ubuntu 24.04 LTS (22.04 likely works) |
| Public IP | Static or stable public address |
| Ports open | **80** and **443** for DNS/HTTPS path |
| Domain name | Recommended for web/PWA; not required for Punkti node sync |
| Software | `docker`, `docker compose`, `git` |

---

## 2. Install Packages

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git ufw
```

### Optional: Configure firewall

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
```

---

## 3. Install Docker

### Option A: Official Docker install (recommended)

```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository
sudo sh -c 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list'

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify
sudo docker run hello-world
```

### Option B: Install via apt (simpler, older version)

```bash
sudo apt install -y docker.io docker-compose-v2
```

### Add your user to the docker group (avoids `sudo`)

```bash
sudo usermod -aG docker $USER
# Log out and back in, or run:
newgrp docker
```

---

## 4. Clone the Repository

```bash
git clone https://github.com/Fisker1111/Punkto.git
cd Punkto
```

---

## 5. Create Persistent Folders

```bash
mkdir -p config data backups
```

---

## 6. Create Node Configuration

```bash
cp docs/examples/punkto-node.example.yml config/punkto-node.yml
```

### Minimum edits needed

Open `config/punkto-node.yml` and update these fields:

| Field | Description |
|-------|-------------|
| `operator.node_name` | A human-readable name for your node (e.g. `"My Punkto Node"`) |
| `network.public_url` | Your node's public URL (e.g. `"https://node.example.org"`) or IP:port |
| `network.seed_nodes` | List of initial peer nodes (see [ip-first-bootstrap.md](ip-first-bootstrap.md)) |
| `serving.serve_recent_hours` | How many hours of recent atoms to serve (default: `24`) |
| `serving.serve_archive` | Whether to serve archive atoms (`false` recommended for now) |
| `acceptance.accept_recent_hours` | How old an atom can be to be accepted (default: `24`) |

---

## 7. Environment File

If `deploy/.env.example` exists, copy it:

```bash
cp deploy/.env.example .env
```

> **Note:** The `.env` file is not committed to Git. It may contain secrets or
> deployment-specific overrides. Do not share it.

---

## 8. DNS / HTTPS Path (recommended for public web)

### 8a. Configure DNS

Create an **A record** pointing your domain to the server's public IP:

| Type | Name | Value |
|------|------|-------|
| A | `node` | `<YOUR_SERVER_IP>` |
| A | `www` | `<YOUR_SERVER_IP>` (optional) |

Replace `node.example.org` with your domain throughout.

### 8b. Configure Caddy (automatic TLS)

Copy the appropriate Caddyfile for your deployment model:

```bash
# For a single-node setup, adapt from deploy/node1/
cp deploy/node1/Caddyfile ./Caddyfile
```

The Caddyfile should reference your domain name. Caddy will automatically
obtain and renew Let's Encrypt TLS certificates on first startup.

### 8c. Start the node

```bash
docker compose pull
docker compose up -d
```

---

## 9. IP:port Path (minimal, DNS-free)

For a Punkti-only node that does not need browser/PWA access:

1. Set `network.public_url` in `config/punkto-node.yml`:
   ```yaml
   network:
     public_url: "http://<YOUR_SERVER_IP>:8000"
   ```

2. Ensure port **8000** (or your chosen port) is open in your firewall.

3. Start the node:
   ```bash
   docker compose pull
   docker compose up -d
   ```

> **Limitations:** Current browser/PWA may prefer HTTPS due to browser security
> (secure context requirements). For full PWA functionality, the DNS/HTTPS path
> is recommended. Punkti node-to-node sync is designed to support IP:port in
> the future, but current clients may expect HTTPS.

---

## 10. Start the Node

```bash
docker compose pull
docker compose up -d
```

Wait a few seconds for services to start:

```bash
sleep 10
```

---

## 11. Verify the Node is Running

### Docker containers

```bash
docker compose ps
```

Expected output (both containers should show `Up`):

```
NAME                IMAGE                                STATUS   PORTS
punkto-web-1        ghcr.io/fisker1111/punkto-web:latest   Up      80→80
punkto-relay-1      ghcr.io/fisker1111/punkto-relay:latest Up      8000→8000
```

### Run Node Doctor

```bash
python3 scripts/node-doctor.py https://node.example.org --expect-name "My Punkto Node"
```

### Manual curl checks

```bash
curl https://node.example.org/health
curl https://node.example.org/node/info
curl https://node.example.org/status
```

Expected:

- `/health` returns `{"status": "ok", ...}`
- `/node/info` returns JSON with `config_loaded: true` and your node name
- `/status` returns HTML with "Punkto Node Status"

---

## 12. First Atom Test

> **Signature policy:** The relay defaults to `PUNKTO_REQUIRE_SIG=false`, which allows unsigned atoms for local development and initial setup. If you have enabled `require_sig: true` in your node config, see the signed-atom example below.

Post a test atom with a recent timestamp:

```bash
TS=$(date +%s%3N)  # Unix milliseconds
curl -X POST https://node.example.org/atom \
  -H "Content-Type: application/json" \
  -d '{
    "punkto": "p:test00000000",
    "content": "Hello from my new Punkto node!",
    "t": '$TS'
  }'
```

Expected response: `HTTP 201` with atom ID, for example:

```json
{"ok": true, "atom_id": "a1b2c3d4e5f6..."}
```

If you receive `HTTP 400` with `"error": "invalid_timestamp"`, check that `t` is in **milliseconds** (13 digits), not seconds.

If you receive `HTTP 403` with `"error": "missing_sig"`, your relay has `PUNKTO_REQUIRE_SIG=true`. Either set `PUNKTO_REQUIRE_SIG=false` in your relay environment, or use a signed atom (see `tools/punkto-key.py` for key generation).

Verify it appears in the feed:

```bash
curl https://node.example.org/feed
```

Expected: JSON array containing the atom you just posted.

---

## 13. Backup

Regular backups are important. See [docs/backup-restore.md](backup-restore.md) for full details.

```bash
./scripts/backup-node.sh --output ./backups
```

This creates a timestamped archive in `./backups/` containing:

- `config/punkto-node.yml` — your node configuration
- `data/atoms.log.jsonl` — the append-only atom log
- `data/node-key.json` — node identity key (keep secure!)
- `data/known-peers.json` — learned peer cache (if present)

---

## 14. Upgrade

To upgrade to the latest version:

```bash
# 1. Pull latest code
git pull

# 2. Pull latest Docker images
docker compose pull

# 3. Stop current containers
docker compose down --remove-orphans

# 4. Start fresh containers
docker compose up -d --pull always --force-recreate

# 5. Verify
python3 scripts/node-doctor.py https://node.example.org --expect-name "My Punkto Node"
```

---

## 15. Troubleshooting

| Symptom | Likely cause | Check |
|---------|-------------|-------|
| **DNS not resolving** | Missing or incorrect A record | `dig node.example.org` |
| **Ports blocked** | Firewall / cloud security group | `curl -v http://YOUR_IP:8000/health` |
| **Caddy/TLS error** | Domain not pointed to this IP yet | `curl -v http://YOUR_IP/health` (should work without HTTPS) |
| **`config_loaded: false`** | Config file missing or invalid | `ls -la config/punkto-node.yml` ; check YAML syntax |
| **`/feed` empty** | No atoms accepted yet | Post a test atom (see section 12) |
| **Old atom rejected** (`atom_too_old`) | Atom timestamp outside `accept_recent_hours` | Use a recent timestamp |
| **Wrong node name** | Config not loaded or wrong field name | Check `operator.node_name` in config, then `docker compose restart` |
| **Docker container not running** | Image pull failed / port conflict | `docker compose logs` |
| **Error: port already allocated** | Another service uses port 80/443/8000 | Check with `sudo ss -tlnp` |

---

## 16. Security Notes

1.  **Punkto is public.** Atoms are public and may be retained by other
    nodes. Do not post passwords, secrets, sensitive personal information,
    or anything you may need permanently deleted. Signing proves authorship
    and integrity; it does not encrypt the atom.

2.  **Do not commit secrets.** `config/`, `data/`, and `.env` are in
    `.gitignore` and must never be committed.

3.  **Backups contain node identity.** The file `data/node-key.json` is your
    node's identity key. Losing it changes your node's `node_id`/`fingerprint`.
    Store backups securely.

4.  **Admin remains SSH/operator-side.** There is no web admin panel.
    All management is done via SSH and command-line tools.

5.  **Keep Docker and Ubuntu updated.**

    ```bash
    sudo apt update && sudo apt upgrade -y
    ```

---

## Restore from Backup (Fresh Server)

If setting up a replacement server from a backup:

```bash
# 1. Fresh Ubuntu + Docker + git (sections 2-3)
# 2. Clone repo
git clone https://github.com/Fisker1111/Punkto.git
cd Punkto

# 3. Pull Docker images
docker compose pull

# 4. Stop any running containers
docker compose down

# 5. Restore backup
./scripts/restore-node.sh /path/to/punkto-node-backup-20260602T120000Z.tar.gz

# 6. Start containers
docker compose up -d

# 7. Verify
python3 scripts/node-doctor.py https://node.example.org --local --expect-name "My Punkto Node"
```

---

## References

| Document | Description |
|----------|-------------|
| [docs/punkto-node.md](punkto-node.md) | Full node configuration reference |
| [docs/ip-first-bootstrap.md](ip-first-bootstrap.md) | IP-first bootstrap model |
| [docs/backup-restore.md](backup-restore.md) | Backup and restore details |
| [docs/public-api.md](public-api.md) | Public API endpoint reference |
| [docs/cache-cloudflare.md](cache-cloudflare.md) | Cache and CDN policy |
| [deploy/README.md](../deploy/README.md) | Deployment infrastructure guide |
| [scripts/node-doctor.py](../scripts/node-doctor.py) | Node health verification script |
