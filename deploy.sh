#!/bin/bash
set -euo pipefail

# Config
SRC_DIR="/a0/usr/projects/punkto/pwa"
RELAY_SRC="/a0/usr/projects/punkto/relay/relay.py"
DEST_DIR="/var/www/punkto"
RELAY_DEST="/opt/punkto-relay"
USER="root"
PASS="3AtIAvCwwI@dok<Bc^Cd"
DOMAINS=("punkto.xyz" "app1.punkto.xyz" "app2.punkto.xyz")

# Check local files exist
echo "=== Checking local PWA files ==="
for f in index.html app.js sw.js nacl.min.js key-management.js manifest.json geohash3d.js lib/maplibre-gl.css lib/maplibre-gl.js lib/dist.min.js lib/dexie.min.js; do
  if [[ ! -f "$SRC_DIR/$f" ]]; then
    echo "ERROR: Missing $SRC_DIR/$f"
    exit 1
  fi
done

# Check relay.py exists
if [[ ! -f "$RELAY_SRC" ]]; then
  echo "ERROR: Missing $RELAY_SRC"
  exit 1
fi

# Get local SW version
LOCAL_SW_VERSION=$(grep -oP "CACHE_NAME = '\Kpunkto-v\d+" "$SRC_DIR/sw.js")
echo "Local SW version: $LOCAL_SW_VERSION"

# Deploy to each domain
for DOMAIN in "${DOMAINS[@]}"; do
  echo -e "\n=== Deploying to $DOMAIN ==="
  
  # Copy PWA files recursively (includes lib/ subdir)
  echo "Copying PWA files..."
  sshpass -p "$PASS" scp -r "$SRC_DIR/." "$USER@$DOMAIN:$DEST_DIR/"
  
  # Deploy relay.py
  echo "Deploying relay.py..."
  sshpass -p "$PASS" scp "$RELAY_SRC" "$USER@$DOMAIN:$RELAY_DEST/relay.py"
  
  # Reload nginx
  echo "Reloading nginx..."
  sshpass -p "$PASS" ssh "$USER@$DOMAIN" "nginx -t && systemctl reload nginx"
  
  # Restart relay service
  echo "Restarting punkto-relay..."
  sshpass -p "$PASS" ssh "$USER@$DOMAIN" "systemctl restart punkto-relay"
  
  # Verify relay is running
  RELAY_STATUS=$(sshpass -p "$PASS" ssh "$USER@$DOMAIN" "systemctl is-active punkto-relay")
  if [[ "$RELAY_STATUS" != "active" ]]; then
    echo "ERROR: $DOMAIN relay service not active! Status: $RELAY_STATUS"
    exit 1
  fi
  
  # Verify SW version matches
  echo "Verifying SW version..."
  REMOTE_SW_VERSION=$(curl -s "https://$DOMAIN/sw.js" | grep -oP "CACHE_NAME = '\Kpunkto-v\d+")
  if [[ "$REMOTE_SW_VERSION" != "$LOCAL_SW_VERSION" ]]; then
    echo "ERROR: $DOMAIN SW version mismatch! Local: $LOCAL_SW_VERSION, Remote: $REMOTE_SW_VERSION"
    exit 1
  fi
  
  # Verify buttons exist
  echo "Verifying Generate New Key button..."
  BUTTON_COUNT=$(curl -s "https://$DOMAIN/" | grep -c 'btn-generate-key.*button')
  if [[ "$BUTTON_COUNT" -ne 1 ]]; then
    echo "ERROR: $DOMAIN missing Generate New Key button! Count: $BUTTON_COUNT"
    exit 1
  fi
  
  # Verify nacl.min.js loads
  echo "Verifying nacl.min.js..."
  NACL_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/nacl.min.js")
  if [[ "$NACL_STATUS" -ne 200 ]]; then
    echo "ERROR: $DOMAIN nacl.min.js not loading! Status: $NACL_STATUS"
    exit 1
  fi
  
  # Verify lib files load
  echo "Verifying lib files..."
  for libfile in lib/maplibre-gl.css lib/maplibre-gl.js lib/dist.min.js lib/dexie.min.js; do
    LIB_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/$libfile")
    if [[ "$LIB_STATUS" -ne 200 ]]; then
      echo "ERROR: $DOMAIN $libfile not loading! Status: $LIB_STATUS"
      exit 1
    fi
  done
  
  # Verify CORS headers are not duplicated (relay fix)
  echo "Checking CORS headers..."
  CORS_COUNT=$(curl -sI "https://$DOMAIN/info" | grep -c "Access-Control-Allow-Origin")
  if [[ "$CORS_COUNT" -gt 1 ]]; then
    echo "WARNING: $DOMAIN has duplicate CORS headers! Count: $CORS_COUNT"
  else
    echo "CORS headers OK (count: $CORS_COUNT)"
  fi
  
  echo "=== $DOMAIN deployed successfully ==="
done

echo -e "\n=== All deployments complete and verified ==="
