#!/usr/bin/env bash
set -euo pipefail

# restore-node.sh — Restore Punkto node persistent data from backup
# Usage: ./scripts/restore-node.sh <backup-file.tar.gz> [--force] [--config-dir ./config] [--data-dir ./data]

VERSION="0.1"
SCRIPT_NAME="$(basename "$0")"

# Default paths (repo-relative)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${REPO_ROOT}/config"
DATA_DIR="${REPO_ROOT}/data"
FORCE=false

# Help function
show_help() {
    cat <<EOF
${SCRIPT_NAME} — Restore Punkto node persistent data v${VERSION}

Usage:
  ${SCRIPT_NAME} <backup-file> [OPTIONS]

Restores the following files from a backup tar.gz:
  - config/punkto-node.yml (node operator config)
  - data/atoms.log.jsonl  (append-only atom log)
  - data/node-key.json    (node identity key)
  - data/known-peers.json (learned peer cache, if present)
  - data/*.json           (other safe data files, if present)

By default, refuses to overwrite existing files unless --force is passed.

Options:
  --force             Overwrite existing config and data files
  --config-dir DIR    Path to config directory (default: ./config)
  --data-dir DIR      Path to data directory (default: ./data)
  --help              Show this help message

Examples:
  ./scripts/restore-node.sh ./backups/punkto-node-backup-20260602T120000Z.tar.gz
  ./scripts/restore-node.sh ./backup.tar.gz --force
  ./scripts/restore-node.sh ./backup.tar.gz --data-dir /var/lib/punkto/data

After restore:
  docker compose up -d
  ./scripts/node-doctor.py https://node.example.org --local
EOF
    exit 0
}

# Parse arguments
BACKUP_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            show_help
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        -*)
            echo "ERROR: Unknown option: $1"
            echo "Run '${SCRIPT_NAME} --help' for usage."
            exit 1
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                echo "ERROR: Unexpected argument: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate backup file
if [[ -z "${BACKUP_FILE}" ]]; then
    echo "ERROR: No backup file specified."
    echo "Run '${SCRIPT_NAME} --help' for usage."
    exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

if [[ "${BACKUP_FILE}" != *.tar.gz ]]; then
    echo "ERROR: Backup file must be a .tar.gz archive."
    exit 1
fi

# Validate backup structure before extracting
echo "Validating backup archive: ${BACKUP_FILE}"
TMP_CHECK="$(mktemp -d)"
if ! tar tzf "${BACKUP_FILE}" > "${TMP_CHECK}/contents.txt" 2>/dev/null; then
    echo "ERROR: Could not read archive (corrupt or not a tar.gz file)."
    rm -rf "${TMP_CHECK}"
    exit 1
fi

# Anti-path-traversal check: ensure no absolute paths or ../ patterns
while IFS= read -r entry; do
    if echo "$entry" | grep -qE '^/' || echo "$entry" | grep -qE '\.\.' || echo "$entry" | grep -qE '~'; then
        echo "ERROR: Archive contains dangerous path: ${entry}"
        echo "       Refusing to extract due to path traversal risk."
        rm -rf "${TMP_CHECK}"
        exit 1
    fi
done < "${TMP_CHECK}/contents.txt"
echo "  Archive structure valid. No path traversal detected."
echo ""
echo "Contents:"
cat "${TMP_CHECK}/contents.txt"
rm -rf "${TMP_CHECK}"

# Check for conflicts
EXISTING_CONFLICTS=()
while IFS= read -r entry; do
    # Only check config/ and data/ files
    if echo "$entry" | grep -qE '^(config/|data/)'; then
        target="${REPO_ROOT}/${entry}"
        if [[ -f "$target" ]] || [[ -d "$target" ]]; then
            EXISTING_CONFLICTS+=("$entry")
        fi
    fi
done < <(tar tzf "${BACKUP_FILE}")

if [[ ${#EXISTING_CONFLICTS[@]} -gt 0 ]]; then
    echo ""
    echo "WARNING: The following files already exist:"
    for f in "${EXISTING_CONFLICTS[@]}"; do
        echo "  - ${REPO_ROOT}/$f"
    done
    if [[ "$FORCE" != "true" ]]; then
        echo ""
        echo "Use --force to overwrite existing files."
        echo "Aborting restore."
        exit 1
    fi
    echo ""
    echo "--force is set. Will overwrite existing files."
fi

# Create target directories if missing
mkdir -p "${CONFIG_DIR}" "${DATA_DIR}"

# Extract the backup (relative paths from tar are relative to repo root)
cd "${REPO_ROOT}"
echo ""
echo "Extracting backup to: ${REPO_ROOT}"
tar xzf "${BACKUP_FILE}"

# Set safe permissions
while IFS= read -r entry; do
    target="${REPO_ROOT}/${entry}"
    if [[ -f "$target" ]]; then
        chmod 600 "$target" 2>/dev/null || true
    fi
    if [[ -d "$target" ]]; then
        chmod 700 "$target" 2>/dev/null || true
    fi
done < <(tar tzf "${BACKUP_FILE}")

echo ""
echo "Restore complete."
echo ""
echo "Next steps:"
echo "  1. docker compose up -d"
echo "  2. ./scripts/node-doctor.py https://node.example.org --local"
echo ""
echo "IMPORTANT: If this backup contains a node-key.json, your node identity"
echo "           (fingerprint/node_id) will be preserved. This is by design."
echo "           Verify node identity after restart."
