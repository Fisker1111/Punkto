# CODEX TASK 28 — Punkto discovery v1 (static GeoHash density index prototype)

**Status:** ACTIVE
**Base branch:** `origin/main` (f4e6f87)
**Branch:** `experiment/punktto-discovery-index-v1`
**CEO-OS issue:** https://github.com/Fisker1111/CEO-OS/issues/28
**Normative spec (read first, do not rewrite):** `docs/proposals/PUNKTO_DISCOVERY_INDEX_V1.md`

> Spec correction already applied (Codex counterexample from the first run):
> the short-XY example was `abc_0`, which frozen Layer 3 rejects (XY needs
> ≥ 4 characters). The spec now uses `bcde_0 → bcde000000`. Do not re-litigate
> this; any *other* genuine contradiction must still stop the run with a
> concrete counterexample.
>
> Second correction already applied (Codex counterexample from the second run):
> the "stdlib only" wording contradicted the mandatory reuse of
> `punkti_node.publication`, which transitively imports the repo's existing
> `cryptography` dependency. The rule is now "no NEW dependencies beyond
> `node/requirements.txt`". `cryptography` and `PyYAML` are installed in this
> environment. Do not re-litigate this either.

## Goal

Build the **isolated prototype** described in CEO-OS #28 and
`docs/proposals/PUNKTO_DISCOVERY_INDEX_V1.md`: a deterministic, static,
Layer-4 **discovery index** over an already-published frozen Punkti 0.6
publication, so that a blank AI can navigate with HTTP GET only:

```
GET nodes.json → GET <node.index> → occupied GeoHash children → exact h → immutable record bytes
```

## Hard boundaries

* **Do NOT change Punkti 0.6 Layer 3.** No edit to `docs/proposals/PUNKTI_0_6_PUBLICATION.md`,
  no edit to any frozen publication object shape, no change to `root → manifest →
  shards → R`, no change to `punkti_node/publication.py` object schemas.
* **Do NOT deploy.** No production `punkto.xyz`, no node1/node2, no DNS.
* **Do NOT merge** any PR. **Do NOT touch** PR #124, #123, #122, #121.
* **No new dependencies.** Your new modules under
  `experimental/punktto-discovery-index/` must import **only the Python
  standard library** plus the repo's own modules. The repo already depends on
  `cryptography` (see `node/requirements.txt`) and `PyYAML`, and
  `punkti_node.publication` transitively imports `cryptography` via
  `punkti_node/__init__.py` → `carrier.py` — so using the mandatory frozen
  publication APIs (which the task requires) necessarily pulls in the repo's
  **existing** `cryptography` dependency. That is allowed and expected.
  What is forbidden is adding any dependency not already present in
  `node/requirements.txt` (no new pip installs, no numpy, no geohash
  package, no HTTP client library — use `urllib`/`http.server`).
  The environment already has `cryptography` and `PyYAML` installed; verify with
  `python3 -c "import cryptography, yaml"` before assuming, and if either is
  missing, report that as a blocker instead of vendoring a substitute.
* No npm, no JS build step, no bundler.
* Keep everything **inside one new experimental directory** plus the two
  minimal node changes listed in §3.

## 1. Required layout

Create `experimental/punktto-discovery-index/` with:

```
experimental/punktto-discovery-index/
  README.md                     # what this is, how to run it, explicit "prototype" banner
  src/discovery/
    __init__.py
    geohash.py                  # reference standard-GeoHash encoder + vectors + independent check
    index.py                    # index object model, canonical JSON, hashing, validation
    generator.py                # builds the discovery index from a published Punkti 0.6 tree
    client.py                   # GET-only blank-AI traversal client (+ frozen-path fallback)
    metrics.py                  # request/byte accounting vs. the frozen baseline
  tests/
    test_geohash.py
    test_generator.py
    test_client.py
    test_robustness.py
    test_metrics.py
  vectors/geohash-vectors.json  # deterministic vectors (committed)
```

Repo conventions to follow: look at `experimental/punkti-v0.6-publication/` and
`experimental/punkti-v0.6-static/` for structure, and at
`punkti_node/publication.py` for canonical JSON, digest and object-path helpers
(`canonical()`, `digest()`, `object_path()`, `shard_path()`, `root()`, `manifest()`,
`shard()`). **Reuse `punkti_node.publication` validators** to validate the
source publication — do not re-implement the Layer-3 parser.

## 2. Behaviour (the spec is authoritative; this is the checklist)

### 2.1 Generator

Input: a **published Punkti 0.6 static tree directory** containing
`root.json`, `manifests/<head>.json`, `h/<...>/<sha>.json` shards and
`records/<sha[:2]>/<sha>` record objects (the layout produced by
`punkti_node.publication.Publisher`).

Output: a **discovery directory** (e.g. `<out>/index.json` + `<out>/d/<sha>.json`)
holding:

* root object `index.json` with `v = "punkti/discovery/0.1"`,
  `source = {"head": <manifest sha>, "seq": <manifest seq>}`,
  `prefix = ""`, `atoms`, `addresses`, `children` (prefix → descriptor with
  `atoms`, `addresses`, `href`, `sha256`) and optional `unanchored` descriptor;
* one object per occupied prefix at depths **2, 6 and 10** (depth 2 → root child,
  depth 6 → child of depth-2, depth 10 → terminal), each a canonical-JSON file
  named by its own sha256 under `d/`;
* terminal objects carry `entries`: one entry per **distinct exact `h`**, with
  `atoms: [{mid, sha256, href}]`, `href` relative to the discovery root and
  pointing at `../records/<sha[:2]>/<sha>`;
* unanchored (`h == ""`) atoms live in a separate terminal object referenced by
  the root's `unanchored` descriptor — never as a prefix, never as ground level.

Rules:

* All objects embed the **same** `source.head`/`source.seq`.
* **All** referenced objects are written durably *before* `index.json` is
  exposed; `index.json` is exposed atomically (temp file in the same directory
  + `os.replace`). A reader never sees a root referencing a missing child.
* If the publication `head` changes while generating, the run **fails** and
  exposes nothing (re-read the root pointer at the end and compare).
* Generation is **deterministic**: regenerating from the same publication tree
  yields byte-identical files (sorted keys, sorted prefixes, sorted entries).
* Path sanitization: every generated path component is validated
  (`[0-9a-z]{1,12}` geohash prefix; `sha256` = 64 lowercase hex; `href` must
  stay inside the publication tree; reject `..`, absolute paths, traversal,
  control characters, empty components).
* Short published XY addresses (4–9 chars) are indexed under the canonical
  padded-10 leaf prefix (as the frozen publication does), while the **exact**
  `h` string is preserved byte-for-byte in `entries`.
* `atoms` counts record entries; `addresses` counts distinct exact `h` values.
  Several atoms on one exact `h` ⇒ `addresses` 1, `atoms` = atom count.

### 2.2 GeoHash encoder

Dependency-free reference implementation of the **standard** GeoHash algorithm
(base-32 `0123456789bcdefghjkmnpqrstuvwxyz`, longitude first, alternating bit
interleave). Ship:

* `encode(lat, lon, precision)` and `decode(prefix)`;
* `vectors/geohash-vectors.json` with deterministic cases, including
  `57.64911,10.40744 → u4pruydqqvj`, `42.6,-5.6 → ezs42`,
  `0,0 → s00000000000`, `37.7749,-122.4194 → 9q8yy`;
* an **independent second implementation** (different algorithm shape — e.g.
  interval/bisection based, not the same bit loop) that must agree with the
  reference on every vector, plus a test that asserts the two agree;
* the Golden Gate Bridge district approximate coordinate
  `lat=37.8188889, lon=-122.4779444` →
  6 chars `9q8zhu`, 10 chars `9q8zhuwqcp`, 12 chars `9q8zhuwqcpc7`.

### 2.3 GET-only client

`discovery.client` implements a blank-AI traversal that starts with **only** a
base URL and a `nodes.json` URL:

1. `GET nodes.json` → expect `v == "punkti/bootstrap/1"`; pick a node entry;
2. if the entry has an optional `index` member → `GET` it, verify `v`, then walk
   `children` by prefix, verifying each fetched child's bytes against the
   advertised `sha256`; terminal `entries` give exact `h` and atom
   `{mid, sha256, href}`;
3. `GET` each atom `href` and check the bytes hash to the advertised `sha256`
   (**raw record integrity**);
4. **fallback**: if `index` is absent, or a child/terminal object is missing or
   hash-mismatched → use the frozen static read path
   (`publication/root.json` → `manifests/<head>.json` → `h/...` shards →
   `records/...`) and say so in the result.

The client must **distinguish** raw record integrity from cryptographic
authorship: hashing proves the bytes are the addressed bytes; MID recomputation
and Ed25519 signature validation are a separate, optional step. Use the
authoritative frozen reader (`punkti_node.publication.Reader`) for the
cross-check, and assert the immutable source `head` matches the index's
`source.head`.

### 2.4 Metrics

`discovery.metrics` measures, over a real HTTP server (stdlib
`http.server`), the **request count and bytes** for:

* (a) unknown visitor discovering populated regions via the discovery index;
* (b) known-place lookup (exact `h` known) via the discovery index;
* (c) the same two scenarios over the frozen `root → manifest → shards` baseline.

Also report the **actual number and total bytes of generated discovery files**,
and the same for a synthetic corpus of growing size (e.g. 10 / 100 / 1 000 /
10 000 atoms spread over distinct cells) so the "millions of tiny files" risk
is measured. Put the real numbers in the README and in a committed evidence
file `experimental/punktto-discovery-index/evidence/metrics.json`.

## 3. The only two changes outside the new directory

The issue explicitly asks to wire the **optional** discovery URL into the
staging `nodes.json` while preserving compatibility:

1. `punkti_node/config.py`: allow an **optional** `index` member on a
   `bootstrap.nodes[]` entry (still rejecting any other unknown members), and
   validate it as a URL exactly like `base`/`publication`/`submit`.
2. `punkti_node/store.py` `special_route()`: include the `index` key in the
   emitted node entries **only when present** in the config entry. The
   `nodes.json` response keeps `v = "punkti/bootstrap/1"` and the existing
   `id`/`base`/`publication`/`submit` members unchanged.

A node entry **without** `index` must keep working exactly as before, and a
client that ignores `index` must be unaffected. Add/adjust unit tests for both.

## 4. Tests (all required, stdlib `unittest`)

`experimental/punktto-discovery-index/tests/` must cover:

1. **Fixture**: separated populated XY branches; several atoms sharing exactly
   one `h`; other heights in the same XY; a short XY cell; an unanchored atom;
   an empty region. Assert exact unique-address/atom counts at **every** level
   (root, depth 2, depth 6, terminal), valid child URLs, and record object
   hashes. (Build the source publication with the frozen
   `punkti_node.publication.Publisher` over fixture atoms.)
2. **GET-only traversal** from a fresh client with no knowledge of the source
   manifest, plus cross-check of selected entries against the authoritative
   frozen reader and the immutable source `head`; explicit distinction between
   raw record integrity and cryptographic authorship.
3. **Golden Gate**: prefix-based discovery from the approximate bridge
   coordinate — no invented Z, no external geocoder.
4. **Robustness**: deterministic regeneration (byte-identical), stale-snapshot
   linkage, atomic exposure/ordering (root never references a missing child;
   interrupted generation exposes nothing), changing source head (generation
   fails, nothing exposed), missing/corrupt derived child, path sanitization
   (`..`, absolute paths, control chars, bad sha, bad prefix all rejected), and
   fallback when `index` is absent.
5. **Metrics**: request/byte counts and the file-count/byte table.

Tests must run with:

```bash
python3 -m unittest discover -s experimental/punktto-discovery-index/tests -t .
```

Run that, plus the existing suites, and make sure they all pass:

```bash
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
```

If a pre-existing suite fails, verify it also fails on `origin/main` and report
that honestly; do not silently fix unrelated failures.

## 5. Also produce

* `experimental/punktto-discovery-index/README.md` — prototype banner, what it
  is, exact commands, the real measured numbers (files, bytes, request counts,
  baseline comparison), and the explicit statement that the discovery index is
  **not verified content** and the frozen Layer-3 publication is unchanged.
* `docs/DISCOVERY_AI_READ.md` — an **ultra-short** proposed `/ai` READ
  introduction (~20 lines max) showing
  `nodes.json → index.json → child index → records`, with low-level
  verification details linked as optional. No writing pressure, no npm, no
  mandatory JS. It is a proposal document; do **not** modify `pwa/ai.html`.
* `docs/proposals/PUNKTO_DISCOVERY_INDEX_V1.md` already exists (the spec).
  **Do not rewrite it.** If you find a genuine contradiction in it, STOP and
  report it with a counterexample instead of silently changing it.

## 6. Git

* Commit on the current branch `experiment/punktto-discovery-index-v1`.
* Small focused commits; write a clear message body.
* **Do not push.** The Hermes worker reviews the diff and pushes.
* Report: files changed, exact commit SHA(s), tests run and their real output.

## 7. Stop condition

Stop after: implementation + tests + README/evidence/`/ai` proposal are
committed locally on this branch, and you have reported the exact SHA and the
real test output. Do not push, do not open a PR, do not deploy, do not merge.
