# Codex task — Punkti 0.6 static publication + read-only replication prototype

Read first, in this order:
1. `AGENTS.md` (repo root)
2. `experimental/punkti-v0.6-static/docs/SPEC.md` — the normative experimental
   profile you MUST implement. It is written by the orchestrator to prevent
   profile drift; do not invent a different profile. If you find the spec
   contradictory or unimplementable, STOP and report the exact contradiction in
   your final report instead of silently changing the spec.
   Two tensions are ALREADY RESOLVED by the orchestrator and are NOT a reason
   to stop: (a) shard addressing is `h/<prefix>/<sha256>.json` with superseded
   versions retained; (b) Z textual encoding limits are inherited from the
   APPROVED codec (`parse_h` ≤ 32 chars, `parse_z` ≤ 27 chars) — do NOT change
   or bypass the codec, use values that fit it, and record the tension as a
   FINDING in the report. Any FURTHER tension you find between prose and the
   approved codec: record it as a FINDING, implement around it using the
   approved codec's actual behaviour, and CONTINUE — only stop for a
   contradiction that would block a required capability.
3. `experimental/punkti-v0.6-mesh/src/carrier.py` and
   `experimental/punkti-v0.6-mesh/src/spatial.py` — the APPROVED carrier and
   XY_Z codec. Import/reuse them; never fork or rewrite them.
4. `experimental/punkti-v0.6-mesh/src/mesh.py` — the current dynamic Mesh
   (PUSH + Range PULL). Read only; you must NOT modify it. You need it only
   for the measurement comparison.

## Goal

Build the reference prototype + evidence that proves (or disproves) the
static-first hypothesis of CEO-OS Issue #20:

> Ordinary HTTP serves Punkti; other nodes replicate Punkti by reading what a
> publication serves.

The acid test: publish, stop the daemon completely, serve only the generated
directory with a dumb static HTTP server, and show that a separate node can
still discover, fetch, independently verify, admit/dedupe, republish and
converge.

## Scope — create ONLY inside `experimental/punkti-v0.6-static/`

```
experimental/punkti-v0.6-static/
  README.md                      # how to run everything, exact commands
  docs/SPEC.md                   # (already written; do not delete)
  docs/STATIC_PUBLICATION_REPORT.md   # the founder-facing deliverable (see below)
  src/staticpub/__init__.py
  src/staticpub/carrier_io.py   # helpers to build/parse exact R bytes using the approved carrier
  src/staticpub/publisher.py    # publisher: store -> static publication tree
  src/staticpub/reader.py       # read-only replicator: static GET/HEAD only
  src/staticpub/store.py        # node store: valid store + candidate store, dedupe
  src/staticpub/httpsource.py   # local filesystem HTTP source (dumb static server)
  src/staticpub/bench.py        # index-only vs pack measurements + mesh comparison
  src/staticpub/harness.py      # node lifecycle helpers for tests/benchmarks
  tests/                         # unittest suite (real HTTP only, no mocks of the wire)
  evidence/*.json                # machine-readable evidence
```

Do NOT touch anything outside `experimental/punkti-v0.6-static/` — no changes
to `experimental/punkti-v0.6-mesh/`, `experimental/nairobidot-l3/`, `pwa/`,
`core/`, `relay/`, `docs/proposals/` or any deployment file. No production
deployment, no main merge, no tag, no 0.6 freeze.

Language: Python 3.10+ standard library only, plus `cryptography` (already
installed) — exactly like the existing mesh experiment. No new dependencies.
Use `unittest` (the repo style). Use `cryptography`'s Ed25519 for test keys.

## Required capabilities

### A. Publisher
- Builds a publication tree per SPEC §2 from a node's valid store.
- Content-addressed objects; `SHA256` name == `SHA256` of bytes.
- Deterministic: publishing the same store twice yields byte-identical files.
- Publish ordering per SPEC §2.1 with fsync + atomic `root.json` replacement.
- Supports mode A (index-only: readers fetch record objects) and mode B (packs:
  shards also reference packs that bundle exact `R` bytes; canonical record
  objects are still published).
- Builds XY hierarchy shards per SPEC §5 (depth-2 manifest index, geohash
  characters as levels, leaves at depth 10) with a `records` list of
  `(mid, sha256, h)`.
- Recovery: if a previous publish was interrupted (missing objects), the next
  publish completes it deterministically and the publication stays readable
  at the previous head until the new `root.json` is swapped in.

### B. Reader / replicator
- Uses ONLY static GET (HEAD optional) semantics. No POST, no query API, no
  live daemon at the serving side.
- Imperative algorithm per SPEC §4.
- Independently verifies: content-address of every fetched object, then
  structural + cryptographic validation through the approved carrier
  (an invalid or corrupt object MUST NOT enter the valid store).
- Admission/dedup per SPEC §4.6: valid store keyed by MID, unverifiable
  variants in a separate candidate store keyed by `SHA256(R)`; an invalid
  variant cannot poison a valid MID.
- Publishes its own accepted set back out via the publisher (republish).
- Can read a publication from a plain static HTTP server (e.g.
  `python3 -m http.server`) — this is the acid test.

### C. Node harness
- A node = store + publisher + reader + subscriptions. Nodes A, B, C can
  publish, replicate from each other, and republish.

### D. Clean-room reader proof (where practical)
- Implement an INDEPENDENT minimal reader that does NOT import the reference
  publisher/reader modules: it must parse `root.json`, manifests, shards,
  records and packs from raw bytes with its own code. It MUST reach the same
  accepted record set as the reference reader on the same publication.
  Put it in `src/staticpub/cleanroom.py`. State honestly in the report what
  the clean-room reader does and does not re-implement (e.g. carrier
  validation may be reused — say so explicitly and justify it).

### E. Test suite (required scenarios — all 10, mandatory)
1. `A={A,B,C,D}`, `B={C,D,E,F}` -> both reach the union.
2. Same MID with an invalid and a valid `R` variant -> the invalid one cannot
   poison the valid one.
3. Same XY, different Z -> both records coexist; Z filter selects correctly.
4. XY-prefix-limited replication -> only the matching region is fetched
   (assert on requests and on bytes).
5. Negative and large/high Z values -> handled, canonical decimal preserved.
   Z encoding limits are inherited from the APPROVED codec (`parse_h` ≤ 32
   chars for the whole address, `parse_z` ≤ 27 chars) and MUST NOT be changed
   or bypassed: use the largest canonical values that fit the approved codec.
   Record the "unbounded Z prose vs codec character limit" tension as an
   explicit FINDING in the report (section 9 and section 11).
6. Offline source daemon with static files still served -> replicate
   successfully with the daemon stopped.
7. Stale root then refresh -> reader detects the change (and does not blend
   stale state silently).
8. Missing referenced immutable object during a publication race -> no false
   checkpoint / no admission of unverifiable data.
9. Source disappearance and later reappearance -> reader recovers, idempotent.
10. Three-node partial-overlap convergence -> all three reach the union.

Plus hostile cases from SPEC §9: truncation, stale head, missing
segment/object, corrupt static object, mismatched digest, replay/duplicate,
reordered publication visibility, selective withholding, long offline/rejoin.

Also required:
- dumb-server proof test: publication served by `python3 -m http.server`
  (or an equivalent stdlib static server) with NO Punkti daemon running.
- a test proving a "normal static web server/container-shaped" path works too
  (e.g. serving the same directory from a different stdlib server with a
  different root path / different port) — i.e. the paths are relative to the
  served directory and nothing depends on the origin.
- CDN/object-store-shape proof: the SAME publication directory must be usable
  when served under a different base prefix path (e.g. mounted at `/cdn/punkti/`)
  — implement by making the reader's base URL/path explicit (no hardcoded
  absolute paths). Test it.

### F. Measurements / benchmarks (bench.py)
Baseline for comparison = the existing dynamic Mesh PUSH + Range PULL
(`experimental/punkti-v0.6-mesh/src/mesh.py`, `tests/measure.py`). Do NOT
modify the mesh modules; import them read-only for the comparison (note: the
mesh package imports are flat module names — put its `src` on `sys.path`).

Measure at least:
- 5,000 atoms; 100,000 atoms if practical within resource limits (measure and
  report actual counts; if 100k is impractical, report why and the largest
  achieved);
- 100% overlap; 0% overlap;
- fresh subscriber;
- one-new-atom incremental catch-up;
- one XY-prefix subscription;
- broad/all-space subscription.

Record per scenario: HTTP requests, transferred bytes, useful bytes, wall time,
CPU/memory if practical, number and size of mutable files, static-server
origin work (what the dumb server did per request), and behaviour with many
concurrent readers if practical.

Compare mode A (index-only) vs mode B (packs) on the SAME data, and compare
both against the dynamic Mesh baseline. Output:
- `evidence/bench_static.json` (raw numbers)
- `evidence/bench_mesh.json` (dynamic baseline numbers)
- `docs/BENCHMARK.md` (human-readable comparison table)

Be honest about noise: run each micro-scenario at least 3 times and report
median.

## Deliverable — `docs/STATIC_PUBLICATION_REPORT.md`

The founder-facing report MUST contain, in this order:

1. proposed minimal static publication profile (the SPEC profile, as
   implemented, with the exact JSON shapes);
2. exact directory/object examples (real excerpted files from a run);
3. reference publisher + reader/replicator description (module map, entry
   points, API sketch);
4. clean-room reader proof (what was re-implemented, what was reused, verdict);
5. dumb-server-offline-daemon proof (exact command + observed result);
6. two-node and three-node convergence evidence;
7. index-only vs pack benchmark (table + verdict);
8. comparison with the current dynamic PUSH + Range PULL (table + verdict);
9. failure/hostile results (per case, pass/fail + evidence);
10. what dynamic Mesh mechanisms become unnecessary if this profile is adopted;
11. what the current Mesh still does materially better;
12. recommendation: adopt static-first for 0.6 / keep dynamic Mesh normative /
    hybrid with a sharply defined optional accelerator — with the reasoning
    and the conditions.

Also state the limitations honestly (loopback only, no WAN, no durability
beyond the prototype, no CDN vendor, no production readiness, not frozen).

## Acceptance criteria (all must be true before you stop)

- `python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -v`
  runs from the repository root and ALL tests pass (no skips that hide a
  failure; network/socket restrictions must make tests fail loudly, not skip).
- All 10 required scenarios + the hostile cases are covered by named tests.
- The 5,000-atom and (if practical) 100,000-atom benchmarks actually ran and
  produced the committed evidence files; the numbers in the report come from
  those files.
- Mode A and mode B both pass the same correctness suite.
- The server side of every replication test is a dumb static file server; no
  Punkti daemon is running during replication.
- You did not modify any file outside `experimental/punkti-v0.6-static/`.
  (`git status` must show only that directory.)
- `README.md` states the exact commands to run the suite and the benchmarks.

## Stop condition

When the above hold, commit on the current branch (`experiment/punkti-v0.6-static-publication`)
with a focused commit message, do NOT push, and report: files changed, exact
test counts, benchmark numbers summary, the 12 report verdicts in one line
each, and anything you could not do.
