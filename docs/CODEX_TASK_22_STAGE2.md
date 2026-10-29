> Historical pre-correction draft, superseded by the 2026-10-29 spatial-only correction: every v0.6 record requires canonical XY_Z; empty h and publication key `~` are invalid. Signed historical evidence remains frozen in `legacy-unanchored/`.

# CODEX_TASK_22 — STAGE 2 (static publication reader, submit path, node publisher)

Read `docs/CODEX_TASK_22.md` first (full contract + acceptance criteria), then this
file (Stage 2 scope). Stage 1 is already landed on this branch
(`a450490`) and MUST keep passing.

**Do not commit. Do not push. Do not deploy. Do not touch any server.**

---

## Stage 2 goal

The browser reads Punkti from a **dumb static HTTP publication**; the node writes
Punkti into one. No `/pull`/`/sync` is required for any browser read.

---

## S2.1 — `pwa/punkti/reader.js` (the heart of this stage)

A **standalone, UI-independent** ES module. Hard rule: it MUST NOT import from
`pwa/ui-*.js`, `pwa/app.js`, `pwa/core/`, `pwa/storage/`, `pwa/protocol/`,
`pwa/sync/`. It may import from `pwa/punkti/spatial.js` and `pwa/punkti/carrier.js`
only, plus browser globals (`fetch`, `crypto.subtle`, `TextEncoder/Decoder`,
`atob/btoa`, `nacl`).

It MUST run under plain `node` for the test runner **and** in a browser. Inject the
fetch function so tests can serve from a local static server or from an in-memory map:

```js
export function createReader({ fetchImpl = globalThis.fetch?.bind(globalThis), resolver, ... })
```

### Reading algorithm (normative: `docs/proposals/PUNKTI_0_6_PUBLICATION.md`)

1. GET the mutable **root pointer** (`root.json`). Parse as canonical JSON; members
   exactly `head`, `seq`, `v`; `v === "punkti/pub/0.6"`; `seq` an integer `>= 1`;
   `head` 64 lowercase hex. Reject anything else as an invalid object.
2. GET the **manifest** at the address `head`. Verify `SHA256(bytes) === head`.
   Members exactly `index`, `pack_count`, `prev`, `record_count`, `seq`, `v`.
   `seq` MUST equal the root's `seq`. `prev` is 64 hex or `null`; the rule
   `(seq === 1) === (prev === null)` MUST be enforced.
3. Walk the **index tree** from `manifest.index` (depth-2 XY prefixes, plus at most
   one reserved `"~"` key for unanchored records). For each shard:
   * GET the shard bytes at the resolved path; verify `SHA256(bytes) === address`.
   * Members exactly `children`, `packs`, `prefix`, `records`, `v`.
   * `prefix` must equal the prefix under which the shard was reached.
   * Interior shard (`children` non-empty) MUST have empty `records` and `packs`;
     leaf shard (depth 10, or `"~"`) MUST have non-empty `records` and empty `children`.
   * Child keys are one char longer than the shard prefix and MUST start with it;
     child length `<= 10`.
   * Record entries have members exactly `h`, `mid`, `sha256`; `mid` matches
     `punkti/0.6:<64 lowercase hex>`; `sha256` is 64 hex; entries sorted ascending by
     `sha256` with no duplicates.
   * Record placement: the record's `h` MUST file under the correct leaf prefix —
     `L = K(xy).slice(0,10)` for anchored records, `"~"` for `h === ""`.
   * `packs` sorted ascending by content address, no duplicates.
4. Fetch **records** (and optionally **packs**) and verify each object's content
   address before using it.
   * Record object bytes are `R`; `SHA256(R)` MUST equal the entry's `sha256`.
   * Pack format: magic `PUNKTIPACK1` (**11 ASCII bytes**, no terminator), then
     `U32(count)` (1..256), then `count` × `LP(record)`. No trailing bytes.
   * When packs are used, the pack membership rule is normative: the multiset of
     record digests in the packs MUST equal the shard's record digest set exactly
     (partitioned into groups of <= 256 in ascending `sha256` order). A missing,
     duplicated, foreign, reversed or truncated pack MUST be rejected.
5. **Decode and verify every `R` locally** with `pwa/punkti/carrier.js`:
   * `SHA256(R)` equals the claimed digest;
   * the decoded MID equals the entry's `mid` and the decoded `h` equals the
     entry's `h`;
   * a record whose validation state is `INVALID-structural` or
     `INVALID-provenance` is **rejected** (counted, not admitted);
   * `UNVERIFIABLE-alg` records are admitted as **candidates** (unverified), never
     as valid.
6. **Dedupe by MID**, with anti-poisoning: an invalid `R` variant for a MID MUST
   NOT evict or suppress a valid `R` for the same MID, and MUST NOT be retained in
   place of one. Keep the valid record; keep the invalid variant only as a
   quarantined candidate.
7. **Scope filtering** client-side: filter by XY prefix and by exact-decimal Z.
   Use the prefix-interval rule from `PUNKTI_0_6_PUBLICATION.md` §4.2:
   `I(p) = [p + "0"*(12-d), p + "z"*(12-d)]`, and a prefix intersects a scope iff
   `I(p).low < scope.XY.high` and `I(p).high >= scope.XY.low` (unbounded cases
   handled). The final, exact selection is always on the record's own `h` via
   `pwa/punkti/spatial.js` `matches()`.
8. **Stale / missing / corrupt / race handling**, all retryable and surfaced as
   typed errors:
   * stale root (`seq` lower than the previously seen `seq` for this base) →
     refresh and retry;
   * equivocal root (same `seq`, different `head`) → retryable error;
   * manifest `seq` != root `seq` → publication race → retry;
   * missing object (HTTP 404 / network error) → retryable, with a bounded retry
     count and backoff;
   * corrupt object (digest mismatch / malformed bytes) → the read attempt fails
     with a `corrupt object` reason; it MUST NOT be silently admitted.
   Expose the error `reason` and an `error_class` of `retryable` or `invalid`.
9. **Unanchored atoms** (`h === ""`, reserved index key `"~"`) MUST be
   representable and browsable.

### Path resolvers

Filesystem layout is NOT normative. The reader MUST accept a resolver. Ship:

* `hexSharded` — the frozen reference layout:
  `root.json`, `manifests/<sha>.json`, `h/<prefix chars joined by '/'>/<sha>.json`,
  `records/<sha[0:2]>/<sha>`, `segments/<sha[0:2]>/<sha>`;
* `flat` — `root.json`, `manifests/<sha>.json`, `h/<sha>.json`,
  `records/<sha>`, `segments/<sha>`;
* `indexMap` — a resolver driven by an explicit path map supplied by the caller
  (e.g. `{ "records/<sha>": "objects/ab/cd/<sha>", ... }`).

Export the resolvers as named functions so the node's publisher and the tests can
agree on one layout.

### Public API

```js
createReader({ fetchImpl, resolver, maxRetries, onProgress })
  -> { readPublication(base, scope) -> { head, seq, admitted, valid, candidates, rejected, records },
       readRecord(base, sha) -> bytes,
       lastError }
```

`readPublication` MUST return the admitted records with their decoded atoms so the
UI can render them, and MUST report `valid`/`candidates`/`rejected` counts.

---

## S2.2 — `pwa/punkti/submit.js`

A standalone ES module (same import rules as above).

```js
createSubmitClient({ baseUrl, fetchImpl, identity })
  -> { submit(atom) -> { ok, address, mid, state, error }, }
```

`submit(atom)` MUST:

* build the record with `pwa/punkti/carrier.js` `encodeRecord` using the caller's
  identity secret key;
* POST it to `${baseUrl}/submit` with a JSON body
  `{ records: [{ address, sha256, record }] }` (base64 `record`, hex `sha256`,
  qualified `address`);
* be **idempotent**: submitting the same record twice MUST be harmless and MUST NOT
  create a second logical atom;
* surface clear, human-usable errors for invalid/rejected records: distinguish
  `invalid` (the node rejected the record: structural/provenance failure),
  `network` (the node was unreachable) and `unsupported` (HTTP status the client
  does not understand). The message MUST name the reason the node gave.

---

## S2.3 — Node: publisher + `/submit` + static publication serving

Python, in `punkti_node/`.

### `punkti_node/publication.py`

Implement the **publisher** and the **static replication reader**, per
`docs/proposals/PUNKTI_0_6_PUBLICATION.md`.

You MAY reuse the frozen reference implementation in
`experimental/punkti-v0.6-publication/src/pubnorm/` — that is the accepted,
Founder-frozen evidence and it is **already vendored in this tree and passing its
70 tests**. Prefer **porting/adapting** it into `punkti_node/publication.py` over
writing a new one from scratch, so the node and the frozen evidence cannot drift.
Keep `experimental/` untouched.

Required:

* `Publisher` that, given the node's admitted records, writes:
  * each record object under the **hexSharded** layout
    (`records/<sha[0:2]>/<sha>`);
  * leaf shards at `h/<prefix chars joined by '/'>/<sha>.json`;
  * the manifest at `manifests/<sha>.json`;
  * the root pointer at `root.json`;
  * optionally replication packs at `segments/<sha[0:2]>/<sha>`
    (`PUNKTIPACK1` + `U32(count)` + `LP(record)` per entry, <= 256 entries).
* **Atomicity**: every immutable object is written to a temp file in the same
  directory, `fsync`ed, then `os.replace`d over the target, then the directory is
  `fsync`ed. The **root pointer** MUST be replaced atomically **only after** every
  immutable object it names is durable. A crash mid-publish MUST leave the
  publication readable at its previous root.
* **Manifest chaining**: first manifest `seq = 1`, `prev = null`; each later
  manifest `seq = previous + 1`, `prev` = previous manifest address.
* **Idempotence**: publishing an unchanged record set MUST NOT advance the root
  (`seq` unchanged) — the same content MUST produce the same root bytes.
* `Reader` that can **replicate a peer over plain static HTTP**: GET the peer's
  root, manifest, shards and records; verify every content address; verify every
  `R` locally with the node's own `carrier.validate`; dedupe by MID; and feed the
  admitted records into the local publisher so the local publication converges.
  No live mesh session, no `/pull`, no `/sync`, no callback.

### `/submit` route

On the bundling node, add a `POST /submit` route that is **user submission**, not
peer replication:

```
POST /submit  -> validate -> dedupe -> persist -> republish static publication
```

* Validate the submitted record locally with `carrier.validate`; reject
  structural/provenance failures with a clear reason and HTTP 400.
* Dedupe by MID against the durable store; a duplicate MUST be accepted
  (idempotent, HTTP 200) and MUST NOT create a second logical atom or a second
  log line.
* Persist durably (the existing `DurableStore` append log).
* Republish the static publication (publish the whole admitted set) and only then
  answer success.
* The response MUST include the record's `address` (MID), `sha256` (SHA256(R)) and
  the resulting publication `seq`/`head`, so the browser can show it.
* **User submission MUST NOT be a peer-sync requirement**: `/submit` is not a
  normative peer endpoint, and `/push` (the legacy mesh peer route) MUST NOT become
  one.

### Serving

* The static publication MUST be served from the **same origin** as the PWA, under
  ordinary static paths (e.g. `/publication/root.json`,
  `/publication/records/<aa>/<sha>`, …), so the PWA can read it through the same
  origin with no CORS and no second host.
* The existing `punkti_node/web.py` static file server must be able to serve the
  publication directory. Extend `StaticWeb` with an extra mounted directory
  mapping (a prefix → directory), keeping the existing path-traversal defences
  intact.
* The publication directory MUST live under the node's persistent data directory
  so it survives a container restart.
* An operator MUST be able to **disable the UI** while still serving and
  replicating Punkti (the existing `web.enabled` flag must not disable publication
  serving).

### Config

Add configuration for the publication directory and for enabling/disabling
publication serving, e.g.:

```yaml
publication:
  enabled: true
  path: /data/publication          # under storage.data_path by default
  packs: false                     # emit replication packs
  serve_prefix: /publication
```

with matching environment overrides (`PUNKTO_PUBLICATION_ENABLED`,
`PUNKTO_PUBLICATION_PATH`, `PUNKTO_PUBLICATION_PACKS`,
`PUNKTO_PUBLICATION_SERVE_PREFIX`), validated in `punkti_node/config.py` like the
other sections. Update the example configs and docs.

---

## S2.4 — Tests

### `pwa/punkti/test-vectors/publication-vectors.json`

Replace the Stage-1 placeholder with the **frozen publication vectors**, copied
**verbatim** from `experimental/punkti-v0.6-publication/vectors.json` (the
`fixtures` map: `index`, `packs`, `missing`, `newer`, `poison`, `small-pack`,
`tamper-manifest`, `tamper-record`, `tamper-shard`, `pack-count`,
`pack-duplicate`, `pack-foreign`, `pack-reversed`, `pack-trailing`,
`pack-truncation`) plus the `vectors` array (V1..V9) and `profile`.

**Copy the bytes exactly. Never regenerate a vector.**

### `pwa/test-punkti-publication.mjs`

A plain `node` script (exit non-zero on failure) that exercises `pwa/punkti/reader.js`
against those frozen vectors and proves:

1. **V1** — reading the `index` fixture yields exactly the expected admitted set,
   `head`, `seq`, `valid_count`, `rejected`, `candidates` and `candidate_count`
   from the vector's `expected` block.
2. **V1 (packs)** — reading the `packs` fixture yields the same logical set.
3. **V2** — `tamper-manifest`, `tamper-shard` and `tamper-record` each produce a
   **retryable** error with reason `corrupt object`.
4. **V3** — `small-pack` reads correctly; `pack-count` produces a retryable
   `invalid object` error.
5. **V4/V5/V6** — the remaining vectors' expected outcomes, as recorded in the
   vector file.
6. **Poison** — the `poison` fixture (same MID, one invalid and one valid `R`
   variant) yields the **valid** record admitted and the invalid variant NOT
   admitted, and the valid variant is not suppressed.
7. **Missing object** — the `missing` fixture yields a retryable `missing object`
   error.
8. **Newer root** — the `newer` fixture is read successfully (a newer root is
   not "stale").
9. **Stale root** — feeding an older root after a newer one yields a retryable
   `stale root` error.
10. **Pack membership** — `pack-duplicate`, `pack-foreign`, `pack-reversed`,
    `pack-trailing` and `pack-truncation` are each rejected.
11. **Path resolver equivalence** — reading the same logical publication through
    the `hexSharded`, `flat` and `indexMap` resolvers yields identical results.

Serve the fixtures over a real local HTTP server (Node's `http` module, no
dependencies) so the reader really performs HTTP GETs — do not stub `fetch` away
entirely; a tiny in-memory `fetchImpl` is acceptable **only** for the resolver
equivalence sub-test.

### `punkti_node/test_publication.py` (new)

Python unittest suite proving:

1. publishing a record set produces a byte-stable publication (same input →
   same root bytes, same `seq`);
2. the manifest chain is correct (`seq`, `prev`);
3. the root advances only after immutable objects are durable (simulate an
   interruption and assert the previous root still reads);
4. the reader over a plain `http.server` reproduces the frozen expected sets;
5. `/submit` validates, dedupes (idempotent), persists and republishes; a second
   identical submit does not add a log line;
6. an invalid record is rejected with a clear reason and HTTP 400;
7. a node can replicate a peer **through the static publication only** (no
   `/pull`, no `/sync`): start node A and node B, submit to A, replicate A→B
   through B's static reader, assert B's publication converges to A's set;
8. restart persistence: the publication and store survive a node restart.

---

## S2.5 — Checks that must pass before you report done

```bash
for f in pwa/punkti/*.js; do node --check "$f"; done
node --input-type=module --check < pwa/punkti/reader.js
node --input-type=module --check < pwa/punkti/submit.js
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests
cmp experimental/punkti-v0.6-mesh/src/carrier.py punkti_node/carrier.py
cmp experimental/punkti-v0.6-mesh/src/spatial.py punkti_node/spatial.py
python3 -m punkti_node --check-config --config node-config.example.yml
```

All must exit 0. Stage-1 checks must still pass.

**Known pre-existing failure** (not yours to fix, but do not make it worse):
`node pwa/test-punkti-client.mjs` fails because the legacy `pwa/sync/punkti-client.js`
still emits the old 12-char geohash `h`. Stage 3 replaces that client. Report its
status honestly.

---

## S2.6 — Report

1. Files changed/added.
2. Real output of every command in §S2.5.
3. The publication-vector cases proved, and the acceptance criteria from
   `docs/CODEX_TASK_22.md` §4 that are now PASS (protocol/browser 1–8, static-only
   9–10, write-to-static 11, node replication 12) — with PASS / FAIL / NOT RUN.
4. Any contradiction or under-specification you hit in the frozen contracts, with
   a concrete counterexample.
5. Confirmation: nothing committed, nothing pushed, nothing deployed, no server
   touched.
