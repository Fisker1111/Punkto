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

*Last updated: 2026-06-05*
