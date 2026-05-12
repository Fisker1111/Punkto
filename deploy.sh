#!/bin/bash
# Punkto PWA Deployment Script - ensures consistent deploys to app1/app2
set -e

USER="root"
PASS="3AtIAvCwwI@dok<Bc^Cd"
APP1="app1.punkto.xyz"
APP2="app2.punkto.xyz"
DEST="/var/www/punkto"
SRC="/a0/usr/projects/punkto/pwa"

echo "=== Deploying to $APP1 ==="
sshpass -p "$PASS" scp "$SRC"/* "$USER@$APP1:$DEST/"
sshpass -p "$PASS" ssh "$USER@$APP1" "nginx -t && systemctl reload nginx"

echo "=== Deploying to $APP2 ==="
sshpass -p "$PASS" scp "$SRC"/* "$USER@$APP2:$DEST/"
sshpass -p "$PASS" ssh "$USER@$APP2" "nginx -t && systemctl reload nginx"

echo "=== Verifying Deploy ==="
for ENDPOINT in "https://$APP1" "https://$APP2"; do
  echo "$ENDPOINT: Buttons=$(curl -s $ENDPOINT | grep -c 'btn-generate-key.*button') SW=$(curl -s $ENDPOINT/sw.js | grep 'CACHE_NAME' | head -1)"
done

echo "=== Deploy Complete ==="
