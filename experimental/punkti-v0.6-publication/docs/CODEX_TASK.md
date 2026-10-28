# Codex Task — Punkti 0.6 normative static publication + conformance vectors

Status: **ACTIVE — implement on this branch only. Do NOT merge to main. Do NOT deploy.
Do NOT tag.** Source of truth: CEO-OS Issue #21.

## Read first (in this order)

1. `docs/proposals/PUNKTI_0_6_PUBLICATION.md` — **the normative contract you must
   implement.** Read it completely before writing anything.
2. `docs/proposals/PUNKTI_0_6_LAYER3_RESET.md` — the accepted L3 carrier
   (`C`/`S`/MID/`R`, validation states). Do not change it.
3. `docs/proposals/PUNKTI_0_6_SPATIAL_XY_Z.md` / the accepted `h = <xy>_<z>` codec —
   do not change it.
4. `experimental/punkti-v0.6-static/` — the accepted #20 experiment
   (`src/staticpub/*`, `docs/SPEC.md`, `tests/*`). **Reuse it**; do not rebuild from
   scratch. It is the evidence base and several of its mechanisms (content
   addressing, publish ordering, anti-poisoning stores, clean-room reader) are
   already proven and measured.

Also read `experimental/punkti-v0.6-mesh/src/carrier.py` and
`experimental/punkti-v0.6-mesh/src/spatial.py`: they are the **approved, unmodified**
carrier and spatial codec. Import them; never fork or edit them.

## Branch / base

- Work branch (already checked out): `draft/punkti-0.6-static-first`
- Base commit: `f54c981` ("Promote accepted static-first replication architecture")

## Deliverable layout

Create a new self-contained experiment package `experimental/punkti-v0.6-publication/`:

```
experimental/punkti-v0.6-publication/
  README.md                 # what this is, how to run everything
  src/pubnorm/__init__.py
  src/pubnorm/objects.py    # logical objects: canonical JSON, root, manifest, shard, record, pack
  src/pubnorm/publisher.py  # reference publisher (publish ordering, determinism, idempotent retry)
  src/pubnorm/reader.py     # reference reader (staged admission, all §9 failure classes)
  src/pubnorm/independent.py# INDEPENDENT implementation of the same contract (see below)
  src/pubnorm/vectors.py    # vector definitions + generator
  tests/test_vectors.py     # V1..V9 normative vector suite
  tests/test_hostile.py     # hostile / failure suite
  tests/test_convergence.py # V9 two-implementation convergence over a dumb static origin
  scripts/                  # generator / runner entry points
  vectors.json              # generated deterministic vectors (committed)
  docs/NORMATIVE_VECTORS.md # generated human-readable vector document (committed)
  docs/IMPLEMENTATION_EVIDENCE.md  # test results, commands, measured evidence
```

The normative spec document itself is **already written by the spec author**:
`docs/proposals/PUNKTI_0_6_PUBLICATION.md`. To be clear about ownership — that
document is the contract, and it is not yours to rewrite. If you believe the
contract is internally inconsistent, contradictory with the accepted L3/spatial
profiles, or unimplementable as written, **STOP and report the specific
counterexample** instead of silently editing the contract or inventing a
different design. Everything below must be built to satisfy that document
exactly as written.

## Hard requirements

1. **Implement the normative contract exactly.** Every §-rule in
   `PUNKTI_0_6_PUBLICATION.md` is a MUST. In particular:
   - canonical JSON: UTF-8, sorted member names by code point, no whitespace, no
     trailing newline, integers only, duplicate member names rejected;
   - root pointer = exactly `{"head":…,"seq":…,"v":"punkti/pub/0.6"}`, no
     timestamp, no extra members;
   - manifest = exactly `{"index":…,"pack_count":…,"prev":…,"record_count":…,"seq":…,"v":…}`;
   - shard = exactly `{"children":…,"packs":…,"prefix":…,"records":…,"v":…}`, with the
     interior/leaf rules;
   - the reserved index key `"~"` for unanchored (`h=""`) records, `"~"` shard is a
     leaf with `prefix == "~"` and never mixes in anchored records;
   - index geometry: leaf depth `D = 10`, leaf prefix `K(xy)[:10]` where
     `K(xy) = xy.ljust(12,"0")`; manifest index lists depth-2 prefixes; prefix chain
     verified while walking;
   - record object bytes = the exact canonical `R`; content address = `SHA256(R)`;
   - pack framing `b"PUNKTIPACK1" || u32be(count) || count × (u32be(len) || R)` with
     the normative membership rule (leaf record entries sorted by `sha256` hex,
     consecutive groups of at most 256);
   - publish ordering records → packs → shards → manifest → atomic root replace;
     interrupted publish leaves the previous root/manifest readable; republishing
     the same logical state is byte-identical;
   - reader: staged admission (verify all in-scope objects before admitting
     anything), exact §9 failure classes (stale root, equivocal root, missing
     object, corrupt object, publication race) each failing the whole attempt with
     no partial admission, per-record rejection for invalid carrier, candidates
     store keyed by `SHA256(R)` for `UNVERIFIABLE-alg` that never displaces a
     valid MID;
   - Z filtering is post-fetch; XY prefix filtering happens before fetching record
     content;
   - no completeness/freshness claim anywhere in behaviour or wording.

2. **Two independent implementations.** `src/pubnorm/independent.py` MUST be an
   independent implementation of the same normative contract — it must NOT import
   `objects.py`, `publisher.py` or `reader.py`. It MAY import the approved
   `carrier`/`spatial` modules (those are the accepted L3 codec, not the
   publication contract). It should be structured differently (e.g. a flat
   functional parser, its own canonical-JSON encoder) so that agreement is real
   evidence and not tautology. State this boundary in the module docstring and in
   `README.md`.

3. **Deterministic vectors.** `vectors.json` and `docs/NORMATIVE_VECTORS.md` are
   generated deterministically from the code (a generator script under
   `scripts/`), committed as artifacts, and regenerated to prove determinism
   (byte-identical on re-run). No timestamps, no random ports, no wall-clock, no
   environment-dependent values in the artifacts. Key material for fixtures is
   derived from a fixed seed literal, exactly like the existing freeze-candidate
   vectors in `experimental/punkti-v0.6-freeze/`.
   Vectors must be machine-checkable and must cover, at minimum, V1–V9 as listed
   in §13 of the normative spec:
   - V1 root → manifest discovery;
   - V2 immutable object digest verification (including tamper detection on a
     manifest, a shard and a record);
   - V3 pack decoding (valid decode, count mismatch, truncation, trailing bytes,
     foreign record not belonging to the leaf);
   - V4 exact `R`/MID verification (bytes preserved byte-for-byte, MID recomputed
     from `C` equals the advertised MID);
   - V5 same MID with distinct `R` digests, and an invalid (forged) variant: the
     valid record survives, the invalid one is rejected, the valid MID is not
     poisoned;
   - V6 XY prefix selection (prefix selection before content fetch; unanchored
     `"~"` selection only by an unrestricted scope);
   - V7 negative and decimal Z preservation (exact decimals, negative Z, Z
     canonicalisation unchanged);
   - V8 stale root, missing object, corrupt object → whole attempt fails, nothing
     admitted, retry is idempotent;
   - V9 two independent implementations converge from static-only origins.
   Each vector records inputs and expected observable outcomes
   (digests, admitted MIDs, admitted/rejected counts, error class), not prose.

4. **Real HTTP, static only.** Vector and hostile tests MUST exercise a real
   static HTTP origin (stdlib `http.server` / `python3 -m http.server` is fine) over
   loopback, not mocked function calls. Replication MUST work with the publisher
   process stopped — serve the published directory with a dumb static server and
   replicate from a separate reader. Do not require any dynamic endpoint
   (`/hello`, `/push`, `/pull`, `/sync`) to exist.

5. **Hostile / failure suite.** Must cover, with real assertions on observable
   behaviour: truncation of every object kind; stale head; missing manifest,
   missing shard, missing record, missing pack; corrupt object (digest mismatch)
   for every object kind; digest naming mismatch; replay/duplicate records;
   reordered publication visibility (root advanced before objects present);
   selective withholding (a peer omits objects); interrupted publish (fail after
   objects / after shards / after manifest) leaving the previous state readable;
   long offline/rejoin; publication race (root changes mid-read); oversized
   fields. No malformed or corrupt object may ever enter the valid store, and a
   missing referenced object MUST NOT produce a false admission or checkpoint.

6. **Stdlib test runner.** Tests must run with
   `python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests -v`
   (stdlib + `cryptography`, which is already installed). No pytest, no new
   dependencies. If you need a fixture signing helper, derive the Ed25519 key from
   a fixed seed exactly as `experimental/punkti-v0.6-static/src/staticpub/carrier_io.py`
   does.

7. **Evidence.** `docs/IMPLEMENTATION_EVIDENCE.md` must record: exact commands run
   and their pass counts; the vector regeneration determinism check (byte-identical
   on re-run); the measured result of the static-only origin experiment; and any
   deviation from the normative contract (there should be none — if there is, say
   so plainly).

8. **Do not touch** `pwa/`, `relay/`, `core/`, `deploy/`, `experimental/punkti-v0.6-mesh/`,
   `experimental/punkti-v0.6-static/`, `experimental/punkti-v0.6-freeze/`,
   `experimental/punkti-v0.6-hostile/`, or the existing `docs/proposals/PUNKTI_0_6_*.md`
   documents (except adding the new file
   `docs/proposals/PUNKTI_0_6_PUBLICATION.md`, which already exists — do not
   modify it; if you find a genuine error in it, report it in `docs/IMPLEMENTATION_EVIDENCE.md`
   and in your final report instead of editing).

9. **Scope discipline.** This is a specification/conformance task. Do not add
   features, dynamic mesh mechanisms, deployment, release tagging, or protocol
   freeze. Do not change C/S/MID/R or the spatial codec to suit the publication.

## Acceptance criteria

- [ ] `python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests -v`
      passes with zero failures and zero errors; report the exact count.
- [ ] `vectors.json` and `docs/NORMATIVE_VECTORS.md` regenerate byte-identically.
- [ ] V1–V9 present and each asserts machine-checkable outcomes.
- [ ] The independent implementation agrees with the reference implementation on
      every vector and in the convergence test, from static-only origins, with the
      publisher stopped.
- [ ] Hostile suite passes: no corrupt/missing object ever causes an admission or
      a checkpoint advance.
- [ ] `docs/IMPLEMENTATION_EVIDENCE.md` written with real command output.
- [ ] Every normative §-rule implemented; deviations reported explicitly (expected:
      none).

## Commit expectation

Commit on `draft/punkti-0.6-static-first` in small, focused commits (e.g. one for the
implementation package, one for generated vectors + evidence). Do NOT push. Do NOT
open a PR. The spec author reviews, pushes and opens the PR. Report the exact final
SHA(s) and the files changed.

## Stop condition

Stop when the acceptance criteria are met, the work is committed on this branch, and
you have reported: exact SHAs, files changed, test commands and pass counts, the
vector-regeneration determinism result, the static-only convergence result, any
deviation from the normative contract, and any genuine inconsistency you found in
`docs/proposals/PUNKTI_0_6_PUBLICATION.md`.
