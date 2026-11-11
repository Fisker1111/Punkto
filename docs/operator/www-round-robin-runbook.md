# www.punkto.xyz round-robin operator runbook

## 1. Readiness summary and go/no-go

**NO-GO. Review-only; this document does not authorize DNS cutover or any production
execution.** All commands below are proposals for AZ after separate explicit founder
authorization. Evidence is the supplied [Task 58 audit](../CODEX_TASK_58.md), verified
2026-11-10; the audit is not re-derived here. Repo deploy copies have drifted from live
host files and must not be used as whole-file replacements.

| Gate | Verdict | Evidence |
|---|---|---|
| www DNS resolves | FAIL | §1.1: CNAME app1.punkto.xyz TTL 3600; app1 has no A, AAAA or CNAME; www is broken on 1.1.1.1, 8.8.8.8 and 9.9.9.9 |
| Both www certificates usable | FAIL | §1.2: neither node has one; ACME DNS errors, not a challenge-method failure |
| DNS-01 credentials/tooling | BLOCKED | §1.2: saved node1 GoDaddy API credentials return 401; node2 has none and certbot has no DNS plugin |
| Direct www v0.6 serving | FAIL | §1.3: both www blocks redirect to apex, which resolves only to node1; node2 apex itself is legacy v1 |
| Node-local v0.6 origin available | PASS | §1.4: both use 172.22.0.3:8000 on their own punkti_edge network and the same image digest |
| Read-byte parity | PASS | §1.5: /, /ai, /health byte-identical (86209, 5834, 59 bytes respectively) |
| Signed publication convergence | FAIL | §1.5: node1 c77ba862… seq 14; node2 392bab15… seq 16; 15 record files identical but different signed publication states |
| Discovery document parity | FAIL | §1.5: /nodes.json differs in advertised https://punkto.xyz/submit for punkto-xyz |
| www write and MCP consistency | FAIL | §1.3–1.5: redirects today; node1 apex has public submit and MCP 405; node2 test2 has guarded submit and MCP 404 |
| Node2 canary data approval | BLOCKED | §1.4, §2.1: founder must decide whether www may serve test2's dataset |
| Capacity acceptance | BLOCKED | §1.6: node2 1 vCPU, 961 MB RAM, 409 MB available, no swap, 14 GB disk free, also legacy containers; no load acceptance recorded |
| Cutover authorization | BLOCKED | §0: founder has not authorized it |

The change is a repair of unreachable www, not a live-traffic migration. Identical
HTTP shape is **not** identical signed content. Do not cut over until publication
chains converge after separately reviewing/landing PR #151, or the founder explicitly
accepts serving two different publication heads. PR #151 is review-only, not merged;
this package does not implement replication or assume that work has landed.

## 2. Preconditions and order

1. Founder refreshes GoDaddy API credentials (currently HTTP 401), supplies them
   securely to each node, and approves the node2 test2 canary dataset decision.
2. Record chain convergence evidence or the explicit divergence exception; resolve
   discovery parity expectations and node2 capacity acceptance. Node1 has 1967 MB RAM
   and 37 GB disk free; node2 is the tighter resource boundary.
3. Obtain explicit founder authorization identifying the reviewed artifact SHA,
   permitted TLS/container preparation, rehearsal, and DNS window. CI/review is not
   deployment authorization. Preserve exact-SHA review and applicable Pilot CI gates.
4. Back up live Caddy files and inspect the actual Docker mounts and network on each
   node. Issue distinct DNS-01 certificates **before** changing www A/CNAME records.
5. Validate candidates, then complete merged Caddy files; activate only www changes
   under the authorization. Prove each origin with IP + SNI before DNS. The verifier's
   DNS gate will still fail at this stage; any divergence exception stays explicit.
6. Rehearse the non-production failure case. Only then perform §3, re-run §6 through
   cache expiry, record results, and stop for human acceptance.

Do not touch apex/node1/node2/test1/test2/app1/app2/explorer vhosts. Node1 apex
`punkto.xyz/mcp` must remain working throughout. No production services are stopped
for the drill.

## 3. Exact DNS change (authorized operator only)

Authoritative NS: `ns27.domaincontrol.com`. GoDaddy target:

| Action | Name | Type | Value | TTL |
|---|---|---|---|---|
| Delete | www | CNAME | app1.punkto.xyz | 3600 |
| Add | www | A | 46.101.118.157 | 600 |
| Add | www | A | 159.65.115.166 | 600 |

A CNAME and A records cannot coexist at www. **Apex, node1, node2, test1, test2,
app1, app2 and explorer are untouched.** In particular apex remains
46.101.118.157 TTL 600; node1 remains 46.101.118.157, node2 and test2 remain
159.65.115.166, TTL 600. Do not create app1 addresses to work around the breakage.

Use a non-recorded privileged shell, no tracing or verbose HTTP output. Read secrets
silently into variables; do not type values into command history. The helper sends
Authorization through stdin, not process arguments. Never log credentials.

```bash
set -euo pipefail
set +x
read -r -s -p 'GoDaddy key: ' GD_Key; printf '\n'
read -r -s -p 'GoDaddy secret: ' GD_Secret; printf '\n'
export GD_Key GD_Secret
# Reused for forward and rollback calls in this shell.
gd() {
    printf 'header = "Authorization: sso-key %s:%s"\n' "$GD_Key" "$GD_Secret" |
        curl --config - --fail-with-body --silent --show-error \
        --connect-timeout 10 --max-time 30 \
        -H 'Content-Type: application/json' "$@"
}
# Require success (no 401) before proceeding. Save record evidence securely.
gd https://api.godaddy.com/v1/domains/punkto.xyz > /tmp/www-domain-before.json
gd 'https://api.godaddy.com/v1/domains/punkto.xyz/records?type=A' > /tmp/www-a-before.json
gd https://api.godaddy.com/v1/domains/punkto.xyz/records/CNAME/www > /tmp/www-cname-before.json
# CUTOVER — only after TLS, direct-vhost, data and approval gates are satisfied.
gd -X DELETE https://api.godaddy.com/v1/domains/punkto.xyz/records/CNAME/www
gd -X PUT https://api.godaddy.com/v1/domains/punkto.xyz/records/A/www \
    --data '[{"data":"46.101.118.157","ttl":600},{"data":"159.65.115.166","ttl":600}]'
```

Stop on any API error. If PUT fails after DELETE, restore the original CNAME using
the rollback PUT below (first inspect whether any A records were installed). These
are type/name-scoped calls, never a whole-zone PUT. See GoDaddy's
[DELETE reference](https://developer.godaddy.com/en/docs/references/rest/domains/v1/record-delete-type-name).
Old CNAME caches can persist 3600 seconds, and negative caches for app1 may also
persist according to resolver/SOA policy. A new TTL 600 does not flush old caches.

Exact DNS rollback, using the same secret-safe `gd` helper:

```bash
gd -X DELETE https://api.godaddy.com/v1/domains/punkto.xyz/records/A/www
gd -X PUT https://api.godaddy.com/v1/domains/punkto.xyz/records/CNAME/www \
    --data '[{"data":"app1.punkto.xyz","ttl":3600}]'
unset GD_Key GD_Secret
```

This deletes both newly installed A records and restores the original CNAME. It
restores the **known-broken www baseline**, not a healthy www service. A different
repair requires a new founder decision; never silently change apex or app1.

## 4. TLS issuance plan

Use **DNS-01**. With two A records HTTP-01 or TLS-ALPN validation may hit either
origin, and independent challenge responders can fight over the same name. DNS-01
allows issuance before the address repair. Each node has its **own ACME account and
own private key**; never transfer account keys or certificate private keys between
nodes. Existing node1 acme.sh SAN cert expired 2026-07-24 and is not used by Caddy.
Node2 has no apex certificate; do not attempt to fix its apex/test1 issuance here.

On node1 use `/root/.acme.sh/acme.sh` and its existing `dnsapi/dns_gd.sh`. Refresh
GD_Key and GD_Secret securely as above; the saved credentials currently return 401.
On node2 install acme.sh (certbot currently has only nginx, standalone and webroot,
no DNS plugin). Review/pin an upstream revision before installation:

```bash
# node2 only, after authorization; founder/reviewer supplies the reviewed revision.
: "${ACME_SH_REV:?set reviewed acme.sh commit}"
: "${ACME_EMAIL:?set ACME contact email}"
git clone https://github.com/acmesh-official/acme.sh.git /root/acme.sh-src
git -C /root/acme.sh-src checkout --detach "$ACME_SH_REV"
(cd /root/acme.sh-src && ./acme.sh --install --home /root/.acme.sh --accountemail "$ACME_EMAIL")
test -f /root/.acme.sh/dnsapi/dns_gd.sh
```

On **each node separately**, with fresh exported GD_Key/GD_Secret, no debug mode and
no recorded shell, run (sequential initial issuance avoids competing TXT cleanup):

```bash
umask 077
: "${ACME_EMAIL:?set ACME contact email}"
/root/.acme.sh/acme.sh --register-account --server letsencrypt -m "$ACME_EMAIL"
/root/.acme.sh/acme.sh --issue --server letsencrypt --dns dns_gd \
    -d www.punkto.xyz --keylength ec-256
install -d -m 700 /root/punkto-www-tls
/root/.acme.sh/acme.sh --install-cert -d www.punkto.xyz --ecc \
    --key-file /root/punkto-www-tls/key.pem \
    --fullchain-file /root/punkto-www-tls/fullchain.pem
chmod 600 /root/punkto-www-tls/key.pem /root/.acme.sh/account.conf
unset GD_Key GD_Secret
```

Verify acme.sh account/domain private keys are also mode 600; keep all credentials
and private keys on their node, never in this repo or logs. Restrict account.conf
because dns_gd saves API credentials. Do not print it.

**Mount prerequisite:** the operator must inspect the live compose definition and
approve a node-local read-only directory bind
`/root/punkto-www-tls:/etc/caddy/www-tls:ro` for `punkto-web-1`. The audit does not
establish this mount exists. This PR changes no compose file and invents no live
compose path. If adding the mount needs container recreation, schedule it explicitly
with the founder; do not improvise or stop production to perform a drill. Confirm
Caddy's actual UID can read the directory and mode-600 key (set ownership to that
UID if needed). Mount the directory, not individual files, for renewed-file visibility.

Both candidates load their node-local issued certificate with this Caddy `tls`
directive (no automatic HTTP challenge issuer):

```caddyfile
tls /etc/caddy/www-tls/fullchain.pem /etc/caddy/www-tls/key.pem
```

After the merged live config is approved and its actual container mount path is
confirmed as `/etc/caddy/Caddyfile`, install the renewal hook on each node:

```bash
/root/.acme.sh/acme.sh --install-cert -d www.punkto.xyz --ecc \
    --key-file /root/punkto-www-tls/key.pem \
    --fullchain-file /root/punkto-www-tls/fullchain.pem \
    --reloadcmd 'docker exec punkto-web-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile'
```

This command also installs/reloads immediately: run only in the approved apply
window. If the live path differs, stop and correct the reviewed commands first.
Each node's own daily acme.sh cron renews its own cert and reruns install/reload;
verify `crontab -l`, successful hook execution and externally served expiry.
Stagger renewal schedules (for example node1 02:15 UTC, node2 03:45 UTC), monitor
failures and expiry, and avoid simultaneous manual DNS-01 operations. Never copy a
private key as a renewal fallback. See upstream
[acme.sh issuance and install guidance](https://github.com/acmesh-official/acme.sh).

## 5. Caddy vhost plan

Use [node1 candidate](../../deploy/candidate/www/node1.Caddyfile.www) and
[node2 candidate](../../deploy/candidate/www/node2.Caddyfile.www), following
[validation-only instructions](../../deploy/candidate/www/README.md).
On node1 replace only the complete `www.punkto.xyz` block currently containing
`redir https://punkto.xyz{uri} permanent`; on node2 replace only its www block
containing `redir https://punkto.xyz{uri}`. Redirecting to the node1-only apex would
collapse the round robin. Never replace the whole live file with a fragment.

Both candidates directly proxy `172.22.0.3:8000` on their own `punkti_edge` network:
node1 `punkto-app-1` (host 127.0.0.1:18080, `/opt/punkto/app`); node2
`punkto-test2-1` (host 127.0.0.1:18110, `/opt/punkto/v06-test2`). Both Caddy
containers are 172.22.0.2 on their separate hosts. Both node images have digest
`sha256:d4faaa49f6065917a87d465ff159a23135d330636c80b3b3b22ef259e4d2d965`.
The same private address therefore reaches different node-local data.

The **www write policy** refuses POST `/submit` and `/api/submit` with 403 on both
nodes, including operator/peer IPs. Node1 **apex** public submit remains open under
#35 phase 3. A client at www therefore cannot submit as it can at the apex.
Mesh POST `/push`, `/sync`, `/api/push`, `/api/sync` is 403 except for the sibling
(node1 allows 159.65.115.166; node2 allows 46.101.118.157). Use direct remote_ip,
not client-controlled forwarded headers. Route ordering places guards before proxies.

**MCP decision:** exact `/mcp` on both www origins proxies directly to
`https://punkto-mcp.sunebech.workers.dev`, overrides Host to that name, and uses
`flush_interval -1`. POSTs proxy directly without redirects; the read-only submit
policy does not disable MCP. Node1 apex MCP is untouched. Both candidates retain
nosniff, DENY, strict-origin-when-cross-origin, remove Server, and encode gzip.

After authorization, per node, first save the live file:

```bash
backup="$HOME/punkto/Caddyfile.before-www-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p "$HOME/punkto/Caddyfile" "$backup"
printf 'Record rollback backup: %s\n' "$backup"
cp -p "$HOME/punkto/Caddyfile" /tmp/Caddyfile.www-proposed
```

In `/tmp/Caddyfile.www-proposed`, replace just the www site block with that node's
candidate. Review `diff -u "$backup" /tmp/Caddyfile.www-proposed`; require only that
block to differ. Validate the full proposed file per README before applying. After
explicit authorization, copy its contents into the existing host file (preserving a
file bind-mount inode), validate again and reload:

```bash
cat /tmp/Caddyfile.www-proposed > "$HOME/punkto/Caddyfile"
docker exec punkto-web-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec punkto-web-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

If validation/reload fails, immediately restore §8; do not proceed to DNS.

## 6. Verification and exact expectations

Run [the read-only verifier](../../scripts/verify-www-roundrobin.sh):

```bash
scripts/verify-www-roundrobin.sh --help
WWW_HOST=www.punkto.xyz NODE1_IP=46.101.118.157 NODE2_IP=159.65.115.166 TIMEOUT=8 \
    scripts/verify-www-roundrobin.sh
```

It uses `openssl s_client -connect IP:443 -servername www.punkto.xyz
-verify_hostname www.punkto.xyz -verify_return_error`, and curl
`--resolve www.punkto.xyz:443:IP` for **each** IP, with no TLS bypass, redirect
following or environmental HTTP proxy. Each operation has a timeout. Temporary
response files are removed. Malformed one-byte JSON `{` POSTs cannot create records.

Expected successful lines for each `nodeN (IP)`:

- `PASS ... TLS handshake, trusted chain and hostname`
- `PASS ... certificate SAN covers www.punkto.xyz`
- `PASS ... certificate expiry notAfter=...` (actual future expiry is printed)
- `PASS ... GET / HTTP 200`, `/ai HTTP 200`, `/publication/root.json HTTP 200`,
  `/nodes.json HTTP 200`, `/health HTTP 200`, `/mcp HTTP 405`
- `PASS ... POST /submit HTTP 403 (malformed probe)` and `/api/submit HTTP 403`
- `PASS body parity / identical`, `/ai identical`, `/health identical`
- `PASS publication heads: node1: head=... seq=...; node2: head=... seq=... (converged)`
- For each 1.1.1.1, 8.8.8.8, 9.9.9.9:
  `PASS resolver IP target topology A=['159.65.115.166', '46.101.118.157'] CNAME=[]`
- Fully green: `SUMMARY PASS=29 FAIL=0`, exit 0. Any hard failure exits 1.

Current pre-cutover execution must print FAIL for TLS/HTTP gates and DNS topology,
with unavailable parity/chain checks also FAIL; it must complete rather than crash.
A transport failure proves only this runner could not verify that gate, not its cause.
Do not claim convergence from missing bodies or identical error pages.

Today node1 head is
`c77ba862be21e00d37bdc62f35bac7359d09698d19cd4ef8b2ce5be33ff0a9e5` seq 14;
node2 is `392bab1513f4708c6de96a193b418c9cce59e834dc5748e0d066de9a657c71e0`
seq 16. All 15 record files match, but chains have 14 vs 16 manifests and only
seq-1 `51237e65…` is shared: **different signed publication states**. The verifier
reports head/seq divergence as FAIL, even with a recorded founder exception; keep
that exception beside the output, never relabel it PASS. `/nodes.json` 433 vs 396
bytes differs in the advertised submit URL; its status check does not assert byte parity.

Resolver spread is an RRset check, not proof of 50/50 client traffic. Also check:

```bash
dig @ns27.domaincontrol.com www.punkto.xyz A +noall +answer
dig @ns27.domaincontrol.com www.punkto.xyz CNAME +noall +answer
curl --noproxy '*' --max-time 8 --resolve punkto.xyz:443:46.101.118.157 \
    -o /dev/null -w '%{http_code}\n' https://punkto.xyz/mcp
```

Expect two A records TTL 600 authoritatively and no CNAME after cutover; apex MCP
remains 405 for GET. Inspect apex `/` and `/health` (200), normal www browser
navigation and console on each forced origin, and record SHA, host, time and evidence.
No browser/manual live acceptance is performed by this review-only PR.

## 7. Negative / non-production drill

After separate authorization, use test2 as the healthy reference and a spare
loopback HTTP origin on an operator workstation. No DNS changes, no production
service stops, no writes to test2:

```bash
curl --noproxy '*' --max-time 8 --resolve test2.punkto.xyz:443:159.65.115.166 \
    -o /dev/null -w 'test2 HTTP %{http_code}\n' https://test2.punkto.xyz/health
# In a separate terminal, serve an empty temporary directory on loopback only.
drill_dir=$(mktemp -d)
python3 -m http.server 18958 --bind 127.0.0.1 --directory "$drill_dir"
# In the first terminal:
curl --noproxy '*' --max-time 3 -o /dev/null -w 'local HTTP %{http_code}\n' http://127.0.0.1:18958/
```

Expect test2 200 and local 200. Ctrl-C **only the foreground loopback Python
process** in the second terminal, then repeat both curls: local fails (curl nonzero,
HTTP 000), test2 stays 200. Repeating the failed local request demonstrates a client
pinned to a dead address does not magically fail over; explicitly selecting the
healthy test2 origin succeeds. Remove the empty drill directory afterward. This is
a controlled model of cached origin selection, not a claim to measure public DNS
balancing or browser retry behavior. Never stop node1/node2, their Caddy, or test2.

## 8. Rollback

1. Record failure and stop forward changes. Execute §3's scoped DNS rollback. Verify
   authoritative and public resolver CNAME `app1.punkto.xyz.` and absence of direct
   www A records after caches expire. This intentionally restores broken www.
2. On each changed node, use its recorded backup (never the repo deploy copy):

   ```bash
   : "${backup:?set the recorded absolute backup path for this node}"
   cat "$backup" > "$HOME/punkto/Caddyfile"
   docker exec punkto-web-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   docker exec punkto-web-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
   ```

3. Confirm node1 apex `/` and `/health` 200 and `/mcp` 405 using forced SNI/IP,
   node2 test2 `/` and `/health` 200, and unchanged node/explorer/staging routes.
   Verify `docker compose ps` in the operator-confirmed live projects and inspect
   logs without secrets. These existing surfaces should be healthy; www will not be.
4. Keep new certs securely in place for diagnosis; do not purge stores. Reverting
   any separately approved mount preparation needs its own reviewed operational
   procedure. Record rollback time, DNS observations, backup paths and results;
   return to founder review before any further repair.

## 9. Limitations

DNS round robin provides **no automatic failover** and **no guaranteed 50/50 split**.
Clients/resolvers cache and may choose a failed node until expiry or retry; some
will not retry the other address. A health-checked edge is a later milestone.
Independent signed states, discovery differences, canary approval, node2 capacity
and renewal reliability remain real gates even when HTTP shape matches. The audit
found no websocket, cookie, session or Authorization logic in the PWA/node app, so
reads are interchangeable at the transport level, not necessarily signed-content
identical. This runbook authorizes nothing by itself.
