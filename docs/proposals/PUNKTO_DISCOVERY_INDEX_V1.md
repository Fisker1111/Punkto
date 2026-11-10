# Punkto discovery v1 — static GeoHash density index (Layer-4 prototype)

**Status:** PROPOSED PROTOTYPE — not a production design commitment, not a protocol
change, not a cutover. Founder-approved experiment: CEO-OS Issue #28.

**Scope:** Punkto **Layer 4** only. The frozen Punkti 0.6 Layer-3 publication
(`root → manifest → hashed shards → R`) is **unchanged**: no object is rewritten,
no member is added to a Layer-3 object, no publication path layout is touched.

## 0. Principle

> A blank AI needs only: `GET nodes.json` → `GET <node.index>` → follow occupied
> GeoHash child links → pick an exact `h` → `GET` immutable records.

The discovery index is a **derived, static, read-only side index** over an
already-published Punkti 0.6 publication. It never becomes a second source of
truth: it is bound to one publication manifest `head` and is useless without it.

Explicitly out of scope: relevance ranking, topics, author/user analytics,
full-text search, dynamic search endpoints, npm, a GUI, a geocoding server,
a new publication protocol, and any change to the frozen publication bytes.

## 1. Versioned JSON schema

Version string: `punkti/discovery/0.1`.

Every discovery object is canonical JSON (same rules as the frozen publication:
UTF-8, sorted member names, no insignificant whitespace, no trailing newline,
integers only, no duplicate member names) and is served as `application/json`.

### 1.1 Common members

| Member | Type | Meaning |
|---|---|---|
| `v` | string | exactly `punkti/discovery/0.1` |
| `source` | object | `{"head": <manifest content address>, "seq": <manifest seq>}` — the immutable snapshot binding |
| `prefix` | string | the GeoHash prefix this object describes; `""` for the root object |
| `atoms` | integer | number of indexed atom records below this prefix (≥ 0) |
| `addresses` | integer | number of **distinct exact `h` strings** below this prefix (≥ 0) |

`atoms` counts record entries (one entry per indexed atom record variant);
`addresses` counts distinct exact `h` values. For an exact `h` carrying several
atoms, `addresses` counts 1 and `atoms` counts the number of atoms.

### 1.2 Root object — `index.json`

```json
{
  "atoms": 0,
  "children": {},
  "prefix": "",
  "source": {"head": "<64 hex>", "seq": 1},
  "v": "punkti/discovery/0.1"
}
```

`children` maps a child GeoHash prefix to a child descriptor:

```json
"children": {
  "9q": {"atoms": 4, "addresses": 2, "href": "d/<sha256>.json", "sha256": "<64 hex>"}
}
```

A child descriptor always carries: child prefix counts (`atoms`, `addresses`),
a **static relative** `href`, and the `sha256` of the child object's exact bytes.
`href` is relative to the **discovery root directory** (the directory that
contains `index.json`).

### 1.3 Terminal object (leaf)

The terminal object carries the exact addresses and their atoms:

```json
{
  "atoms": 2,
  "entries": [
    {"atoms": [
        {"href": "../records/ab/abcd...", "mid": "punkti/0.6:<64 hex>", "sha256": "<64 hex>"}
      ],
     "h": "9q8zhu0000_0"}
  ],
  "prefix": "9q8zhu0000",
  "source": {"head": "<64 hex>", "seq": 1},
  "v": "punkti/discovery/0.1"
}
```

* `h` is the **exact** address as published, preserved byte-for-byte — short XY
  addresses stay short, and `z` keeps its published spelling.
* Atom entries are `{mid, sha256, href}`; `href` is relative to the discovery root
  directory and points at the immutable record object in the same publication
  (so, from `<publication>/discovery/`, it is `../records/<sha[:2]>/<sha>`).
* `mid` is the atom identity. It is **not** a spatial or HTTP locator.

### 1.4 Unanchored atoms (`h == ""`)

Unanchored atoms are represented **separately**, never as a prefix and never as
ground level. The root object carries:

```json
"unanchored": {"atoms": 1, "addresses": 1, "href": "d/<sha256>.json", "sha256": "<64 hex>"}
```

The referenced object is a terminal object with `prefix: ""` and the same
`entries` shape, whose only `h` value is `""`.

## 2. Branch levels and partitioning

The discovery tree uses **three** prefix levels: depth **2**, depth **6**, depth
**10**. Rationale:

* depth 2 matches the frozen publication's own manifest index granularity;
* depth 6 is coarse enough to be a "region" an AI can reason about from an
  approximate coordinate, and fine enough to be sparse in practice;
* depth 10 is the frozen canonical padded leaf depth, so the terminal level maps
  1:1 onto publication leaves and no new address spelling is invented.

Occupied prefixes only produce objects; empty prefixes produce nothing.
`~` (the frozen unanchored index key) is never a prefix.

Prefixes are always the **canonical padded-10 publication leaf** prefixes,
ascending. A short published XY address (`bcde_0`, i.e. the shortest legal
XY length of 4) is indexed under leaf `bcde000000` — exactly like the frozen
publication (`punkti_node.publication.leaf_key`) — while its exact `h`
(`bcde_0`) is preserved verbatim in the terminal `entries`. XY shorter than
4 characters is not a legal frozen address at all.

**Partitioning must be measured, not assumed.** The prototype reports, for a
synthetic corpus of increasing size, the number of generated discovery files and
their total bytes, so that "millions of tiny files" is a measured risk, not a
hypothetical one.

## 3. Snapshot binding, ordering and atomic exposure

1. The generator reads the publication root pointer, then the manifest at
   `head`, and validates both with the frozen reader/validator code.
2. Every generated object embeds the same `source.head` / `source.seq`.
3. **All** referenced objects (child and terminal) are written durably *before*
   the root pointer `index.json` is exposed.
4. `index.json` is exposed atomically (write to a temporary file in the same
   directory, then `os.replace`). A reader therefore never sees a root pointer
   that references a missing child.
5. If the publication's `head` changes while the generator runs, the run fails
   and exposes nothing; mismatched snapshots are never silently combined.
6. A stale snapshot is acceptable **only if marked**: the root object's `source`
   binding always names the exact manifest the index was built from. If the
   publication has moved on, the index is stale by construction and a client
   that wants freshness must compare `source.head` with the publication root.

## 4. Client behaviour (GET-only)

A fresh client that knows **only** a base URL:

1. `GET <base>/nodes.json` → `{"v": "punkti/bootstrap/1", "nodes": [...]}`. Each
   node entry may carry an **optional** `index` member (a URL). Existing members
   (`id`, `base`, `publication`, `submit`) and the bootstrap version are
   unchanged; a client that ignores `index` keeps working.
2. `GET <node.index>` → the root object. Verify `v`; verify the child/terminal
   object bytes against the advertised `sha256`.
3. Walk `children` by prefix to the exact address; read `entries`.
4. `GET` each atom's `href` to obtain the immutable record bytes.

Failure handling:

* `index` absent → fall back to the frozen static-publication read path
  (root → manifest → shards → records). This fallback is mandatory and tested.
* a child object missing or hash-mismatched → treat the discovery branch as
  unusable and fall back to the frozen read path. Never trust unverified bytes.

**Integrity vs. authorship.** Verifying that fetched bytes hash to the advertised
`sha256` proves *raw record integrity* (the bytes are the bytes the publication
addressed). It does **not** prove cryptographic authorship. Authorship requires
recomputing the MID and validating the Ed25519 signature over the canonical atom
— a separate step the prototype demonstrates with the authoritative frozen reader
but does not conflate with index integrity.

## 5. Reference GeoHash encoder

The prototype ships a tiny, dependency-free reference implementation of the
**standard** GeoHash algorithm (base-32 alphabet
`0123456789bcdefghjkmnpqrstuvwxyz`, longitude first, alternating bit
interleaving) plus deterministic vectors.

Validation is required against **independent** vectors and an **independent**
encoding path, not only against itself:

* published reference vectors (e.g. `57.64911,10.40744 → u4pruydqqvj`;
  `42.6,-5.6 → ezs42`; `0,0 → s00000000000`; San Francisco
  `37.7749,-122.4194 → 9q8yy`);
* a second, independently written encoder (different algorithm shape) must
  agree with the reference encoder on every vector.

**Golden Gate Bridge example.** Using the official district approximate bridge
coordinate `lat=37.8188889, lon=-122.4779444`:

| precision | GeoHash |
|---|---|
| 6 | `9q8zhu` |
| 10 | `9q8zhuwqcp` |
| 12 | `9q8zhuwqcpc7` |

The 6-character region `9q8zhu` is the coarse discovery prefix; the bridge spans
many finer cells, so discovery by prefix — not precise named-landmark lookup —
is what the prototype demonstrates. No Z is invented, and no geocoding service
is contacted during the test.

## 6. Acceptance tests

1. **Fixture.** An isolated fixture with: separated populated XY branches; several
   atoms sharing exactly one `h`; other heights in the same XY; a short XY cell;
   an unanchored atom; and an empty region. Assert exact unique-address and
   atom counts at **every** level, valid child URLs, and record object hashes.
2. **GET-only traversal.** A fresh client with no knowledge of the source
   manifest walks `nodes.json → index → branches → exact address → record bytes`
   using only HTTP GET and JSON. Raw record integrity is asserted separately
   from cryptographic authorship, and selected entries are cross-checked against
   the authoritative frozen reader and the immutable source `head`.
3. **Golden Gate.** Prefix-based discovery from the approximate bridge
   coordinate, without inventing Z and without any external geocoder.
4. **Robustness.** Deterministic regeneration (byte-identical), stale-snapshot
   linkage, atomic exposure/ordering, changing source head, missing/corrupt
   derived child, path sanitization, and fallback when `index` is absent.
5. **Metrics.** Report the **actual** number and total bytes of generated
   discovery files, and the request count and byte size for (a) an unknown
   visitor discovering populated regions and (b) a known-place lookup — compared
   against the existing `root → manifest → shards` GET baseline.
6. **`/ai` READ introduction.** An ultra-short proposed introduction showing
   `nodes.json → index.json → child index → records`, with low-level
   verification details linked as optional. No writing pressure, no npm, no
   mandatory JS.
