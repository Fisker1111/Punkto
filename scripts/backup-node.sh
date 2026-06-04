#!/usr/bin/env bash
set -euo pipefail

# backup-node.sh — Backup Punkto node persistent data
# Usage: ./scripts/backup-node.sh [--output ./backups] [--config-dir ./config] [--data-dir ./data] [--include-secrets]

VERSION="0.1"
SCRIPT_NAME="$(basename "$0")"

# Default paths (repo-relative)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${REPO_ROOT}/config"
DATA_DIR="${REPO_ROOT}/data"
OUTPUT_DIR="${REPO_ROOT}/backups"
INCLUDE_SECRETS=false

# Help function
show_help() {
    cat <<EOF
${SCRIPT_NAME} — Backup Punkto node persistent data v${VERSION}

Usage:
  ${SCRIPT_NAME} [OPTIONS]

Backs up the following files:
  - config/punkto-node.yml (node operator config)
  - data/atoms.log.jsonl  (append-only atom log)
  - data/node-key.json    (node identity key)
  - data/known-peers.json (learned peer cache, if present)
  - data/*.json           (other safe data files, if present)

Does NOT include by default:
  - .env / secrets.env (pass --include-secrets to include)
  - TLS certificates
  - Docker volumes

Options:
  --output DIR        Output directory for backup file (default: ./backups)
  --config-dir DIR    Path to config directory (default: ./config)
  --data-dir DIR      Path to data directory (default: ./data)
  --include-secrets   Also include .env and secrets.env (prints a warning)
  --help              Show this help message

Examples:
  ${SCRIPT_NAME}
  ${SCRIPT_NAME} --output ./my-backups
  ${SCRIPT_NAME} --data-dir /var/lib/punkto/data
  ${SCRIPT_NAME} --include-secrets
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            show_help
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --include-secrets)
            INCLUDE_SECRETS=true
            shift
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Run '${SCRIPT_NAME} --help' for usage."
            exit 1
            ;;
    esac
done

# Create output directory if missing
mkdir -p "${OUTPUT_DIR}"

# Build timestamp
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${OUTPUT_DIR}/punkto-node-backup-${TIMESTAMP}.tar.gz"

# Build list of files to include
INCLUDE_PATHS=()

# Config file
if [[ -f "${CONFIG_DIR}/punkto-node.yml" ]]; then
    INCLUDE_PATHS+=("${CONFIG_DIR}/punkto-node.yml")
fi

# Data files
if [[ -f "${DATA_DIR}/atoms.log.jsonl" ]]; then
    INCLUDE_PATHS+=("${DATA_DIR}/atoms.log.jsonl")
fi
if [[ -f "${DATA_DIR}/node-key.json" ]]; then
    INCLUDE_PATHS+=("${DATA_DIR}/node-key.json")
fi
if [[ -f "${DATA_DIR}/known-peers.json" ]]; then
    INCLUDE_PATHS+=("${DATA_DIR}/known-peers.json")
fi

# Other JSON data files (safe node state)
for f in "${DATA_DIR}"/*.json; do
    bn="$(basename "$f")"
    case "$bn" in
        atoms.log.jsonl|node-key.json|known-peers.json)
            # Already included above
            ;;
        *)
            if [[ -f "$f" ]]; then
                INCLUDE_PATHS+=("$f")
            fi
            ;;
    esac
done

# Include secrets if requested
if [[ "$INCLUDE_SECRETS" == "true" ]]; then
    echo "WARNING: Including .env and secrets.env in backup."
    echo "         This backup file contains sensitive credentials."
    echo "         Store it securely and do not commit to Git."
    if [[ -f "${CONFIG_DIR}/.env" ]]; then
        INCLUDE_PATHS+=("${CONFIG_DIR}/.env")
    fi
    if [[ -f "${CONFIG_DIR}/secrets.env" ]]; then
        INCLUDE_PATHS+=("${CONFIG_DIR}/secrets.env")
    fi
fi

# Check if there's anything to backup
if [[ ${#INCLUDE_PATHS[@]} -eq 0 ]]; then
    echo "ERROR: No files found to backup at:"
    echo "  Config dir: ${CONFIG_DIR}"
    echo "  Data dir:   ${DATA_DIR}"
    echo "Run '${SCRIPT_NAME} --help' for usage."
    exit 1
fi

# Create tar archive (change to repo root so paths are relative)
cd "${REPO_ROOT}"

# Build relative paths for tar
TAR_PATHS=()
for p in "${INCLUDE_PATHS[@]}"; do
    rel="$(realpath --relative-to="${REPO_ROOT}" "$p" 2>/dev/null || echo "$p")"
    TAR_PATHS+=("$rel")
done

tar czf "${BACKUP_FILE}" "${TAR_PATHS[@]}"

# Summary
echo "Backup created: ${BACKUP_FILE}"
echo ""
echo "Files included (${#INCLUDE_PATHS[@]}):"
for p in "${TAR_PATHS[@]}"; do
    echo "  - $p"
done
if [[ "$INCLUDE_SECRETS" != "true" ]]; then
    echo ""
    echo "NOTE: .env and secrets.env are NOT included."
    echo "      Run with --include-secrets to include them (not recommended for shared storage)."
fi
