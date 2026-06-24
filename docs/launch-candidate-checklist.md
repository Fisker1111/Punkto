# Launch Candidate Checklist

> **Purpose:** Final public-alpha readiness checklist before inviting testers or doing soft marketing.
>
> **Status:** Draft — this document defines the checks required before declaring Punkto ready for public alpha. Each check should be verified manually or by running the referenced tool/script.

---

## 1. Runtime Health

| # | Check | Method | Required | Status |
|---|-------|--------|----------|--------|
| 1.1 | node1 passes node doctor | `python scripts/node-doctor.py https://node1.punkto.xyz` | Required | ⬜ |
| 1.2 | node2 passes node doctor | `python scripts/node-doctor.py https://node2.punkto.xyz` | Required | ⬜ |
| 1.3 | `/health` returns ok | `curl https://node1.punkto.xyz/health` → `{"status":"ok"}` | Required | ⬜ |
| 1.4 | `/node/info` shows `config_loaded=true` | `curl https://node1.punkto.xyz/node/info` → verify key fields | Required | ⬜ |
| 1.5 | `/status` public, no secrets | Browse `/status` — no private_key, no secrets.env, no internals | Required | ⬜ |
| 1.6 | `/feed` returns valid atom list | `curl https://node1.punkto.xyz/feed` → valid JSON array | Required | ⬜ |
| 1.7 | App marker visible | Browse `app1.punkto.xyz` and `app2.punkto.xyz` — console shows version marker | Required | ⬜ |

## 2. Storage

| # | Check | Method | Required | Status |
|---|-------|--------|----------|--------|
| 2.1 | Append-only atom log exists on disk | SSH to node: `ls -la data/atoms.log.jsonl` | Required | ⬜ |
| 2.2 | Accepted atom survives relay restart | `docker compose restart` then `curl /feed` — atom still present | Required | ⬜ |
| 2.3 | Duplicate `atom_id` is deduplicated | Submit same atom twice — second rejected or idempotent | Required | ⬜ |
| 2.4 | Corrupt log line does not crash relay | Inject bad line into `atoms.log.jsonl`, restart — relay starts, skips bad line | Nice | ⬜ |

## 3. Live-Forward Policy

| # | Check | Method | Required | Status |
|---|-------|--------|----------|--------|
| 3.1 | `accept_recent_hours=24` | Verify in config or `/node/info` | Required | ⬜ |
| 3.2 | `serve_recent_hours=24` | Verify in config or `/node/info` | Required | ⬜ |
| 3.3 | Old atom (>24h) rejected | Submit atom with timestamp >24h old → rejected | Required | ⬜ |
| 3.4 | `serve_archive=false` | Verify in config or `/node/info` | Required | ⬜ |
| 3.5 | `serve_pinned=true` | Verify in config or `/node/info` | Required | ⬜ |

## 4. Backup / Restore

| # | Check | Method | Required | Status |
|---|-------|--------|----------|--------|
| 4.1 | Backup script works | `./scripts/backup-node.sh --output ./backups` → creates `.tar.gz` | Required | ⬜ |
| 4.2 | Restore script works | `./scripts/restore-node.sh <backup.tar.gz>` → files restored | Required | ⬜ |
| 4.3 | Node identity preserved after restore | Compare `node_id`/`fingerprint` before/after restore | Required | ⬜ |
| 4.4 | Feed restored after restore | `curl /feed` shows same atoms before/after restore | Required | ⬜ |
| 4.5 | Secrets excluded by default | Script does not include `.env` or secrets without `--include-secrets` | Required | ⬜ |

## 5. Fresh Install

| # | Check | Method | Required | Status |
|---|-------|--------|----------|--------|
| 5.1 | Fresh Ubuntu install guide exists | `docs/fresh-install-ubuntu.md` is present and complete | Required | ⬜ |
| 5.2 | Clean VM validation (manual) | Follow guide on clean Ubuntu 24.04 VM — all steps work end-to-end | Required | ⬜ |
| 5.3 | Node doctor passes after install | `python scripts/node-doctor.py <node-url>` after fresh install | Required | ⬜ |
| 5.4 | First atom test works | `curl -X POST /atom` with valid payload returns 201 | Required | ⬜ |

## 6. API / Docs

| # | Check | Method | Required | Status |
|---|-------|--------|----------|--------|
| 6.1 | Public API docs complete | `docs/public-api.md` covers all 9 endpoints | Required | ⬜ |
| 6.2 | IP-first bootstrap docs complete | `docs/ip-first-bootstrap.md` defines DNS-free operation | Required | ⬜ |
| 6.3 | Cache/Cloudflare policy complete | `docs/cache-cloudflare.md` defines cache rules | Required | ⬜ |
| 6.4 | Backup/restore docs complete | `docs/backup-restore.md` covers full procedure | Required | ⬜ |
| 6.5 | Fresh install docs complete | `docs/fresh-install-ubuntu.md` covers full procedure | Required | ⬜ |
| 6.6 | Node doctor documented | `scripts/node-doctor.py` has usage help or README reference | Nice | ⬜ |

## 7. Security / Public Warnings

| # | Check | Method | Required | Status |
|---|-------|--------|----------|--------|
| 7.1 | Punkto is public | Documentation states atoms are publicly readable | Required | ⬜ |
| 7.2 | Do not post secrets | Documentation warns users not to post secrets | Required | ⬜ |
| 7.3 | Signing gives authorship, not privacy | Documentation explains signature ≠ encryption | Required | ⬜ |
| 7.4 | No private_key/secrets in public endpoints | Verify `/node/info`, `/status`, `/feed` — no key material | Required | ⬜ |
| 7.5 | Admin remains SSH/operator-side | No admin API — management is SSH-only | Required | ⬜ |
| 7.6 | Node doctor does not expose secrets | `node-doctor.py` output reviewed — no secrets in report | Required | ⬜ |
| 7.7 | CORS configured safely | Verify CORS headers — not wide-open unless intended | Nice | ⬜ |

## 8. Launch Decision Statuses

| Status | Meaning |
|--------|---------|
| **Required before public alpha** | Must pass before inviting external testers or marketing |
| **Nice before public alpha** | Should be addressed but not a blocker |
| **Later** | Deferred to post-alpha roadmap |

### Summary

| Section | Required | Nice | Status |
|---------|----------|------|--------|
| 1. Runtime Health | 7 | 0 | ⬜ |
| 2. Storage | 3 | 1 | ⬜ |
| 3. Live-Forward Policy | 5 | 0 | ⬜ |
| 4. Backup / Restore | 5 | 0 | ⬜ |
| 5. Fresh Install | 4 | 0 | ⬜ |
| 6. API / Docs | 5 | 1 | ⬜ |
| 7. Security / Warnings | 6 | 1 | ⬜ |
| **Total** | **35** | **3** | ⬜ |

### Decision

- [ ] **All required checks pass** → Proceed to public alpha
- [ ] **Some required checks fail** → Fix before alpha
- [ ] **Critical security checks fail** → Block immediately

---

*Last updated: 2026-06-22*

---

## Canary Deploy Evidence — node2 (2026-06-22)

**Canary deploy of HEAD `596e746` to node2 only (159.65.115.166).**

### Pre-deploy state recorded

| Item | Value |
|---|---|
| Fingerprint | `node:0b2af9b3ca1d` |
| Atom count | 4 |
| Relay image | `ghcr.io/fisker1111/punkto-relay:latest` (sha256:cdf61fb9...) |
| Web image | `ghcr.io/fisker1111/punkto-web:latest` (sha256:30b5f191...) |
| Backup | `~/punkto/backups/punkto-node-backup-20260622T125011Z.tar.gz` |
| Extra backup | `~/punkto/backups/canary-20260622T125009Z/` (.env, Caddyfile, compose, inspect) |

### Verification results

| # | Check | Result | Evidence |
|---|---|---|---|
| 1.3 | `/health` returns ok | ✅ PASS | HTTP 200, `{"status":"ok"}` |
| 1.4 | `/node/info` config_loaded=true | ✅ PASS | `config_loaded: True` |
| 1.5 | `/status` no secrets | ✅ PASS | No private_key/secrets exposed |
| 1.6 | `/feed` valid JSON | ✅ PASS | `['atoms', 'cursor']` |
| 1.7 | App marker visible | ✅ PASS | `PUNKTO_APP_VERSION = 'v107-...'` in deployed app.js |
| 3.1 | `accept_recent_hours=24` | ✅ PASS | Verified via /node/info |
| 3.2 | `serve_recent_hours=24` | ✅ PASS | Verified via /node/info |
| 3.4 | `serve_archive=false` | ✅ PASS | Verified via /node/info |
| 7.4 | No private_key in public endpoints | ✅ PASS | /node/info, /status, /feed clean |
| 7.7 | CORS configured | ✅ PASS | `Access-Control-Allow-Origin "*"` (intentional) |
| — | Fingerprint unchanged | ✅ PASS | `node:0b2af9b3ca1d` matches pre-deploy |
| — | Atoms preserved | ✅ PASS | 66 lines in /data/atoms.log.jsonl |
| — | TLS valid | ✅ PASS | `verify return:1`, CN=node2.punkto.xyz |
| — | Unsigned atom rejected | ✅ PASS | HTTP 403 `missing_sig` |
| — | Valid signed atom accepted | ✅ PASS | HTTP 201 `accepted` |
| — | First-use warning works | ✅ PASS | Ack-banner visible, Place here disabled until ack |
| — | PWA can create signed atom | ❌ **FAIL** | `Error: atom missing required field 'sig'` — `submitAtomFromModal` doesn't call `signAtom` |
| — | Node doctor | ✅ PASS | Both warnings are known false positives |

### Critical finding

**PWA create flow does not sign atoms.** `submitAtomFromModal` in `pwa/app.js` builds an atom and calls `postAtomToNetwork` without calling `signAtom` from `pwa/key-management.js`. The signing function exists but is not wired into the create flow.

**Impact:** Enabling `PUNKTO_REQUIRE_SIG=true` breaks PWA atom creation. Users see `Error: atom missing required field 'sig'`.

**Node2 state:** `PUNKTO_REQUIRE_SIG=true` is active on node2 relay. Unsigned atoms are rejected. The PWA create flow is broken until signing is wired in.

**Node1:** Not touched. Still running old image with `require_sig=false`.

---

## Canary Deployment Evidence — node2 (2026-06-22)

### Commit: 45a1602 — fix(pwa): wire Ed25519 signing into atom create and reply flows

### Verification Results

| Check | Result | Evidence |
|---|---|---|
| /health 200 | ✅ PASS | HTTP 200, status ok |
| /status 200 | ✅ PASS | HTTP 200, no secrets exposed |
| /node/info config_loaded | ✅ PASS | config_loaded: True |
| Hard marker in deployed app.js | ✅ PASS | PUNKTO_APP_VERSION = 'v108-pwa-signing-fix-2026-06-22-1' |
| Node fingerprint unchanged | ✅ PASS | node:0b2af9b3ca1d (matches pre-deploy) |
| Existing atoms preserved | ✅ PASS | Feed returns atoms with valid sigs |
| Unsigned atom rejected 403 | ✅ PASS | HTTP 403, error: missing_sig |
| Valid signed atom accepted 201 | ✅ PASS | HTTP 201, atom_id returned |
| PWA can create signed atom | ✅ PASS | Browser create flow → atom in feed with sig=true, pubkey present |
| First-use public warning works | ✅ PASS | Warning banner visible in create modal |
| TLS valid | ✅ PASS | CN=node2.punkto.xyz, issuer=Let's Encrypt |
| PUNKTO_REQUIRE_SIG in container | ✅ PASS | PUNKTO_REQUIRE_SIG=true |
| Node1 untouched | ✅ PASS | Not modified |

### Canary Status: ✅ PASS — all 11 verification checks passed

### Changes Deployed
- `pwa/app.js`: Added ensureIdentity() + signAtomForSubmit(), wired signing into submitAtomFromModal and reply path, bumped version to v108
- `pwa/key-management.js`: Added explicit window.signAtom/verifyAtom/generateIdentity exposures
- `deploy/docker-compose.yml`: Added PUNKTO_REQUIRE_SIG passthrough
- Node2: PUNKTO_REQUIRE_SIG=true enabled, relay + web containers running

### Rollback
- See canary report rollback instructions (Option A: remove PUNKTO_REQUIRE_SIG, Option B: full restore from backup)

---

## Node1 Deployment Evidence (2026-06-24)

### Commit: aadb286 — docs + 45a1602 fix(pwa): wire Ed25519 signing into atom create and reply flows

### Pre-deploy state
- Version: v107-desktop-bottom-gap-2026-06-09-1
- Fingerprint: node:a62adb0c3074
- PUNKTO_REQUIRE_SIG: not set
- Atom count: 2 (synced from node2)
- Backup: backups/canary-node1-20260624T092554Z.tar.gz

### Verification Results

| Check | Result | Evidence |
|---|---|---|
| /health 200 | ✅ PASS | HTTP 200 |
| /status 200 | ✅ PASS | HTTP 200, no secrets |
| /node/info config_loaded | ✅ PASS | config_loaded: True |
| Hard marker v108 | ✅ PASS | PUNKTO_APP_VERSION = 'v108-pwa-signing-fix-2026-06-22-1' |
| Node fingerprint unchanged | ✅ PASS | node:a62adb0c3074 (matches pre-deploy) |
| Existing atoms preserved | ✅ PASS | 4 atoms in feed, all signed |
| Unsigned atom rejected 403 | ✅ PASS | HTTP 403, missing_sig |
| Valid signed atom accepted 201 | ✅ PASS | HTTP 201, atom_id returned |
| PWA create flow (signed) | ✅ PASS | Browser create → 'Node1 deploy verify' in feed with sig=true |
| First-use public warning | ✅ PASS | Ack-banner visible, Place here disabled until ack |
| TLS valid | ✅ PASS | CN=node1.punkto.xyz, issuer=Let's Encrypt |
| PUNKTO_REQUIRE_SIG in container | ✅ PASS | PUNKTO_REQUIRE_SIG=true |
| Node-doctor | ✅ PASS | PASS (1 warning: false positive 'secret' pattern) |

### Node1 vs Node2 Comparison

| Item | Node1 | Node2 | Match |
|---|---|---|---|
| Version | v108-pwa-signing-fix-2026-06-22-1 | v108-pwa-signing-fix-2026-06-22-1 | ✅ |
| PUNKTO_REQUIRE_SIG | true | true | ✅ |
| Node-doctor | PASS | PASS | ✅ |
| Fingerprint | node:a62adb0c3074 | node:0b2af9b3ca1d | ✅ (unique per node) |

### Status: ✅ PASS — all 11 verification checks passed, both nodes aligned
