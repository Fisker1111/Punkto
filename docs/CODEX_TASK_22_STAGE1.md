# CODEX_TASK_22 — STAGE 1 (core protocol layer)

Read `docs/CODEX_TASK_22.md` first — it is the full contract and acceptance criteria.
This file scopes **Stage 1 only**. Do not start the PWA redesign, Docker, CI or
Playwright work (that is Stage 2).

**Do not commit. Do not push. Do not deploy. Do not touch any server.**

---

## Stage 1 goal

Land the **frozen Punkti 0.6 Layer-3 core** in both implementations, on the Python
node and in a **new reusable browser client module**, such that both produce and
consume the *same bytes* as the frozen normative vectors.

---

## S1.0 — Already vendored for you (do not re-fetch)

Into this tree I have already placed, verbatim from the accepted branch
`protocol/punkti-0.6-frozen`:

* `experimental/punkti-v0.6-mesh/` — the frozen XY_Z Python carrier/spatial reference
  (with `tests/test_xy_z.py`, `tests/test_revision.py` added).
* `pwa/spatial-xy-z.js`, `pwa/test-spatial-xy-z.mjs` — the accepted JS XY_Z codec and
  its test (from #19/#21).
* `docs/proposals/PUNKTI_0_6_*.md` — the frozen normative contracts.

`python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests` passes (37 tests).

**The XY_Z Python carrier is at `experimental/punkti-v0.6-mesh/src/carrier.py` and
`.../src/spatial.py` and is FROZEN. Do not modify their logic.** They are only
*relocated* below.

---

## S1.1 — Node-side: adopt the frozen XY_Z carrier

`punkti_node/` currently ships the **old provisional 3D-geohash** carrier
(`punkti_node/carrier.py` requires a 12-char interleaved geohash; `punkti_node/spatial.py`
is the "Provisional 60-bit 3D profile"). That is the shipped bug this task must fix.

Required:

1. `punkti_node/carrier.py` MUST become byte-identical to
   `experimental/punkti-v0.6-mesh/src/carrier.py`.
   `punkti_node/spatial.py` MUST become byte-identical to
   `experimental/punkti-v0.6-mesh/src/spatial.py`.

   The CI workflow enforces exactly this:
   ```bash
   cmp experimental/punkti-v0.6-mesh/src/carrier.py punkti_node/carrier.py
   cmp experimental/punkti-v0.6-mesh/src/spatial.py punkti_node/spatial.py
   ```
   Keep that invariant.

2. `punkti_node/__init__.py` loads `carrier`/`spatial`/`mesh` by file location with a
   local absolute-import shim. The frozen carrier now does `from spatial import
   parse_h`, so **the loader must be able to resolve `spatial` while `carrier` is being
   executed** — i.e. load `spatial` before `carrier`, and make the shim resolve
   lazily/safely. Verify `import punkti_node` and `python3 -m unittest
   punkti_node.test_node punkti_node.test_web` still pass.

3. `punkti_node/spatial.py`'s `Subscription` changes shape from
   `h_lo/h_hi/z_min(float)/z_max(float)` to `xy_lo/xy_hi/z_min(str)/z_max(str)`.
   Update every consumer accordingly:
   `punkti_node/config.py` (defaults + env overrides), `punkti_node/store.py`,
   `punkti_node/mesh.py`, `punkti_node/runtime.py`, `punkti_node/web.py`,
   `config/punkto-node.example.yml`, `node-config.example.yml`,
   `node-config.punkto-xyz.example.yml`, `punktto-config.example.yml`,
   `docs/*` config examples, and the `pwa/ui-settings.js` subscription editor if it
   emits the old field names.

   **Canonical Z is a decimal string, not a float.** Never round-trip Z through a
   binary float in the node's config/subscription path.

4. `punkti_node/test_node.py` / `test_web.py` currently use 12-char 3D-geohash `h`
   fixtures. Update them to the frozen XY_Z form and keep them meaningful. Do not
   weaken assertions to make them pass.

5. The legacy `p:` 12-char geohash address form and `core/geohash3d.py` /
   `pwa/geohash3d.js` are the **frozen v0.5.1** contract and MUST remain, unchanged,
   for v0.5.1 compatibility. They are not the 0.6 profile. Only the **0.6**
   `punkti/0.6` path moves to XY_Z.

---

## S1.2 — New browser client module `pwa/punkti/` (Stage-1 scope: spatial + carrier + vectors)

Create a **standalone, UI-independent** ES-module package under `pwa/punkti/`.

Hard rule: it MUST NOT import from `pwa/ui-*.js`, `pwa/app.js`, `pwa/core/`,
`pwa/storage/`, `pwa/protocol/`, `pwa/sync/`. It may use browser globals only
(`fetch`, `crypto.subtle`, `TextEncoder`/`TextDecoder`, `atob`/`btoa`, `nacl`).
It MUST run unchanged under plain `node` (for the test runner) **and** in a browser.
Where a browser-only API is needed (e.g. `crypto.subtle`), read it off `globalThis`
so a Node-compatible polyfill path exists — Node 22+ has `globalThis.crypto.subtle`,
so plain use of `crypto.subtle` is acceptable.

### `pwa/punkti/spatial.js`
Port of the frozen XY_Z profile, matching
`experimental/punkti-v0.6-mesh/src/spatial.py` **behaviourally**:
`xy_key`, `encode_xy(lat, lon, precision)` with precision 4..12 (default 10),
`decode_xy`, `parse_z` (canonical decimal: `0|[1-9][0-9]*` with optional fraction,
no `-0`, no trailing `0` in a fraction, length <= 27), `format_z`, `compare_z`
(exact decimal comparison — use `BigInt` scaled coefficients, never float),
`parse_h`, `encode_h`, `Subscription` equivalent as `normalize_scope` / `matches` /
`subscribed`, with `xy_lo`/`xy_hi`/`z_min`/`z_max` semantics identical to Python
(lower-inclusive / upper-exclusive over `K(xy) = xy.ljust(12,"0")`).

`pwa/spatial-xy-z.js` (already vendored) is a good reference implementation — reuse
or extend it rather than writing a second interpretation. **Do not create two
competing spatial implementations in the tree**: if you keep `pwa/spatial-xy-z.js`,
it must become a thin re-export of, or be replaced by, the single
`pwa/punkti/spatial.js`. One implementation, one file.

`format_z` in JS must reproduce the Python `ROUND_HALF_EVEN` behaviour on a float
input (nearest millimetre, ties to even) — the vendored `pwa/spatial-xy-z.js` already
implements this; port that logic, do not reinvent it.

### `pwa/punkti/carrier.js`
Punkti 0.6 carrier in the browser, byte-for-byte equivalent to
`experimental/punkti-v0.6-mesh/src/carrier.py`:

* canonical body `C` = `LP(v) || LP(t_decimal) || LP(h) || LP(x) || LP(alg) ||
  LP(pk_raw) || U32(nrefs) || (LP(target) || LP(rel))… || LP(ext_raw)`
  (field order exactly as in the Python `canonical()`).
* `S = "PUNKTI-L3-SIGN\0" || C`
* `MID = lowercase_hex(SHA256("PUNKTI-L3-MID\0" || C))`
* `R = LP(C) || LP(sig_raw)`
* canonical padded RFC 4648 base64 (reject non-canonical padding / nonzero unused bits
  by decode→re-encode comparison), `LP(b) = U32(len(b)) || b`, `U32` = 4-byte
  big-endian unsigned.
* envelope field set is exactly `{v,t,h,x,alg,pk,refs,ext,sig}`; `v = "punkti/0.6"`;
  `t` an integer 0..9007199254740991, accepted JSON spelling `0|[1-9][0-9]*`
  (reject `-0`, leading zeros, `+`, `.`, exponent).
* `h` is `""` or `<xy>_<z>` per the XY_Z profile (max 32 chars, exactly one `_`).
* reference `target` is `namespace:lowercase-hex-digest`; namespace must not be
  `punkti/0.5.1` or `punkti/0.6` with a digest that is not 64 hex chars.
* `SIG` is **excluded from MID** — a second signature over the same `C` yields the
  same MID.
* Ed25519 verify via `nacl.sign.detached.verify(sig, S, pk)` (TweetNaCl is vendored at
  `pwa/nacl.min.js` and is a browser global `nacl`).
* validation states, mirroring the Python `State` enum:
  `VALID`, `UNVERIFIABLE-alg`, `INVALID-structural`, `INVALID-provenance`,
  `UNVERIFIABLE-key`, `OPAQUE-version`. Structure and provenance are reported
  **separately**; an unknown `alg` is never reported VALID; a failed signature is
  never reported VALID.
* limits: body 1 MiB, record 2 MiB, <= 256 refs, rel <= 1024 bytes.

Expose at least:
`canonical(atom) -> Uint8Array`, `signingInput(body)`, `computeMid(body)`,
`encodeRecord(atom, secretKey) -> {address, mid, sha256, record}`,
`decodeRecord(bytes) -> {atom, body, sig}`,
`validate(bytes) -> {state, address, mid, h}`,
`b64/unb64` helpers.

### `pwa/punkti/test-vectors/`
Copy the **frozen vector bytes verbatim** into JSON fixture files here. Never
regenerate a vector.

* `carrier-vectors.json` — the frozen carrier fixtures from
  `experimental/punkti-v0.6-freeze/vectors.json` (the `fixtures` map: `C`, `S`,
  `MID`, `address`, `R`, `sig`, `sha256_R`, `atom`, `state`, plus `seed_hex` /
  `seed_literal`). That file is on branch `protocol/punkti-0.6-frozen` at
  `experimental/punkti-v0.6-freeze/vectors.json` — fetch it with
  `git show origin/protocol/punkti-0.6-frozen:experimental/punkti-v0.6-freeze/vectors.json`
  and copy the `fixtures` (and `seed_hex`) into the JSON file.
  **Preserve every hex byte exactly.**
* `spatial-vectors.json` — the XY_Z expected values: the geohash rows
  (`[55.675398,12.561895] -> "u3butz7k9q7v"`, `[51.5074,-.1278] -> "gcpvj0duq533"`,
  `[35.6762,139.6503] -> "xn76cydhzven"`, `[40.7128,-74.006] -> "dr5regw3ppyz"`,
  `[59.9139,10.7522] -> "u4xsudvxb2mq"`, `[0,0] -> "s000000000000"`,
  `[-90,-180] -> "000000000000"`, `[90,180] -> "zzzzzzzzzzzz"`, each at precision
  4/10/12), the measured heights
  (`[23.0254,-0.0001,0,23,-18,23.025,1.2345,-1.2345,0.0625,0.1875,-0.0625,-0.1875,1e20]`
  -> canonical decimal Z strings), the invalid Z spellings
  (`['+23','2.3e1','023','23.','23.0','23.50','-0','0.0','٢٣','.5','23\n']`),
  the invalid `h` spellings, the Z ordering list
  `['-18','-0.5','0','0.05','0.5','23','23.02','23.025','999999999999999999999999998','999999999999999999999999999']`,
  and the scope boundary expectations. Take them from
  `pwa/test-spatial-xy-z.mjs` (already vendored) and
  `docs/proposals/PUNKTI_0_6_SPATIAL_XY_Z.md`.
* `publication-vectors.json` — **Stage 1 may create the file header only**; the
  publication reader is Stage 2. Mark it `{"status": "stage-2", "vectors": {}}` so the
  runner can report a clear NOT-RUN for publication vectors rather than pretending.

---

## S1.3 — `pwa/test-punkti-vectors.mjs`

A plain `node` script (no framework) that exits non-zero on any failure. It MUST:

1. Load `pwa/punkti/test-vectors/*.json`.
2. Assert the **browser** carrier reproduces, for every carrier fixture:
   `C` bytes, `S` bytes, `MID`, `address` (`punkti/0.6:<mid>`), `R` bytes and
   `SHA256(R)` — **byte for byte**, comparing hex strings.
   To build `C`/`R` for a fixture you need the fixture's Ed25519 **secret key**:
   `vectors.json` carries `seed_hex`/`seed_literal` — use them to derive the key
   with TweetNaCl (`nacl.sign.keyPair.fromSeed`) and confirm the derived public key
   equals the fixture's `pk`. Confirm the produced signature equals the fixture `sig`.
   If the fixture's private seed is not recoverable from `vectors.json`, STOP and
   report that instead of inventing one.
3. Assert `signingInput`/`MID`/`R` round-trip: `decodeRecord(encodeRecord(atom))`
   reproduces `C` exactly and re-encoding is byte-stable.
4. Assert the **signature is excluded from MID**: re-signing the same `C` with a
   different key yields the same MID but a different `R` and a different
   `SHA256(R)`.
5. Assert the XY_Z spatial vectors (above), including invalid-Z and invalid-`h`
   rejection, Z ordering, and scope boundary cases.
6. Assert the Python and JS implementations agree, for every fixture, by shelling out
   to `python3` and comparing the produced `C`/`S`/`MID`/`R` hex. The Python side is
   the frozen reference; if JS and Python disagree, that is a **failure of this
   task**, not a reason to weaken an assertion — report it.

Print a clear summary line, e.g.
`XY_Z: N assertions passed; carrier: M fixtures byte-identical; JS==Python: OK`.

---

## S1.4 — Checks that must pass before you report done

```bash
node --check pwa/punkti/spatial.js
node --check pwa/punkti/carrier.js
node --input-type=module --check < pwa/punkti/spatial.js
node --input-type=module --check < pwa/punkti/carrier.js
node pwa/test-punkti-vectors.mjs
node pwa/test-spatial-xy-z.mjs
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
python3 -m unittest punkti_node.test_node punkti_node.test_web
cmp experimental/punkti-v0.6-mesh/src/carrier.py punkti_node/carrier.py
cmp experimental/punkti-v0.6-mesh/src/spatial.py punkti_node/spatial.py
python3 -m punkti_node --check-config --config node-config.example.yml
```

All must exit 0. If an existing repo test fails **because of** your change, fix the
cause honestly — do not delete or weaken the assertion.

---

## S1.5 — Report

1. Files changed/added.
2. The real output of every command in §S1.4 (paste, do not paraphrase).
3. The count of carrier fixtures proved byte-identical, and the number of XY_Z
   assertions.
4. Anything in the frozen contracts you found contradictory or under-specified —
   with a concrete counterexample, if any.
5. Confirmation: nothing committed, nothing pushed, nothing deployed.
