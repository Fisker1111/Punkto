#!/bin/bash
set -euo pipefail

# Config
SRC_DIR="/a0/usr/projects/punkto/pwa"
DEST_DIR="/var/www/punkto"
USER="root"
PASS="3AtIAvCwwI@dok<Bc^Cd"
DOMAINS=("punkto.xyz" "app1.punkto.xyz" "app2.punkto.xyz")

# Check local files exist
echo "=== Checking local PWA files ==="
for f in index.html app.js sw.js nacl.min.js key-management.js manifest.json geohash3d.js; do
  if [[ ! -f "$SRC_DIR/$f" ]]; then
    echo "ERROR: Missing $SRC_DIR/$f"
    exit 1
  fi
done

# Get local SW version
LOCAL_SW_VERSION=$(grep -oP "CACHE_NAME = '\Kpunkto-v\d+" "$SRC_DIR/sw.js")
echo "Local SW version: $LOCAL_SW_VERSION"

# Deploy to each domain
for DOMAIN in "${DOMAINS[@]}"; do
  echo "\n=== Deploying to $DOMAIN ==="
  # Copy files via scp
  sshpass -p "$PASS" scp "$SRC_DIR"/* "$USER@$DOMAIN:$DEST_DIR/"
  # Reload nginx
  sshpass -p "$PASS" ssh "$USER@$DOMAIN" "nginx -t && systemctl reload nginx"
  # Verify SW version matches
  REMOTE_SW_VERSION=$(curl -s "https://$DOMAIN/sw.js" | grep -oP "CACHE_NAME = '\Kpunkto-v\d+")
  if [[ "$REMOTE_SW_VERSION" != "$LOCAL_SW_VERSION" ]]; then
    echo "ERROR: $DOMAIN SW version mismatch! Local: $LOCAL_SW_VERSION, Remote: $REMOTE_SW_VERSION"
    exit 1
  fi
  # Verify buttons exist
  BUTTON_COUNT=$(curl -s "https://$DOMAIN/" | grep -c 'btn-generate-key.*button')
  if [[ "$BUTTON_COUNT" -ne 1 ]]; then
    echo "ERROR: $DOMAIN missing Generate New Key button! Count: $BUTTON_COUNT"
    exit 1
  fi
  # Verify nacl.min.js loads
  NACL_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/nacl.min.js")
  if [[ "$NACL_STATUS" -ne 200 ]]; then
    echo "ERROR: $DOMAIN nacl.min.js not loading! Status: $NACL_STATUS"
    exit 1
  fi
  echo "=== $DOMAIN deployed successfully ==="
done

echo "\n=== All deployments complete and verified ==="
