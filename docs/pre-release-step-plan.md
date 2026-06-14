# Punkto Pre-Release Step Plan

> Rules for every point:
> - Do not mark a point as passed without verification.
> - If code changes are made, run tests or manual API checks.
> - If deployment is needed, say clearly: "Deploy required: yes".
> - If deployment is not needed, say clearly: "Deploy required: no".
> - Update this document after each point with PASS, FAIL, PARTIAL, evidence, commit hash if relevant.

---

## Point 1 — Relays must only accept signed atoms

**Goal:** Public relays must reject unsigned atoms and atoms with invalid signatures.

**Deploy required:** yes (relay code changed)

**Deploy status:** not deployed

### Tasks completed

1. Added Ed25519 cryptography imports (try/except with `_HAS_CRYPTO` guard).
2. Added `require_sig: False` to `DEFAULT_NODE_CONFIG["serving_policy"]`.
3. Added four pure functions to `relay/relay.py`:
   - `require_signature_enabled()` — reads `PUNKTO_REQUIRE_SIG` env var, falls back to config `require_sig`
   - `canonical_atom_for_signing(atom)` — canonical JSON bytes excluding `sig` and `pubkey`
   - `verify_atom_signature(atom)` — Ed25519 verification, returns `None` on success or error dict
   - `validate_signature_policy(atom)` — orchestrates policy check, returns `(bool, Optional[dict])`
4. Wired `validate_signature_policy` into `do_POST` handler after acceptance policy check.
5. Created `relay/test_sig.py` with 6 test cases using real Ed25519 keys.

### Test command

```
cd /a0/usr/projects/punkto/relay && python3 test_sig.py
```

### Test output

```
[RELAY] [2026-06-10T10:07:29] node config missing at /config/punkto-node.yml; using safe defaults
[RELAY] [2026-06-10T10:07:29] Loaded existing node identity node_fingerprint=node:1979e64f6fe9 path=/data/node-key.json
============================================================
PUNKTO_REQUIRE_SIG — signature enforcement tests
============================================================

[PUNKTO_REQUIRE_SIG=true]  require_signature_enabled()=True

A. unsigned atom + require_sig=true
  PASS A: rejected — error=missing_sig

B. missing pubkey + require_sig=true
  PASS B: rejected — error=missing_pubkey

C. fake signature + require_sig=true
  PASS C: rejected — error=invalid_sig

D. valid signed atom + require_sig=true
  PASS D: accepted

E. modified-after-signing atom + require_sig=true
  PASS E: rejected — error=invalid_sig

[PUNKTO_REQUIRE_SIG=false]  require_signature_enabled()=False

F. unsigned atom + require_sig=false
  PASS F: accepted

============================================================
Results: 6/6 passed
STATUS: ALL PASS
```

### Status: **PASS**

---

## Point 2 — Fix fresh-install documentation

**Deploy required:** no (docs only)

**Deploy status:** not applicable

### Changes made

1. Fixed atom POST example in section 12:
   - `"timestamp"` → `"t"` (relay requires `t`, not `timestamp`)
   - `date +%s` → `date +%s%3N` (milliseconds, not seconds)
2. Added `PUNKTO_REQUIRE_SIG` note explaining default `false` and what to do if signature enforcement is enabled.
3. Added expected response examples after each command:
   - POST /atom: `{"ok": true, "atom_id": "..."}` with HTTP 201
   - GET /feed: JSON array containing posted atom
4. Added troubleshooting hints for `HTTP 400 invalid_timestamp` and `HTTP 403 missing_sig`.

### Verification — all 5 guide steps simulated against local relay

```
=== 1. /health ===
{"status":"ok","node":"relay-f1360a5ece01","buffer_size":0}
HTTP 200 ✅

=== 2. /node/info ===
config_loaded: False (expected without node config file in local dev)
HTTP 200 ✅

=== 3. /status ===
HTTP 200 ✅

=== 4. POST /atom (t in milliseconds, PUNKTO_REQUIRE_SIG=false) ===
{"status":"accepted","atom_id":"bca2457ea6e3e323f51eb740486a6eab031761c406e70f36e1906b2e7830106a","punkto":"p:test00000000"}
HTTP 201 ✅

=== 5. /feed ===
feed items: 2 ✅
```

### Status: **PASS**

---

## Point 3 — Run the full pre-release checklist

**Status:** TODO

**Evidence:** Not tested yet.

---

## Point 4 — Public/private warning in app and docs

**Status:** TODO

**Evidence:** Not tested yet.

---

## Point 5 — Verify /status and /node/info expose no secrets

**Status:** TODO

**Evidence:** Not tested yet.

---

## Point 6 — Backup and restore test

**Status:** TODO

**Evidence:** Not tested yet.

---

## Point 7 — Public alpha GitHub issues

**Status:** TODO

**Evidence:** Not tested yet.

---

## Point 8 — Public alpha wording

**Status:** TODO

**Evidence:** Not tested yet.

---

## Summary table

| Point | Name | Deploy required | Status | Evidence |
|-------|------|----------------|--------|----------|
| 1 | Relays only accept signed atoms | Yes | **PASS** | 6/6 tests pass (see above) |
| 2 | Fix fresh-install documentation | No | TODO | Not tested |
| 3 | Run full pre-release checklist | No | TODO | Not tested |
| 4 | Public/private warning | Yes | TODO | Not tested |
| 5 | Verify public endpoints expose no secrets | Maybe | TODO | Not tested |
| 6 | Backup and restore test | Maybe | TODO | Not tested |
| 7 | Public alpha GitHub issues | No | TODO | Not tested |
| 8 | Public alpha wording | Maybe | TODO | Not tested |

---

## Point 3 — Validate and update full pre-release checklist

**Status: PARTIAL**

**Commit tested:** `145edf9`

**Deploy required:** no (for checklist audit itself)

**Date verified:** 2026-06-14

### Summary

| Section | Checks | Result |
|---------|--------|--------|
| A. Repository and tests | 8/8 | ✅ PASS |
| B. Relay runtime | 6/6 | ✅ PASS |
| C. Storage | 4/4 (with finding) | ⚠️ PARTIAL |
| D. Configuration | 5/5 | ✅ PASS |
| E. Public endpoint safety | 4/4 | ✅ PASS |
| F. Documentation consistency | 7/7 | ✅ PASS |
| G. Deployment-dependent | 6 items | 📋 TODO |

**Total: 34/34 local checks PASS, 6 TODO (deployment-only), 1 defect documented (C-finding)**

---

### A. Repository and tests — PASS

```
[PASS] A1. Working tree clean
[PASS] A2. Signature tests (test_sig.py): 6/6 passed STATUS: ALL PASS
[PASS] A3. relay.py syntax clean
[PASS] A4. test_relay.py syntax clean
[PASS] A5. node --check pwa/app.js
[PASS] A5. node --check pwa/ui-shell.js
[PASS] A5. node --check pwa/ui-text.js
[PASS] A5. node --check pwa/ui-map.js
```

### B. Relay runtime — PASS

Relay started on port 8000, `PUNKTO_REQUIRE_SIG=false`.

```
[PASS] B1. /health HTTP 200: {"status":"ok","node":"relay-f1360a5ece01","buffer_size":1}
[PASS] B2. /status HTTP 200
[PASS] B3. /node/info HTTP 200 JSON: name=Punkto ver=v0.1 ok=True
[PASS] B4. POST unsigned atom → HTTP 201
        {"status":"accepted","atom_id":"8c71ffd3d689efd0071e4a33d2cfe0d75a5991445e3c1ead361a31be85422b0b","punkto":"p:test00000000"}
[PASS] B5. POST invalid atom (no t) → HTTP 422 error=invalid_punkto
[PASS] B6. GET /feed → HTTP 200, 2 items
```

Note: punkto ID must match `p:[0-9a-z]{12}` exactly (12 lowercase alphanumeric chars).

### C. Storage — PARTIAL

```
[PASS] C1. atom log exists on disk: /data/atoms.log.jsonl
[PASS] C2. atom log non-empty: 3 lines
[PASS] C3. atom log lines are valid JSON
[PASS] C4. duplicate atom idempotent: HTTP 200 {"status":"duplicate","atom_id":"..."}  
```

**⚠️ DEFECT FOUND — C-finding: atom log missing cursor and atom_id fields**

Actual log format:
```json
{"punkto": "p:test00000000", "content": "...", "t": 1749900000000}
```

Expected format per `docs/sync-fast-forward.md`:
```json
{"cursor": 1, "atom_id": "abc123...", "atom": {"punkto": "...", "content": "...", "t": ...}}
```

The relay does not write `cursor` or `atom_id` to the log. Fast-forward protocol (`/feed?since=<cursor>`) cannot work from this log without recomputing atom_ids and adding sequence numbers. This defect should be addressed before public alpha.

**Recommendation:** implement atom log writer per `docs/sync-fast-forward.md` spec (Phase 8B).

### D. Configuration — PASS

```
[PASS] D1. PUNKTO_REQUIRE_SIG=true rejects unsigned (pure fn): error=missing_sig
[PASS] D2. PUNKTO_REQUIRE_SIG=false allows unsigned (pure fn): accepted
[PASS] D3. require_signature_enabled()=True when env=true
[PASS] D4. require_signature_enabled()=False when env=false
[PASS] D5. cryptography library available: _HAS_CRYPTO=True
```

### E. Public Endpoint Safety — PASS

Checked /health, /node/info, /feed, /status for: private_key, secrets.env, password, secret_key, auth_token.

```
[PASS] E1. /health: no secret material exposed
[PASS] E2. /node/info: no secret material exposed
[PASS] E3. /feed: no secret material exposed
[PASS] E4. /status: no secret material exposed
```

### F. Documentation consistency — PASS

```
[PASS] F1. guide uses "t" not "timestamp" (atom field)
[PASS] F2. guide uses date +%s%3N (milliseconds)
[PASS] F3. guide mentions PUNKTO_REQUIRE_SIG
[PASS] F4. guide has /atom endpoint
[PASS] F5. guide has /feed endpoint
[PASS] F6. guide has /node/info endpoint
[PASS] F7. public-api.md present (17530 chars)
```

### G. Deployment-dependent — TODO

These checks require live deployed nodes and cannot be verified locally:

| Item | Reason |
|------|--------|
| G1. node doctor passes on deployed node | Requires SSH to node1/node2 |
| G2. atom persists after docker compose restart | Requires deployed node |
| G3. YAML config loaded (config_loaded=true) | Requires deployed node |
| G4. TLS/HTTPS endpoints reachable | Requires deployed node |
| G5. PWA app marker visible on app1/app2 | Requires browser + deployed node |
| G6. Backup/restore scripts on deployed node | Requires deployed node |

### Launch candidate checklist status

Based on local verification, the overall `docs/launch-candidate-checklist.md` status:

| Section | Locally verifiable | Local status | Deploy-only |
|---------|-------------------|--------------|-------------|
| 1. Runtime Health | 5/7 | PASS | 2 items (nodes 1.1, 1.2) |
| 2. Storage | 2/4 | PARTIAL (log format defect) | 2 items |
| 3. Live-Forward Policy | 1/5 | PASS (old atom rejection works) | 4 items |
| 4. Backup / Restore | 0/5 | TODO | 5 items |
| 5. Fresh Install | 1/4 | PASS (guide exists, updated) | 3 items |
| 6. API / Docs | 3/6 | PASS (public-api.md, fresh-install, node.md present) | 3 items |
| 7. Security | 3/7 | PASS (no secrets in endpoints) | 4 items |

**Point 3 status: PARTIAL** — all locally testable checks PASS; storage log format defect found (C-finding); 6 deployment-dependent checks remain TODO.


---

## Point 4 — Fix append-only atom log format and fast-forward persistence

**Status: PASS**

**Commit tested:** (see below)

**Deploy required:** yes (relay code changed)

**Deploy status:** not deployed

**Date verified:** 2026-06-14

### Problem

Atom log stored raw atoms only (`{punkto, content, t}`). No cursor or atom_id in log records. Identified in Point 3 audit as C-finding.

### Solution (Option A — backward-compatible migration)

Modified `Buffer` class in `relay/relay.py`:

1. **`Buffer.__init__`**: Added `self._next_cursor: int = 1` — monotonically increasing sequential cursor.
2. **`Buffer.load()`**: Detects both legacy raw atoms and new wrapped records:
   - New format: `{"cursor": N, "atom_id": "...", "atom": {...}}` — extracts atom, updates `_next_cursor` from stored cursor.
   - Legacy format: raw atom dict — loads as-is, `_next_cursor` starts from 1.
3. **`Buffer.append()`**: Now writes wrapped format: `{"cursor": N, "atom_id": "...", "atom": {...}}`.
4. **`Buffer.feed_since()`**: Unwraps atom from wrapper when parsing log records. Byte-offset cursor preserved for backward compatibility.

### Test command

```bash
cd /a0/usr/projects/punkto/relay && python3 test_log_format.py
```

### Test output

```
============================================================
POINT 4 — Atom log format and fast-forward tests
============================================================

A. New atom gets atom_id and cursor in log record
  [PASS] A. was_new=True
  [PASS] A. log has 1 record
  [PASS] A. record has 'cursor' key: ['cursor', 'atom_id', 'atom']
  [PASS] A. record has 'atom_id' key
  [PASS] A. record has 'atom' key
  [PASS] A. atom_id matches computed: d47efb04d099
  [PASS] A. cursor is integer >= 1: cursor=1

B. Two unique atoms get monotonically increasing cursors
  [PASS] B. log has 2 records
  [PASS] B. cursor2 > cursor1: cursor1=1 cursor2=2

C. Duplicate atom is idempotent (no second cursor)
  [PASS] C. first append was_new=True
  [PASS] C. second append was_new=False
  [PASS] C. log has exactly 1 record
  [PASS] C. both calls return same atom_id

D. New-format log survives relay restart (atom_id and cursor preserved)
  [PASS] D. buffer size=1 after restart
  [PASS] D. atom retrievable by id after restart
  [PASS] D. new cursor after restart > original cursor: orig=1 new=2

E. Legacy raw-atom log loads without crashing
  [PASS] E. loads without exception
  [PASS] E. buffer has 2 legacy atoms: size=2
  [PASS] E. corrupt_lines=0 for legacy

F. After loading legacy entries, new entries continue with safe increasing cursors
  [PASS] F. log has 2 lines total
  [PASS] F. new record is wrapped format: ['cursor', 'atom_id', 'atom']
  [PASS] F. new cursor >= 1: cursor=1

G. feed_since(cursor=0) returns all public atoms
  [PASS] G. feed_since(0) returns 3 atoms
  [PASS] G. new_cursor > 0: new_cursor=474
  [PASS] G. underflow=False

H. feed_since(first_cursor) returns only atoms after that cursor
  [PASS] H. feed_since(after H1) returns 2 atoms
  [PASS] H. underflow=False

I. Corrupt log line is skipped; relay loads remaining atoms normally
  [PASS] I. loads without exception
  [PASS] I. corrupt_lines=1: corrupt=1
  [PASS] I. buffer has 2 valid atoms: size=2

============================================================
Results: 30/30 passed, 0 failed
STATUS: ALL PASS
```

### Point 1 regression check

```
cd /a0/usr/projects/punkto/relay && python3 test_sig.py
Results: 6/6 passed
STATUS: ALL PASS
```

### C-finding from Point 3 — RESOLVED

The atom log format defect identified in Point 3 is now fixed. New log records include `cursor`, `atom_id`, and `atom`. Legacy raw-atom logs load without crashing and continue with safe sequential cursors.

### git diff stats

```
relay/relay.py     | 23 ++++++++++++++++++++---
relay/test_log_format.py | 266 lines (new file)
```


## Point 4 Addendum — Cursor Semantics Review

### Authoritative conclusion: Option B — Byte-offset cursor

**Evidence:**
- `punkto.sync.md §236`: "Cursors are byte offsets as defined in `punkto.node.md §14`." (normative)
- `docs/sync-fast-forward.md §15`: "Full cursor semantics remain future work beyond the current byte-offset compatibility behavior."
- `Buffer.feed_since()` docstring: "The cursor is a byte offset in atoms.log.jsonl."
- Peer sync code (`_sync_one_peer`): reads `int(payload.get('cursor', 0))` — byte offset

**Problem found:** Point 4 initial commit used `"cursor"` as both:
1. Sequential integer in log wrapper record
2. Byte-offset returned by /feed and used by peer sync

This violated the rule: "Do not keep two unrelated values both named cursor without explicit specification."

**Fix applied:** Renamed log wrapper field from `cursor` to `log_seq`. Updated:
- `Buffer.__init__`: `_next_cursor` → `_next_log_seq`
- `Buffer.load()`: detects `log_seq` or legacy `cursor` key for backward compat
- `Buffer.append()`: writes `log_seq` field in wrapper
- `Buffer.feed_since()` docstring: clarified byte-offset is authoritative
- `test_log_format.py`: updated all wrapper field references
- New `test_cursor_semantics.py`: 5-step integration test with real relay process

### Integration test results (18/18 PASS)

```
cd /a0/usr/projects/punkto/relay && python3 test_cursor_semantics.py

============================================================
POINT 4 — Cursor semantics integration tests
Authoritative model: byte-offset cursor (punkto.sync.md §236)
============================================================

[Setup] Starting relay on port 19877
  [PASS] Relay starts and /health returns 200

1. POST atom1, capture cursor from /feed
  [PASS] 1. POST atom1 returns 201
  [PASS] 1. atom1_id present
  [PASS] 1. /feed cursor is integer > 0: cursor=1427
  [PASS] 1. atom1 is in feed

2. POST atom2
  [PASS] 2. POST atom2 returns 201
  [PASS] 2. atom2_id present and distinct

3. GET /feed?since=1427 → should return only atom2
  [PASS] 3. /feed?since=cursor returns exactly 1 atom: count=1
  [PASS] 3. returned atom is atom2: content='second atom'

4. Restart relay, repeat /feed?since=<cursor>
  [PASS] 4. Relay restarts and /health returns 200
  [PASS] 4. /feed?since=cursor after restart returns 1 atom: count=1
  [PASS] 4. atom after restart matches atom2: content='second atom'
  [PASS] 4. cursor unchanged after restart

5. Legacy raw-atom log: relay starts cleanly, new atoms get correct cursors
  [PASS] 5. Relay with legacy log starts
  [PASS] 5. Legacy atoms loaded (feed has >= 2)
  [PASS] 5. New atom accepted after legacy load
  [PASS] 5. Feed has >= 3 atoms after new post
  [PASS] 5. Cursor after new post > 0

============================================================
Results: 18/18 passed, 0 failed
STATUS: ALL PASS
```

### Updated Point 4 status: PASS
- All storage tests: 30/30 PASS (test_log_format.py)
- All cursor semantics integration tests: 18/18 PASS (test_cursor_semantics.py)
- Point 1 regression: 6/6 PASS
- Deploy required: yes
- Deploy status: not deployed
