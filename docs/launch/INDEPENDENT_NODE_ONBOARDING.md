# Independent node onboarding: C2 experiment

## 1. What this proves / what it does not prove

The proposed test demonstrates a copy held under separate operator authority, on
separate host and storage, surviving loss of founder origins and a local restart.
Hostnames alone do not establish independence. No independent operator has yet
completed this package; C2 is **not proven** by shipping it. No availability or
permanence guarantee is made. Ed25519 authorship is real, but not post-quantum.

A tooling rehearsal of this package on a founder-controlled host is recorded in
[`../evidence/issue-39/c2-package-rehearsal.txt`](../evidence/issue-39/c2-package-rehearsal.txt).
It verifies the commands, not independence.

## 2. Preconditions for the operator

Use your own machine/VM and storage, root or Docker-group access, Docker Engine
with Compose, approximately 1 GB free disk, and an optional domain or public IP.
Founder-controlled hosts do not qualify. Record **explicit written consent** with
UTC timestamp before running the experiment. Have a separate disposable test
client with Python 3.12+, curl, and Git. No root access is needed on the test client.

### Getting the verifier

The C2 tooling lives on `docs/c2-independent-node-onboarding`, based on
`docs/c1-custody-handoff` (PR #144). PR #144 is open and unmerged by Founder
decision, so `custody_verify.py` is not yet on `main`. Obtain the package from a
reviewed commit of the C2 branch, or a release archive provided by the coordinator,
not from `main`.

Initialize the evidence directory before cloning:

```bash
OP_DIR="$HOME/punkti-c2"
mkdir -p "$OP_DIR"
git clone https://github.com/Fisker1111/Punkto.git
cd Punkto
git fetch origin docs/c2-independent-node-onboarding
git checkout docs/c2-independent-node-onboarding
git rev-parse HEAD | tee "$OP_DIR/repo-commit.txt"
```

Compare the recorded SHA with the coordinator-reviewed commit before proceeding.
If the branch has moved, check out the reviewed SHA and record `git rev-parse HEAD`
again. Record the package branch and exact SHA in §10's evidence template.

For a coordinator-provided tarball, the only repository files strictly required
for the custody verification steps are `scripts/qa/custody_verify.py`,
`scripts/qa/independent_node_import.py`, and the `punkti_node/` package:
`custody_verify.py` imports the repository's own `punkti_node/carrier.py`. Preserve
that relative directory layout and record the archive's source commit SHA. The
node itself runs from the container image. The full drill also uses the templates
and blackout proxy; install the verifier's cryptography dependency as below.

Obtain a checkout of `https://github.com/Fisker1111/Punkto` at the coordinator-reviewed
commit. It supplies `scripts/qa/custody_verify.py`,
`scripts/qa/independent_node_import.py`, the blackout proxy, templates, and
`node/requirements.txt`. Record `git rev-parse HEAD`; use this checkout on both hosts.

On the operator host, start in this repository's root. Keep this Bash session:

```bash
set -euo pipefail
REPO="$PWD"
OP_DIR="$HOME/punkti-c2"
mkdir -p "$OP_DIR"
cp docs/launch/independent-node/docker-compose.yml "$OP_DIR/"
cp docs/launch/independent-node/node-config.yml "$OP_DIR/"
python3 -m venv "$OP_DIR/venv"
"$OP_DIR/venv/bin/python" -m pip install -r node/requirements.txt
PY="$OP_DIR/venv/bin/python"
IMPORT="$REPO/scripts/qa/independent_node_import.py"
VERIFY="$REPO/scripts/qa/custody_verify.py"
```

The transport CLI itself uses only stdlib. The existing custody verifier requires
the repository's cryptography dependency; the node requirements install it.

Before the drill, after downloading the ROOT record to `$OP_DIR/records/root.record`
as in §6, run this one-line verifier sanity check (stop on failure):

```bash
"$PY" "$VERIFY" --file "$OP_DIR/records/root.record" --expect-sha256 2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d
```

## 3. Which image to run

The supplied C2 baseline establishes that `ghcr.io/fisker1111/punkti-node` is not
publicly pullable. Use the public single image `ghcr.io/fisker1111/punkto`, which
contains the same generic node plus the PWA. Resolve the example tag to a digest
and record it; tags alone are mutable. There is no `latest` tag. The reviewed
`0.7.0-draft.2` manifest-list digest is
`sha256:8d8ecc2420c05aa039411f679ba5d88f0b52130d5b01baa12d91b71303ee298a`;
prefer that digest-pinned image for reproducibility:

```bash
docker pull ghcr.io/fisker1111/punkto:0.7.0-draft.2
PUNKTO_IMAGE="$(docker image inspect ghcr.io/fisker1111/punkto:0.7.0-draft.2 --format '{{index .RepoDigests 0}}')"
test -n "$PUNKTO_IMAGE"
export PUNKTO_IMAGE
printf 'PUNKTO_IMAGE=%s\n' "$PUNKTO_IMAGE" > "$OP_DIR/.env"
docker image inspect "$PUNKTO_IMAGE" --format '{{json .RepoDigests}}' | tee "$OP_DIR/image-digests.json"
```

Alternatively build the generic node from this source checkout (no registry pull
of a private node image required):

```bash
docker build -f node/Dockerfile -t punkti-c2-local .
export PUNKTO_IMAGE=punkti-c2-local
printf 'PUNKTO_IMAGE=%s\n' "$PUNKTO_IMAGE" > "$OP_DIR/.env"
git rev-parse HEAD > "$OP_DIR/source-sha.txt"
docker image inspect "$PUNKTO_IMAGE" --format '{{.Id}}' | tee "$OP_DIR/local-image-id.txt"
```

For a local build, report the content-addressed image ID and source SHA; there is
no registry manifest digest until it is published.

## 4. Operator configuration

Edit `$OP_DIR/node-config.yml`, replacing `operator.example:8000` with your own
reachable origin and choosing your local node name. The complete template is
[`independent-node/node-config.yml`](independent-node/node-config.yml):

```yaml
node:
  name: independent-c2-node
  public_url: http://operator.example:8000
network:
  listen_host: 0.0.0.0
  listen_port: 8000
  advertise_url: ''
  peers: []
bootstrap:
  nodes: []
storage:
  data_path: /data
publication:
  enabled: true
  serve_prefix: /publication
web:
  enabled: false
# write_safety is intentionally omitted: all defaults remain active.
```

All keys come from `punkti_node/config.py` DEFAULTS. `node.public_url` is your
public origin. A nonempty `network.advertise_url` is the protocol-visible callback
origin and takes precedence. `network.listen_host` and `network.listen_port`
only control local binding; they do not advertise an origin. TLS termination is
your responsibility; plain HTTP is acceptable for this drill. Web/PWA serving is
disabled because this test only needs the generic node. No peers or bootstrap
nodes are configured. `write_safety` retains all defaults, including a one-record
batch limit. The recommended setup does not need a public write path: do not
expose `/submit` publicly. Restrict external `/submit` at your own firewall/proxy
while retaining public read routes. Compose publishes the node port; it does not
provide that route restriction itself. Route A below writes the stopped store directly.

## 5. Compose file

Complete [`independent-node/docker-compose.yml`](independent-node/docker-compose.yml):

```yaml
services:
  node:
    image: ${PUNKTO_IMAGE:-ghcr.io/fisker1111/punkto:0.7.0-draft.2}
    environment:
      PUNKTO_NODE_CONFIG: /config/punkti-node.yml
    volumes:
      - ./node-config.yml:/config/punkti-node.yml:ro
      - punkti-data:/data
    ports:
      - "8000:8000"
    restart: unless-stopped
    stop_grace_period: 60s
    healthcheck:
      test: ["CMD", "python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3).close()"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
volumes:
  punkti-data:
```

The explicit environment variable selects the mounted config rather than the
image's default filename. Keep this directory/project name stable. The named
volume persists across `docker compose down` and container recreation; **do not
use `down -v` or remove the volume**. The node stores its durable log at
`/data/atoms.jsonl` and republishes under `/data/publication`.

```bash
cd "$OP_DIR"
docker compose config
docker compose run --rm node --check-config
docker compose up -d
docker compose ps
curl --fail --silent --show-error http://127.0.0.1:8000/health
curl --fail --silent --show-error http://127.0.0.1:8000/ready
```

## 6. Importing the two records (no re-signing, no rewriting)

Create a reusable local verification script containing the immutable expectations:

```bash
cat > "$OP_DIR/verify-pair.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
: "${REPO:?set REPO to the checkout root}"
: "${PY:?set PY to the verifier Python}"
DIR="${1:?record directory}"
"$PY" "$REPO/scripts/qa/custody_verify.py" --file "$DIR/root.record" \
  --expect-sha256 2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d \
  --expect-mid punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed \
  --expect-h s00000000000_0
"$PY" "$REPO/scripts/qa/custody_verify.py" --file "$DIR/reply.record" \
  --expect-sha256 0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b \
  --expect-mid punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854 \
  --expect-h s00000000000_0 \
  --expect-reply-of punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed
SH
export REPO PY
ROOT_SHA=2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d
REPLY_SHA=0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b
ROOT_MID=punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed
REPLY_MID=punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854
mkdir -p "$OP_DIR/records"
"$PY" "$IMPORT" fetch --url https://punkto.xyz/publication/records/24/2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d --out "$OP_DIR/records/root.record" --sha256 "$ROOT_SHA"
"$PY" "$IMPORT" fetch --url https://punkto.xyz/publication/records/0c/0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b --out "$OP_DIR/records/reply.record" --sha256 "$REPLY_SHA"
bash "$OP_DIR/verify-pair.sh" "$OP_DIR/records" | tee "$OP_DIR/import-verification.jsonl"
```

Stop on any verification failure. Choose one route; do not import through both.

### Route A — recommended, write-free

Section 5's initial startup creates `meta.json` and the empty `atoms.jsonl` in the
named volume. Preserve that metadata: the node refuses an existing log without
`meta.json`. Stop the node before writing; no other process may write this volume.
The tested `seed` helper appends one compact wrapper per verified file. It only
base64-encodes the existing record bytes; it does not sign or rewrite them.

```bash
cd "$OP_DIR"
docker compose stop
# Mount the verified files and helper into a one-off container sharing /data.
docker compose run --rm --no-deps --entrypoint python \
  -v "$REPO/scripts/qa/independent_node_import.py:/seed.py:ro" \
  -v "$OP_DIR/records:/records:ro" node /seed.py seed --data-dir /data \
  --file /records/root.record --sha256 "$ROOT_SHA" --address "$ROOT_MID" --append
docker compose run --rm --no-deps --entrypoint python \
  -v "$REPO/scripts/qa/independent_node_import.py:/seed.py:ro" \
  -v "$OP_DIR/records:/records:ro" node /seed.py seed --data-dir /data \
  --file /records/reply.record --sha256 "$REPLY_SHA" --address "$REPLY_MID" --append
docker compose up -d
```

For an operator using a directly mounted data directory instead, this short
stdlib equivalent shows the wrapper construction. Use it **instead of** the two
`seed` calls, with the node stopped and `DATA_DIR` set to its initialized data
directory. The files must already have passed `verify-pair.sh` above.

```bash
: "${DATA_DIR:?set the initialized node data directory; node must be stopped}"
"$PY" - "$DATA_DIR" "$OP_DIR/records" "$ROOT_MID" "$REPLY_MID" <<'PY'
import base64, hashlib, json, pathlib, sys
store, records = map(pathlib.Path, sys.argv[1:3])
assert (store / 'meta.json').is_file(), 'initialize the node before seeding'
with (store / 'atoms.jsonl').open('ab', buffering=0) as out:
    for name, mid in zip(('root.record', 'reply.record'), sys.argv[3:]):
        raw = (records / name).read_bytes()
        wrapper = {'address': mid, 'sha256': hashlib.sha256(raw).hexdigest(),
                   'record': base64.b64encode(raw).decode('ascii')}
        out.write((json.dumps(wrapper, separators=(',', ':')) + '\n').encode())
PY
```

Start the node after the snippet. Startup replays the durable log, re-verifies each
record using the carrier, and republishes admitted records under `/data/publication`.
Malformed or tampered lines are rejected by replay; check the readiness counts and
record bytes below. Do not reseed on restart or rerun: inspect the existing copy.

### Route B — optional, uses the node's write path

Use this only if you deliberately choose to expose the node's write path for the
import. `POST /submit` is the provider-side public write surface, governed by
`write_safety` (enabled by default, maximum batch one, with rate limits). Keep the
defaults; use host loopback and keep external `/submit` blocked. Route A avoids
this write path entirely.

```bash
"$PY" "$IMPORT" submit --base http://127.0.0.1:8000 --file "$OP_DIR/records/root.record" --sha256 "$ROOT_SHA" --address "$ROOT_MID"
"$PY" "$IMPORT" submit --base http://127.0.0.1:8000 --file "$OP_DIR/records/reply.record" --sha256 "$REPLY_SHA" --address "$REPLY_MID"
```

Stop on any failure. The tool reads the file as bytes, checks its SHA-256,
base64-encodes those bytes, and sends exactly one wrapper per request:

```json
{"records":[{"record":"<base64 raw bytes>","sha256":"<hex SHA-256>","address":"<MID>"}]}
```

For inspection, this prints the exact JSON body construction without submitting:

```bash
"$PY" - "$OP_DIR/records/root.record" "$ROOT_MID" <<'PY'
import base64, hashlib, json, pathlib, sys
raw = pathlib.Path(sys.argv[1]).read_bytes()
print(json.dumps({"records": [{"record": base64.b64encode(raw).decode('ascii'),
    "sha256": hashlib.sha256(raw).hexdigest(), "address": sys.argv[2]}]}))
PY
```

The node re-verifies locally. No new posts, no re-signing, no rewriting: byte
identity is preserved. The CLI succeeds only for this record's `admitted: true`;
a duplicate response is nonzero. On a rerun, inspect the duplicate result and
verify the already-stored copy using the serving checks instead of deleting data.

## 7. Serving check

After Route A, records appear only after replay and republication. Wait for
`/ready` with `store.valid == 2` before the record GETs. Stop and investigate if
readiness fails. Set your actual operator origin (replace the example):

```bash
OPERATOR_ORIGIN=http://operator.example:8000
curl --fail --silent --show-error "$OPERATOR_ORIGIN/ready" > "$OP_DIR/ready.json"
"$PY" - "$OP_DIR/ready.json" <<'PY'
import json, pathlib, sys
ready = json.loads(pathlib.Path(sys.argv[1]).read_text())
assert ready['status'] == 'ready' and ready['store']['valid'] == 2, ready
assert ready['store']['corrupt_lines'] == 0, ready
PY
"$PY" "$IMPORT" check --base "$OPERATOR_ORIGIN" --sha256 "$ROOT_SHA" --expect-bytes 447
"$PY" "$IMPORT" check --base "$OPERATOR_ORIGIN" --sha256 "$REPLY_SHA" --expect-bytes 298
for route in node/info health ready; do
  curl --fail --silent --show-error -i "$OPERATOR_ORIGIN/$route"
done
```

Expect HTTP 200 at `/publication/records/24/$ROOT_SHA` (447 bytes) and
`/publication/records/0c/$REPLY_SHA` (298 bytes), with exactly the hashes above.
Paste the tool's JSON plus the status and body of `/node/info`, `/health`, and
`/ready` as evidence; do not replace actual output with an assumed response.

## 8. Origin-loss drill (test client only)

Use a disposable **test client**, not the operator host or any production host.
Never touch production, DNS, Cloudflare, origin guards, or production nodes.
Obtain a complete current inventory of **every founder-operated Punkti origin**
from the coordinator, including every alias, port, and literal IP they list. Do
not claim a complete blackout without that inventory. No additional founder
production endpoints are embedded here.

Before blackout, copy the repository and `verify-pair.sh` to the client, install
`node/requirements.txt` in a local venv as above, and define `REPO`, `PY`,
`IMPORT`, `ROOT_SHA`, `REPLY_SHA`, and `OPERATOR_ORIGIN` there with the same values.
Put the helper at `$REPO/verify-pair.sh` on this client. Do not copy record files
into the fetch output directories. Keep this client Bash session throughout both
drills. Create `founder-origins.txt` with one HTTP(S) origin per line from the
coordinator's inventory (no comments or blank lines).

Recommended: run the complete, stdlib-only threaded proxy at
`scripts/qa/independent_origin_block_proxy.py`. It uses `http.client` for HTTP
GET forwarding and CONNECT byte tunneling for HTTPS. It denies each inventoried
host on **all ports**, including literal IPv4/IPv6 hosts, by closing the connection
without an HTTP response. Other hosts are forwarded. It binds only client loopback;
this is a disposable drill tool, not a public proxy service. HTTPS certificates
remain checked by the client against the real origin; never use `curl -k`.

```bash
set -euo pipefail
export REPO PY
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export no_proxy='' NO_PROXY=''
"$PY" "$REPO/scripts/qa/independent_origin_block_proxy.py" \
  --origins founder-origins.txt --port 8765 > blackout-proxy.log 2>&1 &
PROXY_PID=$!
export http_proxy=http://127.0.0.1:8765
export https_proxy="$http_proxy"
# Wait for the listener; inspect blackout-proxy.log if this fails.
"$PY" - <<'PY'
import socket, time
for attempt in range(50):
    try:
        with socket.create_connection(('127.0.0.1', 8765), timeout=1):
            break
    except OSError:
        time.sleep(.1)
else:
    raise SystemExit('proxy did not start')
PY
kill -0 "$PROXY_PID"
```

Negative control, required now and again after each restore:

```bash
negative_control() {
  local origin code rc
  while IFS= read -r origin || [ -n "$origin" ]; do
    rc=0
    code=$(curl --silent --show-error --connect-timeout 3 --max-time 5 \
      --output /dev/null --write-out '%{http_code}:%{http_connect}' "$origin") || rc=$?
    # Proxy denials: empty HTTP reply (52), CONNECT failure (56), or reset (55).
    # Require no origin HTTP status AND no proxy CONNECT status.
    # TLS errors, timeouts, and bad URLs are failures.
    if [ "$code" != 000:000 ] || { [ "$rc" != 52 ] && [ "$rc" != 56 ] && [ "$rc" != 55 ]; }; then
      printf 'FAIL: %s HTTP=%s curl=%s\n' "$origin" "$code" "$rc" >&2
      return 1
    fi
    printf 'BLOCKED: %s HTTP=%s curl=%s\n' "$origin" "$code" "$rc"
  done < founder-origins.txt
}
negative_control | tee blackout-negative-control.txt
cat blackout-proxy.log
```

Do **not** use `curl --fail` for this control: any HTTP response, even 403 or 404,
means reachability and invalidates the blackout. Match every negative-control
attempt to a `DENY` entry in the proxy log; unrelated connection failures do not
prove enforcement. Successful operator GETs below also confirm proxy forwarding.

Hostname-only alternative (instead of the proxy): use `curl --resolve` or
`curl --connect-to` with client loopback, where nothing listens on the chosen
port. This documented alternative does not cover literal-IP inventory entries;
use the proxy (or a client firewall) for those. The following example targets an
inventoried hostname, not a founder endpoint supplied by this runbook:

```bash
HOST=founder.example
PORT=443
# Run with each inventoried hostname/port; use its actual scheme and origin.
# Each command must report HTTP=000 and curl exit 7 (connection refused).
rc=0
curl --noproxy '*' --resolve "$HOST:$PORT:127.0.0.1" \
  --connect-timeout 3 --max-time 5 --output /dev/null --write-out 'HTTP=%{http_code}\n' \
  "https://$HOST:$PORT" || rc=$?
test "$rc" -eq 7
rc=0
curl --noproxy '*' --connect-to "$HOST:$PORT:127.0.0.1:$PORT" \
  --connect-timeout 3 --max-time 5 --output /dev/null --write-out 'HTTP=%{http_code}\n' \
  "https://$HOST:$PORT" || rc=$?
test "$rc" -eq 7
```

These flags apply only to that curl invocation. If choosing this alternative,
apply the mappings to **every** founder-origin curl request and repeat the full
inventory's connection-failure controls after restore. They do not block Python
or browser clients; use the proxy for the complete multi-client drill below.
A certificate error, timeout, or any HTTP status is not a valid negative control.
Then fetch from your operator origin:

```bash
fetch_and_verify() {
  local output_dir="$1"
  mkdir "$output_dir"
  "$PY" "$IMPORT" fetch --url "$OPERATOR_ORIGIN/publication/records/24/$ROOT_SHA" --out "$output_dir/root.record" --sha256 "$ROOT_SHA"
  "$PY" "$IMPORT" fetch --url "$OPERATOR_ORIGIN/publication/records/0c/$REPLY_SHA" --out "$output_dir/reply.record" --sha256 "$REPLY_SHA"
  "$PY" "$IMPORT" check --base "$OPERATOR_ORIGIN" --sha256 "$ROOT_SHA" --expect-bytes 447
  "$PY" "$IMPORT" check --base "$OPERATOR_ORIGIN" --sha256 "$REPLY_SHA" --expect-bytes 298
  bash "$REPO/verify-pair.sh" "$output_dir"
}
fetch_and_verify blackout-records | tee blackout-verification.jsonl
```

Require both successful hash/length checks and verifier `ok: true`, `state: VALID`,
`ed25519: VALID`, canonical body, MID, location, and reply relationship checks.
Keep the blackout in place for the restore drill.

## 9. Restore / durability drill

### Variant A — retained volume

On the **operator host**, retain the same named data volume (the retained-volume
restore variant). Stop, remove/recreate the container, and start it from that
retained durable copy:

```bash
cd "$OP_DIR"
docker compose stop
docker compose down
docker compose up -d
docker compose ps
curl --fail --silent --show-error http://127.0.0.1:8000/ready
```

Wait for readiness if startup is still in progress. Do not import again. On the
**same test client**, while the blackout remains active:

```bash
negative_control | tee restore-negative-control.txt
fetch_and_verify restored-records | tee restore-verification.jsonl
```

This tests that the operator's durable copy survives founder-origin loss and a
node/container restart. It does **not** test loss of the operator's own volume,
survival of the operator itself, or recovery from a separate backup. Report the
retained-volume method honestly; do not describe it as a tar-backup recovery.

### Variant B — restored backup

This is the stronger durability claim: a separate copy survives loss of the
original volume. A retained volume is not a backup. Report the two variants
separately, including any skipped variant. On the **operator host**, stop the
node, archive the complete data directory (including `atoms.jsonl`, `meta.json`,
`cursors.json` when present, and `publication/`), and record the archive SHA-256.
No sync runs in this isolated setup, so `cursors.json` may not yet exist; preserve
it if present rather than inventing one.

```bash
cd "$OP_DIR"
docker compose stop
mkdir -p "$OP_DIR/backups"
BACKUP="c2-data-$(date -u +%Y%m%dT%H%M%SZ).tar"
docker compose run --rm --no-deps --entrypoint python \
  -v "$OP_DIR/backups:/backup" node -c \
  'import sys, tarfile; t = tarfile.open(sys.argv[1], "x"); t.add("/data", arcname="."); t.close()' \
  "/backup/$BACKUP"
sha256sum "$OP_DIR/backups/$BACKUP" | tee "$OP_DIR/backups/$BACKUP.sha256"
# Create a fresh directory. Refuse to reuse any existing restore directory.
RESTORED_DIR="$OP_DIR/restored-data"
mkdir "$RESTORED_DIR"
# Trusted local backup only. Python tarfile preserves the complete archived tree.
docker compose run --rm --no-deps --entrypoint python \
  -v "$OP_DIR/backups:/backup:ro" -v "$RESTORED_DIR:/restored" node -c \
  'import sys, tarfile; t = tarfile.open(sys.argv[1]); t.extractall("/restored", filter="data"); t.close()' \
  "/backup/$BACKUP"
# Compose merges volume mounts by target, replacing /data with the restored copy.
cat > "$OP_DIR/restore.compose.yml" <<'YAML'
services:
  node:
    volumes:
      - ./restored-data:/data
YAML
docker compose -f docker-compose.yml -f restore.compose.yml config
docker compose -f docker-compose.yml -f restore.compose.yml up -d --force-recreate
docker compose -f docker-compose.yml -f restore.compose.yml ps
curl --fail --silent --show-error http://127.0.0.1:8000/ready
```

Confirm `/ready` is ready with `store.valid == 2`. Do not import again. On the
**same test client**, with its proxy blackout still active:

```bash
negative_control | tee backup-restore-negative-control.txt
fetch_and_verify backup-restored-records | tee backup-restore-verification.jsonl
# Only after recording all selected drill results, remove the client-only blackout.
kill "$PROXY_PID"
wait "$PROXY_PID" || true
unset http_proxy https_proxy no_proxy NO_PROXY
```

Record the backup filename, hash, restored directory, and actual verification
results. This tests recovery from that backup, not future availability or survival
of the operator. Keep using the restore override for subsequent commands if the
restored copy is the active node data.

## 10. Evidence template

```text
C2 independent operator experiment — actual observations only
Operator name/handle:
Consent: I consent to run this preservation experiment on my own host/storage.
Consent UTC timestamp:
Independent authority/host/storage statement:
Host/IP/domain (may be redacted):
Package branch + exact commit SHA used:
Image reference + registry digest (or local image ID + source SHA):
Config path + edited config:
Exact commands run (host/client distinguished):
Initial ROOT GET: status / bytes / SHA-256:
Initial REPLY GET: status / bytes / SHA-256:
/node/info, /health, /ready status and output:
Founder-origin inventory source/date/completeness:
Blackout method and client:
Negative-control output before and after restart:
Blackout ROOT and REPLY GET: status / bytes / SHA-256:
Restart/restore commands and results (retained volume):
Post-restart ROOT and REPLY GET: status / bytes / SHA-256:
Backup file SHA-256 and restore method (or explicitly not tested):
Variant B restored-copy readiness and ROOT/REPLY verification results:
Custody verification JSON (initial, blackout, post-restart):
Observed: [only results actually measured]
Not observed: operator loss; actual volume loss; long-term availability; permanence;
              post-quantum security; [any skipped or failed checks]
Client blackout removed at:
```

## 11. Invitation text

> Would you consent to a roughly 30–60 minute independent preservation experiment?
> You would run a generic Punkti node container on your own host and storage,
> import two existing signed Null Island records without changing them, and serve
> their exact bytes from your own origin. You would verify them from a test client
> while that client blocks founder origins, then restart your node and verify
> again. No production system is touched. You retain your data and control your
> host; you may stop participating at any time. This is a preservation experiment,
> not a service or an availability/permanence promise. The package includes the
> configuration, commands, verifier, and evidence template. Please reply with your
> name/handle, an explicit statement that you consent to run it on your own
> independently controlled host/storage, and a UTC timestamp. Host details may be
> redacted in the evidence. We will not count participation or independence until
> you consent and supply the observed results.

For an authorized third party to send; this document does not send an invitation.

## 12. Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Image not pullable | Private node image, missing tag, or registry failure | Use the public single-image tag and record its digest, or build `node/Dockerfile`. |
| Config validation error | Unknown key, invalid origin, or wrong mount path | Use the supplied YAML, edit only real keys, retain `PUNKTO_NODE_CONFIG`, rerun the config check. |
| `/submit` rejected | Rate limit (429), batch greater than one, digest/address mismatch | Wait and retry rate limits; submit one verified raw file per request; compare expected hash/MID. Never re-sign or rewrite. |
| Record path returns 404 | Publication disabled/not republished, wrong prefix/hash, or import failed | Inspect admission output and node logs, confirm publication config and exact path. Do not count the copy until GET verification passes. |
| Records disappear on restart | Volume omitted, removed, or a different Compose project selected | Restore the original retained volume/project; keep `punkti-data:/data`; never use `down -v`. Repeat the drill and record failure. |
| Founder origin still reachable during blackout | Incomplete inventory, alias/IP omitted, or proxy bypass | Complete the coordinator inventory, verify `no_proxy` does not bypass the proxy, and repeat controls. Any HTTP status means reachable. |
| Records not served after seeding | Wrong wrapper shape, node running during write, `publication.enabled: false`, or `store.valid` not 2 | Verify wrapper JSON, confirm the node was stopped during writing, enable publication, and inspect `/ready` counts before GETs. |
| custody_verify.py missing or import error | Operator cloned main; PR #144 is unmerged so the verifier is not on main | Fetch the reviewed C2 branch commit, or use the coordinator-provided archive; record the SHA |
