#!/usr/bin/env bash
set -euo pipefail

# Phase 9 operator-run acceptance script for static-first one-image distribution.
# Requires: docker daemon, docker buildx, python3, curl.

IMAGE_TAG="${IMAGE_TAG:-punkto:stage3-static-first}"
WORKDIR="${WORKDIR:-$(pwd)/.tmp-static-first}"
PORT_A="${PORT_A:-18080}"
PORT_B="${PORT_B:-18081}"

mkdir -p "$WORKDIR"/node-a-data "$WORKDIR"/node-b-data

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed on this host."
  echo "This acceptance script must run on an operator host with a docker daemon."
  exit 1
fi

cat <<MSG
[static-first acceptance]
- image tag: $IMAGE_TAG
- node A port: $PORT_A
- node B port: $PORT_B
- workdir: $WORKDIR
MSG

echo "[1/9] Build combined image (amd64 + arm64 invocation)"
docker buildx build --platform linux/amd64,linux/arm64 -t "$IMAGE_TAG" --load .

echo "[2/9] Launch node A"
docker rm -f punkto-a >/dev/null 2>&1 || true
docker run -d --name punkto-a \
  -p "$PORT_A:8000" \
  -e PUNKTO_NODE_NAME=node-a \
  -e PUNKTO_WEB_ENABLED=true \
  -e PUNKTO_PUBLICATION_ENABLED=true \
  -v "$WORKDIR/node-a-data:/data" \
  "$IMAGE_TAG"

echo "[3/9] Browser smoke + API smoke against node A"
cat <<SMOKE
Manual browser smoke (required; not automated by this script):
  Open http://127.0.0.1:${PORT_A}/ in a browser and verify the PWA shell loads.
SMOKE
curl -fsS "http://127.0.0.1:$PORT_A/health" >/dev/null
curl -fsS "http://127.0.0.1:$PORT_A/publication/root.json" >/dev/null

echo "[4/9] Submit + static read round-trip"
ROOT_DIR="$(pwd)"
PORT_A_ENV="$PORT_A" ROOT_DIR="$ROOT_DIR" python3 - <<'PY'
import json
import os
import sys
import urllib.request

root = os.environ['ROOT_DIR']
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'experimental/punkti-v0.6-mesh/tests'))

from support import fixture
from punkti_node.mesh import wire

base = f"http://127.0.0.1:{os.environ['PORT_A_ENV']}"

raw = fixture(901)
wrapper = wire(raw)
payload = json.dumps({'records': [wrapper]}).encode('utf-8')

submit_req = urllib.request.Request(
    base + '/submit',
    data=payload,
    headers={'Content-Type': 'application/json'},
)
with urllib.request.urlopen(submit_req, timeout=8) as response:
    body = json.loads(response.read().decode('utf-8'))
assert body['results'][0]['duplicate'] is False
assert body['results'][0]['mid'].startswith('punkti/0.6:')

with urllib.request.urlopen(base + '/publication/root.json', timeout=8) as response:
    root_doc = json.loads(response.read().decode('utf-8'))
assert root_doc['v'] == 'punkti/pub/0.6'
assert root_doc['seq'] >= 1
assert len(root_doc['head']) == 64

print('submit accepted and publication root advanced', root_doc['seq'], root_doc['head'])
PY

echo "[5/9] Restart durability check"
ROOT_HEAD_BEFORE="$(curl -fsS "http://127.0.0.1:$PORT_A/publication/root.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["head"])')"
docker restart punkto-a >/dev/null
sleep 2
ROOT_HEAD_AFTER="$(curl -fsS "http://127.0.0.1:$PORT_A/publication/root.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["head"])')"
if [ "$ROOT_HEAD_BEFORE" != "$ROOT_HEAD_AFTER" ]; then
  echo "ERROR: publication root head changed unexpectedly across restart"
  exit 1
fi

echo "[6/9] Launch node B and static-replicate node A"
docker rm -f punkto-b >/dev/null 2>&1 || true
docker run -d --name punkto-b \
  -p "$PORT_B:8000" \
  -e PUNKTO_NODE_NAME=node-b \
  -e PUNKTO_WEB_ENABLED=true \
  -e PUNKTO_PUBLICATION_ENABLED=true \
  -e PUNKTO_PEERS="http://host.docker.internal:$PORT_A" \
  -v "$WORKDIR/node-b-data:/data" \
  "$IMAGE_TAG"

ROOT_A_HEAD="$(curl -fsS "http://127.0.0.1:$PORT_A/publication/root.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["head"])')"
REPL_DEADLINE=$(( $(date +%s) + 30 ))
ROOT_B_HEAD=""
while [ "$(date +%s)" -lt "$REPL_DEADLINE" ]; do
  ROOT_B_HEAD="$(curl -fsS "http://127.0.0.1:$PORT_B/publication/root.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["head"])')"
  if [ "$ROOT_A_HEAD" = "$ROOT_B_HEAD" ]; then
    break
  fi
  sleep 2
done
if [ "$ROOT_A_HEAD" != "$ROOT_B_HEAD" ]; then
  echo "ERROR: node B publication head does not match node A after replication wait"
  echo "A head: $ROOT_A_HEAD"
  echo "B head: $ROOT_B_HEAD"
  exit 1
fi

echo "[7/9] Disable UI while keeping publication serving"
docker rm -f punkto-a >/dev/null
cat > "$WORKDIR/node-a-no-ui.yml" <<YML
web:
  enabled: false
publication:
  enabled: true
  serve_prefix: /publication
YML
docker run -d --name punkto-a \
  -p "$PORT_A:8000" \
  -e PUNKTO_NODE_CONFIG=/config/punkto-node.yml \
  -v "$WORKDIR/node-a-data:/data" \
  -v "$WORKDIR/node-a-no-ui.yml:/config/punkto-node.yml:ro" \
  "$IMAGE_TAG"

sleep 2
curl -fsS "http://127.0.0.1:$PORT_A/publication/root.json" >/dev/null
if curl -fsS "http://127.0.0.1:$PORT_A/" >/dev/null 2>&1; then
  echo "ERROR: web app UI should be disabled in step 7, but / is still served"
  exit 1
fi

echo "[8/9] Capture container status"
docker ps --filter name=punkto-a --filter name=punkto-b

echo "[9/9] Cleanup hint"
cat <<CLEAN
To clean up:
  docker rm -f punkto-a punkto-b
  rm -rf "$WORKDIR"
CLEAN

echo "[static-first acceptance] completed"
