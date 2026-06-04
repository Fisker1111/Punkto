# Backup and Restore

> **Status:** Documentation + operator scripts.
> Covers backing up and restoring a Punkto node's persistent data.

This document explains how to create and restore backups of Punkto node persistent data. Backups are **operator-side** operations from persistent Docker storage to an external backup file. This is not a public API feature.

## What Is Backed Up

| File | Purpose | Required |
|------|---------|----------|
| `config/punkto-node.yml` | Node operator config (identity, peers, policy) | ✅ Always included |
| `data/atoms.log.jsonl` | Append-only atom log (durable truth) | ✅ Always included |
| `data/node-key.json` | Node identity key (private/public key pair) | ✅ Always included |
| `data/known-peers.json` | Learned peer cache (if present) | ✅ Included if exists |
| `data/*.json` | Other safe node state files | ✅ Included if exists |

## What Is NOT Backed Up

| File | Reason |
|------|--------|
| `.env` | Environment secrets — excluded by default. Pass `--include-secrets` to include (with warning) |
| `secrets.env` | Environment secrets — excluded by default. Pass `--include-secrets` to include (with warning) |
| TLS certificates | Deployment-specific, not node persistent state |
| Docker volumes | Handled separately (see deploy docs) |
| `node_modules/` | Build artifacts, not persistent state |

## Backup Command

```bash
# Default backup (excludes .env/secrets)
./scripts/backup-node.sh

# Output to specific directory
./scripts/backup-node.sh --output ./my-backups

# Custom data/config paths
./scripts/backup-node.sh --data-dir /var/lib/punkto/data --config-dir /etc/punkto

# Include .env and secrets.env (prints a warning)
./scripts/backup-node.sh --include-secrets
```

Backup output is a timestamped tar.gz file:

```
./backups/punkto-node-backup-20260602T120000Z.tar.gz
```

### Backup Safety

- Does **not** require Docker to be running — operates on files directly
- Does **not** include `.env` or `secrets.env` by default (requires explicit `--include-secrets` flag)
- Does **not** modify any files — creates a read-only archive
- Stores **one optional copy** of `.env`/`secrets.env` only when explicitly requested

## Restore Command

```bash
# Restore from backup (refuses to overwrite existing files by default)
./scripts/restore-node.sh ./backups/punkto-node-backup-20260602T120000Z.tar.gz

# Force overwrite of existing files
./scripts/restore-node.sh ./backup.tar.gz --force

# Custom paths
./scripts/restore-node.sh ./backup.tar.gz --data-dir /var/lib/punkto/data
```

### Restore Safety

- **Refuses to overwrite** existing `config/` or `data/` files unless `--force` is passed
- **Validates archive structure** before extracting — checks for path traversal attacks
- **Creates missing directories** (`config/`, `data/`) automatically
- **Sets safe permissions** (600 for files, 700 for directories)
- **Does NOT require Docker** to be running — operates on files directly

## Fresh Server Restore Flow

Complete flow for restoring a Punkto node onto a fresh server:

```bash
# 1. Clone the Punkto repository
git clone https://github.com/Fisker1111/Punkto
cd Punkto

# 2. Set up environment (copy .env.example and configure)
cp deploy/.env.example .env
# Edit .env with your production values

# 3. Pull latest Docker images
docker compose pull

# 4. Bring down any existing containers
docker compose down

# 5. Restore backup into config/data persistent storage
./scripts/restore-node.sh /path/to/punkto-node-backup-20260602T120000Z.tar.gz --force

# 6. Start Docker services
docker compose up -d

# 7. Wait for services to stabilize
sleep 15

# 8. Run node doctor to verify
./scripts/node-doctor.py https://node.example.org --local
```

After restore:

| Item | Expected |
|------|----------|
| Node identity (fingerprint) | ✅ Preserved (from `node-key.json`) |
| Atom log | ✅ Preserved (from `atoms.log.jsonl`) |
| Known peers | ✅ Preserved (from `known-peers.json`) |
| Node config | ✅ Preserved (from `punkto-node.yml`) |
| `/health` | ✅ Returns `status: ok` |
| `/feed` | ✅ Returns atoms from restored log |
| `/status` | ✅ Shows correct node identity |
| `/node/info` | ✅ Shows restored config_loaded=true |

## Node Identity Preservation

The backup includes `data/node-key.json`. This file contains the node's key pair:

- The **public key** determines the node's `fingerprint` / `node_id`
- The **private key** is used for signing node announcements and peer verification

If this file is lost, the node will generate a new key pair on restart, resulting in a **new node identity** (new fingerprint). All previous peer trust relationships tied to the old fingerprint will break.

**Therefore:**

- Treat `node-key.json` as critical state — always include it in backups
- Consider having a secondary copy of `node-key.json` stored securely offline
- After restore, verify the node fingerprint matches the expected identity

## Post-Restore Verification

Always run Node Doctor after restore:

```bash
# Local checks
./scripts/node-doctor.py https://node.example.org --local

# Full remote check
./scripts/node-doctor.py https://node.example.org --expect-ip <SERVER_IP> --expect-name "Node Name"
```

Expected:

| Check | Expected |
|-------|----------|
| `config_loaded` | `true` |
| `node_name` | Matches pre-backup configuration |
| `fingerprint` | Matches pre-backup node identity |
| `storage.log_loaded` | `true` |
| `storage.log_lines` | Matches pre-backup count (or higher if atoms were added during backup) |
| Feed serves atoms | Atoms from restored log are served |

## Script Reference

### `scripts/backup-node.sh`

```
Usage: ./scripts/backup-node.sh [OPTIONS]

Options:
  --output DIR        Output directory for backup file (default: ./backups)
  --config-dir DIR    Path to config directory (default: ./config)
  --data-dir DIR      Path to data directory (default: ./data)
  --include-secrets   Also include .env and secrets.env (prints warning)
  --help              Show this help message
```

### `scripts/restore-node.sh`

```
Usage: ./scripts/restore-node.sh <backup-file> [OPTIONS]

Options:
  --force             Overwrite existing config and data files
  --config-dir DIR    Path to config directory (default: ./config)
  --data-dir DIR      Path to data directory (default: ./data)
  --help              Show this help message
```

## Security Notes

- Backups may contain `node-key.json` which includes the node's **private key** — store backups securely
- If using `--include-secrets`, the backup will contain `.env` or `secrets.env` with sensitive credentials
- The backup file is not encrypted by default — use your own encryption for offsite storage:
  ```bash
  gpg --symmetric --cipher-algo AES256 ./backups/punkto-node-backup-*.tar.gz
  ```
- Do not commit backup files to Git (they are in `.gitignore` by convention)
- Do not expose backup files through any public endpoint
- After restore on a new server, rotate any credentials that may have been compromised
