# Codex follow-up task — benchmark rigor + leaf-depth experiment

Context: the first implementation pass is complete (src/staticpub, 20 tests
passing, report written). The measurement pass is too weak to back a founder
decision. Fix the measurement layer ONLY — no protocol/codec changes, no
changes outside `experimental/punkti-v0.6-static/`.

Read first: `experimental/punkti-v0.6-static/docs/SPEC.md`,
`docs/CODEX_TASK.md`, `src/staticpub/bench.py`, `src/staticpub/publisher.py`,
`src/staticpub/reader.py`, `docs/STATIC_PUBLICATION_REPORT.md`.

## Problem 1 — the depth-10 leaf degeneracy (architectural finding)

`leaf_key()` truncates the XY to 10 characters, and canonical precision is 10,
so EVERY atom normally lands in its own leaf. The measured cost is visible:
mode A, 5 000 atoms, fresh subscriber = **10 509 HTTP requests** (≈ one
request per record plus ≈ one per hierarchy shard).

This defeats the whole point of "static publication exploits XY prefix
locality". The right question the founder asked is: how many requests does a
reader need to cover a region, and how much does the layout choice cost?

Do this:

1. Make the leaf depth a **configurable publisher/reader parameter**
   (`leaf_depth`, integer between 2 and 10; the hierarchy above the leaf keeps
   the existing depth-2 manifest index). Default may stay 10 for backward
   compatibility, but the benchmark must sweep it.
   - The leaf shard at depth D lists the records whose XY starts with that
     D-character prefix.
   - `manifest.depth` must be updated to record the leaf depth (it currently
     says 2, meaning "index depth"); use a distinct field or a documented
     meaning — keep the reader and the clean-room reader consistent, and keep
     `root.json`/`manifest` shapes documented in the report.
   - The reader's range selection MUST still work: a subscription XY range must
     visit only the shards that intersect it.
   - Update the clean-room reader (`cleanroom.py`) accordingly.
2. Sweep leaf depth ∈ {2, 4, 6, 8, 10} for the static modes and report
   requests / transferred bytes / useful bytes / wall time per (depth, mode,
   scenario). The hypothesis to test: a shallower leaf depth (≈4–6) collapses
   the request count for all-space and region subscriptions, at the cost of
   coarser filtering (records of a prefix fetched together even if only some
   match the Z filter).
3. Recommend ONE leaf depth for the 0.6 profile, with the measured trade-off.
   This is a headline result for the founder — put it in the report.

## Problem 2 — unmatched dataset sizes in the Mesh comparison

The current comparison is static@5 000 vs mesh@1 000, which is not a
comparison. Re-run the dynamic Mesh baseline on the **same 5 000-atom dataset
as the static runs** (same records, same subscriptions, same scenario names),
so requests/bytes/wall are comparable. Additionally run the static profile on
1 000 atoms so both sizes exist for both systems.

Mesh baseline note: the mesh node has no equivalent of a static publication;
the honest comparison is "cost to converge a subscriber over HTTP", so report
the mesh's pull requests, transferred records, estimated transferred bytes and
wall time, and the static side's HTTP requests, transferred bytes, useful
bytes and wall time. Do not hide that the two wire formats differ.

## Problem 3 — repeats and the 100 000-atom scenario

- Run each micro-scenario at least **3 times** and report the **median**
  (keep min/max too). Change `run_all`'s default to `repeats=3` and run it.
- The 100 000-atom case currently only GENERATES records; it never publishes
  or replicates. Actually run it: build a source node with 100 000 atoms,
  publish (record publish wall/CPU), then run a fresh-subscriber replication
  (report requests/bytes/wall) for mode A and mode B at the recommended leaf
  depth. Apply a hard time budget (e.g. 45 min for the scale case); if a
  scenario cannot finish inside the budget, report it honestly with the
  partial numbers and state exactly what was not completed. Do not fake or
  extrapolate numbers.
- Report **storage amplification** too: bytes on disk of the published tree
  vs sum of raw record bytes (for mode A and mode B), and **rebuild cost**
  (time to republish the same store).

## Problem 4 — concurrency

Measure "many concurrent readers" if practical: N ∈ {1, 8} readers fetching
the same publication concurrently from the dumb static server, reporting
aggregate requests/bytes/wall. The static server's origin work per request
must be recorded (the server is the same origin in all cases; report the
per-request origin cost explicitly).

## Deliverables (regenerate in place)

- `evidence/bench_static.json` — now with: leaf-depth sweep, matched 1 000 and
  5 000 datasets, repeats ≥ 3 with medians, the real 100 000-atom run honesty
  flag, storage amplification and rebuild cost, concurrency numbers.
- `evidence/bench_mesh.json` — mesh baseline on 1 000 and 5 000 atoms with the
  same scenario names, repeats ≥ 3, medians.
- `docs/BENCHMARK.md` — refreshed tables (leaf-depth sweep table, matched
  static-vs-mesh tables at both sizes, scale table, concurrency table) with an
  explicit note on measurement method (loopback, stdlib static server, warm
  FS cache, therefore comparative rather than absolute latency).
- `docs/STATIC_PUBLICATION_REPORT.md` — update sections 1, 7 and 8 with the
  new numbers and the leaf-depth finding, keep the 12-section structure, and
  keep the honest limitations. If the recommendation changes because of the
  new data, say so and explain why.
- `README.md` — update the benchmark command (`repeats` default) and the run
  time expectation.
- `evidence/test_results.json` — re-run the suite and store the result.

## Constraints

- Stay inside `experimental/punkti-v0.6-static/`. The mesh experiment stays
  read-only.
- The APPROVED carrier and XY_Z codec (`experimental/punkti-v0.6-mesh/src`)
  must not be modified or forked.
- All 20 existing tests must still pass; add tests for the leaf-depth
  parameter (e.g. depth 4 and 6 configurations) and for the manifest/reader
  changes you make. No test may be weakened or deleted to make a change pass.
- No invented numbers: every figure in the docs must come from the committed
  evidence JSON.

## Stop condition

When the evidence files and docs are regenerated and the suite passes, report:
files changed, test counts, the leaf-depth sweep table, the matched
static-vs-mesh tables, the 100 000-atom outcome (completed or not, with the
budget), the recommended leaf depth, and whether the recommendation in the
report changed. Do not push; do not commit if the git dir is read-only —
just report.
