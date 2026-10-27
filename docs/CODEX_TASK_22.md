# CODEX_TASK_22 — Punktto PWA: static-first Punkti 0.6-native client + redesign + Docker conformance

**Status**: ACTIVE
**Base**: `feat/punkti-0.6-static-first-pwa` (from `origin/main` = 1ee5e68)
**Source of truth**: CEO-OS Issue #22 (Fisker1111/CEO-OS)

---

## 0. Read first (normative, already in this tree)

These are the **frozen, Founder-approved** Punkti v0.6 contracts. They are normative.
Do not weaken, reinterpret, or "improve" them.

| Document | Role |
|---|---|
| `docs/proposals/PUNKTI_0_6_LAYER3_RESET.md` | L3 carrier: C/S/MID/R bytes, validation states, MID vs SHA256(R) |
| `docs/proposals/PUNKTI_0_6_SPATIAL_XY_Z.md` | `h = <xy>_<z>` spatial profile (XY 4–12, canonical decimal Z) |
| `docs/proposals/PUNKTI_0_6_PUBLICATION.md` | static publication objects: root / manifest / shard / record / pack |
| `docs/proposals/PUNKTI_0_6_STATIC_PUBLICATION.md` | accepted static-first architecture |
| `docs/proposals/PUNKTI_0_6_MESH.md` | dynamic mesh = optional accelerator only |

**Protocol authority**: `punkti-org/punkti` frozen v0.6 docs + `VECTORS-v0.6.md`
(upstream `main`). **Implementation/evidence reference**: `Fisker1111/Punkto`
branch `protocol/punkti-0.6-frozen`.

If you find a contradiction between these documents, **STOP and report it** with a
concrete counterexample. Do not silently pick a side.

---

## 1. Goal

Make the Punkto PWA a genuinely **static-first, 0.6-native** client:

```
Punkto PWA (Layer 4 UX/meaning)
        |
        v
Punkti client module (Layer 3)   <- NEW, reusable, UI-independent
MID | XY_Z | verification | static publication reader | submit
        |
        v
ordinary HTTP/static publication
```

The browser MUST be able to read, browse and verify Punkti from a **dumb static HTTP
publication** with **no Punkti daemon serving reads**. No `/pull`, `/sync`, session or
callback may be required for browser reads.

---

## 2. Scope — five deliverables

### D1. Punkti browser client module (NEW, reusable, UI-independent)

Create `pwa/punkti/` as a standalone ES-module package. It MUST NOT import from
`pwa/ui-*.js`, `pwa/app.js`, `pwa/core/`, `pwa/storage/` or `pwa/protocol/`. It may
use only browser globals (`fetch`, `crypto.subtle`, `TextEncoder/Decoder`, `atob/btoa`,
`nacl` for Ed25519) and files inside `pwa/punkti/`.

Required modules:

| File | Responsibility |
|---|---|
| `pwa/punkti/spatial.js` | XY geohash encode/decode (4/10/12), canonical decimal Z parse/compare/format, `h = <xy>_<z>` build/parse, scope normalize/match. **Port the profile exactly as in `docs/proposals/PUNKTI_0_6_SPATIAL_XY_Z.md`.** Do not invent a second interpretation. |
| `pwa/punkti/carrier.js` | L3 carrier in the browser: canonical body `C`, signing input `S`, `MID = SHA256("PUNKTI-L3-MID\0" || C)`, `R = LP(C) || LP(sig)`, base64 canonicality, envelope field set, Ed25519 verify via `nacl.sign.detached.verify`, validation states `VALID / UNVERIFIABLE-alg / INVALID-structural / INVALID-provenance / OPAQUE-version`. Signature is **excluded** from MID. |
| `pwa/punkti/reader.js` | Static publication reader: GET mutable root → immutable manifest → XY-prefix shard tree → canonical `R` objects and/or replication packs. Verify content-addressed digests of EVERY fetched object; decode + verify every `R` locally; dedupe by MID without letting an invalid `R` variant poison a valid MID; handle stale root / missing object / corrupt object / publication race safely and retryably; support unanchored atoms (`h = ""`, reserved index key `~`); support client-side XY-prefix and exact-decimal Z filtering. |
| `pwa/punkti/submit.js` | Minimal submission client: `POST /submit` → validate → dedupe → persist → republish static publication. User submission is NOT peer replication. Must be idempotent on duplicate submit. Must surface clear browser-side errors for invalid/rejected records. |

Reader rules that MUST hold (from `PUNKTI_0_6_PUBLICATION.md`):

* Content address = lowercase hex SHA-256 over the object's **exact bytes**.
* Canonical JSON: UTF-8, no BOM, members sorted ascending by Unicode code point,
  separators `,`/`:`, no trailing newline, integers only, duplicate member names
  rejected.
* Root pointer members are exactly `head`, `seq`, `v`; `v = "punkti/pub/0.6"`; `seq >= 1`;
  no other members (no timestamp).
* Manifest members exactly `index`, `pack_count`, `prev`, `record_count`, `seq`, `v`.
* Shard members exactly `children`, `packs`, `prefix`, `records`, `v`.
* Record entry members exactly `h`, `mid`, `sha256`; `mid` is `punkti/0.6:<64 hex>`.
* Index geometry: `K(xy) = xy.ljust(12,"0")`; leaf prefix depth `D = 10`; manifest index
  maps **depth-2 XY prefixes** to shards, plus at most one reserved `"~"` key for
  unanchored records.
* Prefix interval `I(p) = [p + "0"*(12-d), p + "z"*(12-d)]`; scope overlap test:
  `I(p).low < scope.XY.high` and `I(p).high >= scope.XY.low` (with unbounded cases).
* Record entries sorted ascending by `sha256`; `packs` sorted ascending by content address.
* Packs: magic `PUNKTIPACK1` (**11 ASCII bytes**, no terminator), then `U32(count)`
  then `LP(record)` entries, `count` in 1..256. Packs are an **optional accelerator**.
* A reader MUST reject a shard whose bytes do not hash to the address that named it.
* First manifest: `seq = 1`, `prev = null`; later: `seq = prev+1`, `prev` = previous
  manifest address. A reader MUST reject a manifest where `seq` and the nullness of
  `prev` disagree.
* Only the root pointer is mutable, and it MUST be replaced atomically by the publisher.

**Filesystem path layout is NOT normative.** The reader MUST be configurable with a
"path resolver" so a publication served from any directory layout can be read. Ship at
least these two resolvers:
1. `hexSharded` — the reference layout used by the frozen evidence
   (`records/<aa>/<sha>`, `segments/<aa>/<sha>`, `manifests/<sha>.json`,
   `h/<prefix chars joined>/<sha>.json`, `root.json`);
2. `flat` — `records/<sha>`, `segments/<sha>`, `manifests/<sha>.json`,
   `h/<sha>.json`, `root.json`.
Provide a third resolver that reads a **manifest-provided path map** if a publication
supplies one, but never require it.

### D2. Normative-vector conformance in JS

Create `pwa/test-punkti-vectors.mjs` (plain `node` script, no test framework, exit
non-zero on failure) that runs, **in the browser implementation** (`pwa/punkti/*.js`):

* every **XY_Z** normative case from `docs/proposals/PUNKTI_0_6_SPATIAL_XY_Z.md`
  (XY precision 4/10/12, negative Z, decimal Z, large/high Z, unanchored, invalid
  spellings, scope boundary semantics);
* every **carrier** fixture from the frozen vector set. The frozen carrier vectors live
  in the upstream `punkti-org/punkti` repo `VECTORS.md`/`VECTORS-v0.6.md` and, in this
  repo lineage, in `experimental/punkti-v0.6-freeze/vectors.json`. Port the **fixture
  vectors** (C, S, MID, address, R, sha256_R) into a JSON fixture file under
  `pwa/punkti/test-vectors/` — e.g. `carrier-vectors.json` — and assert the browser
  codec reproduces every byte exactly;
* the **publication** vectors: root/manifest/shard/record/pack byte-level constructions
  and the hostile cases (tampered manifest/shard/record, missing object, pack count
  mismatch, pack duplicate/foreign/reversed/trailing/truncated, poison variant,
  stale root, newer root).

When importing a frozen vector set, **copy the bytes verbatim**; never regenerate them.

### D3. Static-only PWA + write-to-static round trip

Wire the client module into the PWA:

* The PWA reads atoms from the **static publication** via `pwa/punkti/reader.js`.
  Remove the dependency of the read path on `/pull`, `/sync`, `/push` or any
  session/callback. A node-local publication served by a dumb static file server must
  be browsable with the Punkti daemon stopped.
* Add a **`/submit`** write path on the bundling node (server side — see D4) and a UI
  affordance that uses it. A successful submit MUST become visible through the static
  read path afterwards. Duplicate submit MUST be harmless (idempotent).
* PreserveLayer 4 opacity: Punkto `x` payload stays opaque Layer-4 content. Do not
  let L4 metadata redefine L3 spatial truth.
* Punkto `MID` becomes the natural exact logical object/link identity where an exact
  Punkti object reference is needed. Do **not** keep `p:<12-char-3D-geohash>` as a
  second quasi-protocol spatial identity.

### D4. Node-side: one-image, static publication, Docker conformance

On the **bundling node** (Python, `punkti_node/`):

* Implement the **publisher**: on submit, validate the record locally
  (`carrier.validate`), dedupe by MID, persist durably, then **republish the static
  publication** under a data-dir location. The publication root pointer MUST be
  replaced atomically (temp file in the same directory → fsync → rename → fsync dir).
  The publication root MUST only advance **after** the immutable objects it names are
  durable.
* Implement a **static publication reader/replicator** on the node: a node MAY
  replicate a peer by reading the peer's static publication over ordinary HTTP and
  republishing it locally — with no live mesh session. (This is the read-only
  replication experiment from Issue #20, promoted to product.)
* Serve the publication from the **same origin** as the PWA so the PWA can read it
  through the same origin (ordinary static paths).
* One image must host: the Punkto PWA + the validator/submitter + the generated static
  Punkti publication. Durable publication/store data MUST survive container restart
  (persistent volume). An operator MUST be able to disable the UI while still
  serving/replicating Punkti.
* The same image MUST work under arbitrary node/domain branding/configuration, and
  MUST NOT require Cloudflare/CDN.

### D5. CI / Docker workflow rationalization (Phase 8)

There are currently two Docker generations in `.github/workflows/`:

* `.github/workflows/docker.yml` — legacy `punkto-web` + `punkto-relay` builds (the
  **old** architecture). **Retire/quarantine** it: it MUST NOT keep publishing
  `latest` from an unrelated legacy path.
* `.github/workflows/node-image.yml` — node-only image.
* `.github/workflows/punkto-image.yml` — the combined single-image workflow.

Required end state:

* exactly **one canonical combined-image workflow** for the reference product;
* legacy `punkto-web` / `punkto-relay` automatic builds retired or quarantined
  (disabled / `workflow_dispatch`-only / clearly marked legacy) so that `latest` is
  never published from an unrelated legacy path;
* image **digest** pinning/review for deployment (record the digest, do not deploy
  a floating tag);
* **linux/amd64 and linux/arm64** both built;
* JS syntax + unit + **vector** tests MUST run **before** any image publish;
* workflow must not publish `latest` from a prerelease/draft tag.

---

## 3. Explicitly OUT of scope

* **No dynamic read/sync acceleration.** No `/pull`-based reading in the browser, no
  mesh session in the read path, no new sync protocol. (CEO-OS #23 tracks the
  optional accelerator.)
* **No production cutover.** Do NOT deploy to `punkto.xyz`. Do NOT touch
  `node1.punkto.xyz` / `node2.punkto.xyz` / `test1.punkto.xyz`. No Docker push, no
  registry write, no release tag, no production config change. This task delivers a
  branch + tests + evidence; the Founder decides cutover.
* Do not modify the frozen protocol documents' *technical* content.
* Do not add AI features, accounts, or a central service.
* Do not replace MapLibre/deck.gl.

---

## 4. Acceptance criteria (all must be demonstrably true)

### Protocol / JS
1. JS reproduces **all** frozen carrier vector bytes (C, S, MID, address, R, SHA256(R)).
2. JS XY_Z: precision 4/10/12, negative Z, decimal Z, large/high Z, unanchored all
   match the normative profile; invalid spellings rejected.
3. Browser-generated records match the normative C/S/MID/R vectors byte-for-byte.
4. Reader rejects: corrupt manifest / shard / record / pack, missing object, pack count
   mismatch, pack duplicate, foreign pack, reversed pack, trailing pack bytes,
   truncated pack.
5. Anti-poisoning: a same-MID invalid `R` variant MUST NOT suppress a valid `R`.
6. Stale root refresh; missing-object retry; equivocal root handled.
7. Exact MID/R verification, including that signature is excluded from MID.
8. Layer-4 opaque payload preserved byte-for-byte through publish→read.

### Static-only PWA
9. A dumb static HTTP server (e.g. `python3 -m http.server`) serving ONLY the
   publication directory, with the source Punkti daemon **stopped**, serves a
   browsable publication: browser loads it, verifies it, displays valid atoms, and
   supports XY-prefix browsing.
10. **No `/pull` and no `/sync` request is made by the browser during a read.** Prove
    this by asserting on the recorded request log of the static server / a request
    interceptor.

### Write-to-static round trip
11. Browser creates a correct `XY_Z` record → `POST /submit` → node validates and
    persists → publication root advances **only after** immutable objects exist →
    browser sees the new atom through the static read path → duplicate submit is
    harmless.

### Node replication
12. Node B reads Node A **through static publication only**; A/B divergent sets
    converge; three-node partial overlap converges; source disappears/reappears;
    restart persistence holds.

### Docker / E2E
13. Image builds; fresh node launches; browser smoke test passes; submit/read works;
    container restart keeps data; a second node static-replicates; application
    logic can be stopped (UI disabled) while the static publication still serves and
    replication/read still succeeds; amd64 + arm64 both build.

**Use Playwright (or equivalent real browser automation) for the critical browser
flows** (criteria 9, 10, 11 and the browser smoke test) — not only Node unit tests.
Playwright browsers are already cached at `~/.cache/ms-playwright` (`chromium-1243`)
and the `playwright` npm package resolves via `npx` (v1.64.1). **Docker is NOT
installed on this machine** — Docker/E2E evidence that requires a docker daemon
**cannot be produced here**; instead provide the runnable scripts and record
explicitly in the evidence report that the Docker daemon steps are unverified locally
and must be run by the deployment operator. Do not fabricate Docker output.

---

## 5. Required checks (must all pass before you report done)

```bash
# JS syntax
for f in pwa/*.js pwa/punkti/*.js pwa/punkti/test-vectors/*.mjs; do node --check "$f" || exit 1; done
node --input-type=module --check < pwa/app.js

# protocol + vector conformance
node pwa/test-punkti-vectors.mjs

# Playwright browser flows (write the script; run it if the daemon permits)
node pwa/test-punkti-static-e2e.mjs      # or .mjs Playwright runner

# python node suite
python3 -m unittest punkti_node.test_node punkti_node.test_web
```

Also run the existing repo suites you touch, and keep them green:
`node pwa/test-slice5.mjs`, `node pwa/test-punkti-client.mjs` (if kept),
`python3 relay/test_relay.py` (known pre-existing failures are pre-existing — do not
introduce new ones).

---

## 6. Deliverables to write into the tree

| Path | Content |
|---|---|
| `pwa/punkti/*.js` | the Layer-3 browser client module (D1) |
| `pwa/punkti/test-vectors/*.json` | frozen vector fixtures copied verbatim |
| `pwa/test-punkti-vectors.mjs` | protocol/vector conformance runner |
| `pwa/test-punkti-static-e2e.mjs` | Playwright static-only + round-trip flows |
| `punkti_node/publication.py` | node-side publisher + static replication reader |
| `punkti_node/submit.py` (or equivalent) | `/submit` route: validate→dedupe→persist→republish |
| `punkti_node/web.py` | static publication serving + `/submit` wiring (same origin) |
| `docs/INTEGRATION_22.md` | integration report: what changed, what was removed/retained, evidence, cutover recommendation |
| `docs/evidence/issue-22/` | raw test output artifacts |

`docs/INTEGRATION_22.md` MUST contain:

* exact list of legacy code **removed** and **retained** (file by file, with reason);
* the PWA redesign summary (what the user sees changed);
* the placement/Z UX explanation (Punkti Z = WGS84 ellipsoidal height vs Punkto
  floor/height-above-ground = optional Layer-4 metadata; how the browser derives or
  requests an ellipsoidal Z; what happens when exact ellipsoidal Z is unavailable);
* every acceptance criterion from §4 with **PASS / FAIL / NOT RUN (reason)**;
* the production cutover recommendation and the explicit list of gates still open.

---

## 7. Stop condition / report format

When finished, report:

1. Files changed (list).
2. Exact commands run and their real output (no paraphrasing; no invented results).
3. Acceptance criterion table from §4 with PASS/FAIL/NOT RUN.
4. Known gaps, risks, and anything a human must decide.
5. Confirmation that NOTHING was deployed, no tag pushed, no registry write, and no
   production file touched.

**Do not commit.** Hermes reviews `git diff` and commits from its own shell.
Leave all changes in the working tree.

**Do not ask questions.** The documents in §0 are normative; if a genuine
contradiction exists, stop and report it with a counterexample instead of guessing.
