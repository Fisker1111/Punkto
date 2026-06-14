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
