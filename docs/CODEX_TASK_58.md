# CODEX TASK 58 — `www.punkto.xyz` two-node round-robin readiness (review-only artifacts)

**Status:** ACTIVE
**Base:** `main` (branch `feat/issue58-www-round-robin`)
**Source of truth:** CEO-OS Issue #58 — https://github.com/Fisker1111/CEO-OS/issues/58
**Role:** Codex is the implementation engineer. Produce **review-only** artifacts.
**Deploy:** NOT authorized. Do not touch any server, DNS, container, or TLS store.

---

## 0. Goal

Produce the Phase-B review-only package for the founder's staged GoDaddy cutover of
`www.punkto.xyz` to DNS round robin over node1 + node2:

1. An exact operator runbook (read-then-apply, ordered, with rollback).
2. Exact candidate Caddy vhost artifacts for both nodes (files in the repo, **not** applied).
3. A read-only verification script that proves each origin independently by IP + SNI.
4. A CI-checkable lint that guards the candidate artifacts against regressions.

The Founder has **not** authorized the cutover. Nothing in this PR may be executed
against production by anyone without a separate explicit founder authorization.

---

## 1. Facts you must build on (verified 2026-11-10, read-only audit)

Do **not** re-derive these; do not contradict them in the runbook. If you believe one is
wrong, stop and report the counterexample instead of writing around it.

### 1.1 DNS (authoritative NS `ns27.domaincontrol.com`, GoDaddy)

| Name | Type | Value | TTL |
|---|---|---|---|
| `punkto.xyz` (apex) | A | `46.101.118.157` (node1) | 600 |
| `node1.punkto.xyz` | A | `46.101.118.157` | 600 |
| `node2.punkto.xyz` | A | `159.65.115.166` | 600 |
| `test2.punkto.xyz` | A | `159.65.115.166` | 600 |
| `www.punkto.xyz` | **CNAME** | `app1.punkto.xyz` | 3600 |
| `app1.punkto.xyz` | **none** | no A, no AAAA, no CNAME | — |

**Consequence:** `www.punkto.xyz` does not resolve today on 1.1.1.1 / 8.8.8.8 / 9.9.9.9,
because the CNAME target `app1.punkto.xyz` has no address record. `www` is currently
broken/unreachable, not merely "not yet migrated". The target change is therefore a
repair, not a live-traffic migration.

**Founder-mandated target DNS (NOT yet authorized to apply):**

- remove the `www` CNAME (a CNAME and an A record cannot coexist at the same name);
- add `www` A `46.101.118.157` (node1) TTL 600;
- add `www` A `159.65.115.166` (node2) TTL 600;
- **no** change to apex, `node1`, `node2`, `test1`, `test2`, `app1`, `app2`, `explorer`.

### 1.2 TLS state

- Neither node holds a usable `www.punkto.xyz` certificate.
- node1 Caddy ACME log (staging CA in one attempt set, prod CA in the other) fails for
  `www.punkto.xyz` **and** `app1.punkto.xyz` with
  `urn:ietf:params:acme:error:dns — no valid A records found for <name>`.
  The failure cause is DNS, not the ACME method.
- node1 Caddy cert store holds only: `explorer.punkto.xyz`, `node1.punkto.xyz`,
  `punkto.xyz`, `test1.punkto.xyz`.
- node2 Caddy cert store holds only: `explorer.punkto.xyz`, `node2.punkto.xyz`,
  `sunebech.com`, `www.sunebech.com`, `test2.punkto.xyz`.
- node2 has **no apex `punkto.xyz` certificate** and its ACME attempts for `punkto.xyz`
  and `test1.punkto.xyz` fail because those names point at node1
  (`46.101.118.157: Invalid response ... 404`, `tls: internal error`).
- node1 has an **acme.sh** install at `/root/.acme.sh` with a GoDaddy DNS API plugin
  (`dnsapi/dns_gd.sh`) and `SAVED_GD_Key` / `SAVED_GD_Secret` in `account.conf`.
  Its historic `punkto.xyz` cert (SAN `punkto.xyz`, `www.punkto.xyz`, `app1.punkto.xyz`)
  expired **2026-07-24** and is not used by Caddy.
- **The saved GoDaddy API credentials currently return HTTP 401** on
  `GET https://api.godaddy.com/v1/domains/punkto.xyz` and on
  `GET .../records?type=A`. DNS-01 automation is therefore blocked until the Founder
  refreshes them. node2 has no GoDaddy credentials at all.
- node2 has `certbot` but **only the `nginx`, `standalone` and `webroot` plugins** — no
  DNS plugin — so DNS-01 on node2 needs either a plugin install or acme.sh.

### 1.3 Live Caddy vhosts (host files, NOT in the image; both drifted from repo `deploy/` copies)

**node1 `~/punkto/Caddyfile`** (Caddy v2.11.4, container `punkto-web-1`):
- `punkto.xyz` → `reverse_proxy 172.22.0.3:8000` (the v0.6 node `punkto-app-1` on the
  `punkti_edge` network), plus exact-path `@mcp path /mcp` proxy to
  `https://punkto-mcp.sunebech.workers.dev`, plus a `@push_write` guard that 403s
  `POST /push|/sync|/api/push|/api/sync` from anyone but `159.65.115.166`.
  `POST /submit` and `POST /api/submit` are publicly OPEN (CEO-OS #35 phase 3).
- `www.punkto.xyz` → `redir https://punkto.xyz{uri} permanent`  ← **redirect only**
- `app1.punkto.xyz`, `node1.punkto.xyz` → legacy `/srv` static tree + legacy relay/atoms
- `test1.punkto.xyz` → `/srv-punkto-world` staging

**node2 `~/punkto/Caddyfile`** (Caddy v2.11.4, container `punkto-web-1`):
- `punkto.xyz` → `root * /srv-punkto-v1` legacy World v1 static site + legacy relay/atoms
  (node2's apex is **legacy v1 content, not v0.6**)
- `www.punkto.xyz` → `redir https://punkto.xyz{uri}`  ← redirect to the legacy apex
- `test2.punkto.xyz` → `reverse_proxy 172.22.0.3:8000` = node2's own v0.6 node
  `punkto-test2-1`, with a `@submit_write` guard 403ing `POST /submit|/api/submit`
  from anyone outside `46.101.199.234 46.101.118.157 159.65.115.166`, and a
  `@push_write` guard 403ing `POST /push|/sync|/api/push|/api/sync` from anyone but
  `46.101.118.157`.
- `node2.punkto.xyz`, `app2.punkto.xyz` → legacy `/srv`; `explorer`, `test1` → legacy.

**Design consequence:** the current `www` design is a redirect to the apex, and the
apex is node1-only for `punkto.xyz`. A redirect-based `www` therefore *cannot* deliver
"round robin between node1 and node2" — the second hop always lands on node1. For
`www` to be a true round robin, each node must **serve the `www` vhost directly from
its own node-local v0.6 origin**, not redirect.

### 1.4 Node-local v0.6 origins (both nodes run the same digest)

- node1: container `punkto-app-1`, image
  `ghcr.io/fisker1111/punkto@sha256:d4faaa49f6065917a87d465ff159a23135d330636c80b3b3b22ef259e4d2d965`,
  published on `127.0.0.1:18080`, compose project `/opt/punkto/app`
  (config `/opt/punkto/app/config.yml`, data `/opt/punkto/app/data`).
- node2: container `punkto-test2-1`, **same image digest**, published on `127.0.0.1:18110`,
  compose project `/opt/punkto/v06-test2` (config `/opt/punkto/v06-test2/config.yml`,
  data `/opt/punkto/v06-test2/data`).
- Both Caddy containers are on `punkti_edge` at `172.22.0.2`; both v0.6 node containers
  are on `punkti_edge` at `172.22.0.3`. So `reverse_proxy 172.22.0.3:8000` is valid on
  either node, and it always reaches that node's own local data. This is how each
  `www` origin stays independent of the other node.

### 1.5 Measured parity (2026-11-10)

Served bytes compared origin-to-origin (`--resolve` per IP, correct SNI):

| Path | node1 apex | node2 `test2` | Result |
|---|---|---|---|
| `/` | 200, 86209 B | 200, 86209 B | byte-identical |
| `/ai` | 200, 5834 B | 200, 5834 B | byte-identical |
| `/health` | 200, 59 B | 200, 59 B | byte-identical |
| `/publication/root.json` | 200 | 200 | **DIFFERENT** |
| `/nodes.json` | 433 B | 396 B | **DIFFERENT** |

`/publication/root.json`:
- node1: `{"head":"c77ba862be21e00d37bdc62f35bac7359d09698d19cd4ef8b2ce5be33ff0a9e5","seq":14,"v":"punkti/pub/0.6"}`
- node2: `{"head":"392bab1513f4708c6de96a193b418c9cce59e834dc5748e0d066de9a657c71e0","seq":16,"v":"punkti/pub/0.6"}`

Publication record sets are byte-identical: 15 record files on each node, all 15 sha256
matches. But the published **chains differ**: node1 has 14 manifests ending at seq 14,
node2 has 16 manifests ending at seq 16, and only the seq-1 manifest
(`51237e65…`) is shared. So the two nodes currently publish **different signed
publication states** over the same record set.

`/nodes.json` differs only in the advertised submit URL for `punkto-xyz`
(node1 advertises `https://punkto.xyz/submit`; node2 does not).

Also measured:
- `GET /mcp` → node1 apex 405 (exact-path proxy is live), node2 `test2` 404 (**no `/mcp`**).
- `POST /submit` and `POST /api/submit` → node1 apex 400 with a malformed body (the
  write path is reachable, i.e. publicly open); node2 `test2` 400 too (its own guard
  admits the operator IP range, which includes the audit egress `46.101.199.234`).
- `POST /push` / `/sync` → 403 on both (mesh peer surface closed to the public).
- No websocket, cookie, session or Authorization logic exists in the PWA or node app;
  reads are therefore interchangeable across origins.

### 1.6 Capacity

- node1: 1 vCPU, 1967 MB RAM, 48 GB disk (37 GB free).
- node2: 1 vCPU, **961 MB RAM (409 MB available)**, 24 GB disk (14 GB free), no swap.
  node2 also still runs the legacy relay/atoms containers.

### 1.7 Relations to other work

- CEO-OS #57 / Punkto PR #151 (`feat/issue57-two-node-parity`) adds static-first
  bidirectional replication and is **review-only, not merged**. It is the mechanism
  expected to make the two publication chains converge. This PR must not duplicate or
  modify that work, and must not assume it is merged.
- `punkto.xyz/mcp` is live on node1 only (CEO-OS #56) and **must keep working**.
  Do not propose removing or weakening it.

---

## 2. Deliverables (all new files; no existing file may be modified except as noted)

### 2.1 `docs/operator/www-round-robin-runbook.md`

The founder-facing runbook. Required structure:

1. **Readiness summary + go/no-go** — state the current verdict (from §1) as a table
   with one row per gate, each row marked PASS / FAIL / BLOCKED, with the evidence
   reference. Make clear that the DNS cutover is **not** authorized by this document.
2. **Preconditions** — the founder must supply: refreshed GoDaddy API credentials
   (currently 401), the decision on whether node2's `www` origin may serve the
   `test2` canary dataset, and the acceptance of the publication-chain divergence
   (or a merged PR #151 that fixes it).
3. **Exact DNS change** — the literal record table to apply (from §1.1), the API
   calls to remove the `www` CNAME and add the two A records with TTL 600, and the
   explicit statement that apex/`node1`/`node2`/`test1`/`test2`/`app1`/`app2`/
   `explorer` are untouched. Include the exact rollback (re-add the CNAME to
   `app1.punkto.xyz`, delete the two A records).
4. **TLS issuance plan** — per node, with one node's own ACME account and its own
   private key (do **not** propose sharing one private key between nodes). Cover:
   - why HTTP-01 / TLS-ALPN is unsafe with two A records at one name (the CA may
     validate against either origin, and the two nodes would fight over the same
     challenge) and therefore **DNS-01 is the recommended method**;
   - node1: acme.sh is already installed with the GoDaddy DNS plugin, but the saved
     credentials 401 — the founder must refresh them, then the runbook gives the
     exact acme.sh DNS-01 command for `www.punkto.xyz` and the Caddy
     `tls` block that loads the issued certificate;
   - node2: acme.sh install + GoDaddy DNS plugin + its own key, or a certbot DNS
     plugin install; Caddy `tls` block for its own issued certificate;
   - renewal: each node renews its own certificate autonomously, and what the
     renewal hook should do (reload Caddy after install);
   - secrets: keys stay on the node, mode 600, never in the repo, never in logs.
5. **Caddy vhost plan** — reference the two candidate files (§2.2) and explain, per
   node, exactly which block replaces today's `www` redirect and why the redirect must
   go. Explain the `www` write policy (§3.3) and the `/mcp` consistency decision (§3.4).
6. **Verification** — reference the script (§2.3) and give the exact expected outputs
   for each check, including the SNI-per-IP probes and the resolver spread check.
7. **Negative / non-production drill** — how to prove the round robin behaves when one
   origin is unavailable **without** taking production down: use the `test2` host and a
   spare loopback origin, never by stopping the production node.
8. **Rollback** — DNS rollback, per-node Caddy rollback to the saved `Caddyfile`
   backup, and how to confirm the site is healthy again.
9. **Limitations** — DNS round robin provides **no automatic failover** and **no
   guaranteed 50/50 split**; a health-checked edge is a later milestone. State this in
   the founder-facing text, not only in a footnote.

### 2.2 Candidate Caddy artifacts (new files, never applied)

- `deploy/candidate/www/node1.Caddyfile.www` — the complete candidate `www.punkto.xyz`
  site block for node1, plus a short header comment stating it is a **candidate for
  founder approval**, the target it proxies to, and the live file it would replace.
- `deploy/candidate/www/node2.Caddyfile.www` — the same for node2.
- `deploy/candidate/www/README.md` — how to load a candidate into the container for
  **validation only** (`docker cp` + `docker exec … caddy validate --config /tmp/…`),
  and the explicit statement that the live `~/punkto/Caddyfile` is not to be edited by
  this PR.

Both candidate blocks must:
- serve `www.punkto.xyz` **directly** from that node's own v0.6 origin
  (`reverse_proxy 172.22.0.3:8000` on `punkti_edge`) — no redirect to the apex;
- keep the mesh peer surface closed (`POST /push|/sync|/api/push|/api/sync` → 403 for
  anyone but the sibling node IP);
- apply the write policy from §3.3;
- apply the `/mcp` decision from §3.4;
- carry the same security headers the live production block uses
  (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, `-Server`) and `encode gzip`;
- not contain any secret, key path outside the node, or credential.

### 2.3 `scripts/verify-www-roundrobin.sh`

A **read-only** verification script (no mutation of any kind). Requirements:

- `set -euo pipefail`; a `usage`/help mode; all targets overridable by env vars
  (`WWW_HOST`, `NODE1_IP`, `NODE2_IP`, `TIMEOUT`).
- For each origin IP, with correct SNI, check: TLS handshake and certificate SAN +
  expiry; HTTP status for `/`, `/ai`, `/publication/root.json`, `/nodes.json`,
  `/health`, `/mcp`; byte-compare the response bodies of the two origins for
  `/`, `/ai` and `/health` and report identical/different per path; compare
  `/publication/root.json` `head`/`seq` and report the chain divergence explicitly.
- Check the public resolver view of `www.punkto.xyz` (A records and CNAME) and report
  whether it matches the target topology.
- Check that `POST /submit` and `POST /api/submit` are refused on the `www` origins
  (the script must use a deliberately malformed, tiny body so no record can be
  created, and must state that in `--help`).
- Print a PASS/FAIL line per check and a final summary; exit non-zero if a hard check
  fails. Read-only: it must never `docker restart/stop`, never write to a config path,
  never issue DNS changes.
- The script must run against the **current** (pre-cutover) state and report the
  known-failing gates as FAIL rather than crashing or hanging.

### 2.4 CI lint for the candidate artifacts

- `scripts/lint_www_candidate.py` (stdlib only, no pytest) — checks:
  - both candidate files exist and are non-empty;
  - each candidate contains exactly one `www.punkto.xyz` site block;
  - each candidate does **not** contain a `redir`/`redir` redirect to the apex;
  - each candidate contains `reverse_proxy 172.22.0.3:8000`;
  - each candidate contains the `/mcp` handling required by §3.4 and the push-write
    403 guard;
  - each candidate contains the four security headers;
  - the runbook file exists and mentions the exact target A records, the DNS-01
    method, the rollback, and the no-automatic-failover limitation;
  - the verify script exists, is executable, and passes `bash -n`.
  Exit non-zero with a precise message on any failure.
- A **new** workflow file `.github/workflows/www-roundrobin-lint.yml` that runs this
  lint on pull requests. Do **not** edit `.github/workflows/pilot-ci.yml` — PR #151 is
  concurrently editing that file and the two must not collide.

### 2.5 `docs/CODEX_TASK_58.md` (this file)

Keep it. Do not rewrite it.

---

## 3. Design decisions you must implement exactly

These are decided. Do not re-litigate them; do not substitute your own.

### 3.1 `www` must be served, not redirected

Each node serves `www.punkto.xyz` from its **own** node-local v0.6 origin via
`reverse_proxy 172.22.0.3:8000` on the `punkti_edge` network. Today's
`redir https://punkto.xyz{uri}` must be removed from the `www` block, because the
apex resolves to node1 only and a redirect would collapse the round robin onto node1.

### 3.2 `www` is a read-only interface on both nodes

`www` is the public read surface. On **both** nodes the `www` vhost must refuse the
public write surface with `403` for `POST /submit` and `POST /api/submit`, so the two
origins behave identically regardless of which one answers. The existing public write
availability of the **apex** `punkto.xyz` on node1 (CEO-OS #35 phase 3) is **not**
changed by this PR — `www` is a separate vhost with its own policy. State this
distinction explicitly in the runbook, because it changes what a client can do when it
lands on node2 instead of node1.

### 3.3 `/mcp` consistency

`/mcp` must behave the **same** on both `www` origins, using the same exact-path
proxy the apex uses on node1 (`@mcp path /mcp` →
`reverse_proxy @mcp https://punkto-mcp.sunebech.workers.dev` with
`header_up Host punkto-mcp.sunebech.workers.dev` and `flush_interval -1`, proxying
POSTs directly with no redirect). Add the same block to the node2 `www` candidate so
that a `www` client gets the same MCP surface whichever origin answers. The existing
apex `/mcp` on node1 is untouched and must keep working.

### 3.4 Divergence must be surfaced, not hidden

The runbook must state, in the go/no-go table and in the verification section, that
today the two origins publish **different signed publication states** (node1 head
`c77ba862…` seq 14; node2 head `392bab15…` seq 16) even though the 15 record files
are byte-identical, and that identical HTTP shape is **not** identical signed content.
Recommendation: do not cut over until this is resolved — either by landing/reviewing
PR #151 so the chains converge, or by an explicit founder decision to accept a
round robin that serves two different publication heads.

### 3.5 TLS: DNS-01, per-node keys, no shared private key

Do not propose a shared certificate/private key between node1 and node2. Do not rely on
HTTP-01 or TLS-ALPN for `www` once it has two A records, because the CA's validation
can land on either origin. See §2.1 item 4.

### 3.6 Non-production drill only

The "one origin down" proof must be rehearsed against `test2` / a local origin, never
by stopping the production node1 or node2 service.

---

## 4. Scope boundaries (hard)

**Allowed:** new files under `docs/`, `deploy/candidate/`, `scripts/`, and a new
workflow file.

**Forbidden:**
- editing `pwa/**`, `node/**`, `punkti_node/**`, `relay/**`, `core/**`,
  `deploy/node1/Caddyfile`, `deploy/node2/Caddyfile`, `deploy/docker-compose.yml`,
  `.github/workflows/pilot-ci.yml`, or any other existing file;
- any change to a live server, DNS zone, container, cert store or TLS store;
- committing any secret, key, password, token or credential (including GoDaddy
  credentials) — refer to them by variable name only;
- merging, deploying, or pushing to `main`;
- duplicating PR #151's replication work.

## 5. Acceptance criteria

1. All files in §2.1–§2.4 exist, are internally consistent, and every fact they state
   matches §1.
2. `bash -n scripts/verify-www-roundrobin.sh` exits 0.
3. `python3 scripts/lint_www_candidate.py` exits 0.
4. Running `scripts/verify-www-roundrobin.sh` against the **current** pre-cutover
   state completes without hanging, prints a PASS/FAIL line per check, and exits
   non-zero because the pre-cutover gates fail (the `www` name does not resolve and no
   `www` certificate exists). Paste that output in your report — it is the proof the
   script is real.
5. No existing file in the repository is modified (`git status --porcelain` shows only
   the new paths).
6. `git diff --check` is clean.

## 6. Stop condition

When the acceptance criteria pass, **stop** and report:

- the exact list of files added;
- the exact commands you ran and their real output (especially items 2–4 above);
- the go/no-go verdict you wrote into the runbook and the gates that are still FAIL or
  BLOCKED;
- the SHA of the commit you created.

Do **not** push, do **not** open a PR, do **not** merge. The orchestrator pushes and
opens the PR.
