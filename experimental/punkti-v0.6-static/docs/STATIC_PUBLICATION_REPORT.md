# STATIC PUBLICATION REPORT — Punkti v0.6 prototype

Status: experimental, loopback-only, not frozen, not production-ready.

Evidence files:

- `evidence/test_results.json`
- `evidence/bench_static.json`
- `evidence/bench_mesh.json`
- `evidence/publication_example.json`

## 1) Minimal static publication profile (implemented)

Implemented profile matches `docs/SPEC.md` and keeps mutable root + immutable content-addressed objects.

Mutable-file accounting from benchmark evidence: `root.json` is the only mutable artifact (`1` file, `150` bytes in measured runs).

Test status from `evidence/test_results.json`:

- status: `OK`
- return code: `0`
- ran: `34`
- seconds: `16.56`

## 2) Exact directory/object examples (real run excerpts)

From `evidence/publication_example.json` (a real publication run):

- root pointer `root.json`: `{"v": "punkti/pub/0.6-draft", "seq": 1, "head": "a2dfa8560eed4a63b3ae0172bd9df41576aaa194150b756f774b1a859c72b2c9", "updated_at": "1970-01-01T00:00:00.003Z"}`
- immutable manifest `manifests/<sha256>.json`: `seq=1`, `prev=null`, `record_count=3`, `pack_count=3`, `depth=2`, `index={"u4": "6f6f854e6e1df0d2aa9765c13655fe9404857ee6bb9672c8e89f88c53847a9a3"}`
- immutable leaf shard `h/<xy chars>/<sha256>.json`: prefix `u4pruydqqv`, 1 record entr(y/ies) keyed by MID, 1 pack(s)
- exact immutable record bytes: `records/77/7787b43cfef3b0b58abb98cba1352d8b60a99a27b45991a1aae8635564d48a99`
- immutable replication pack: `segments/5f/5f81ec921ae501d3163587ccfa95c89ef2c51061f3976723927c6a41b8ed52cf`

Reading rules this layout encodes:

- the file name of every object under `manifests/`, `h/`, `records/` and
  `segments/` is the lowercase hex SHA256 of that object's exact bytes, so a
  reader rejects any object whose bytes do not hash to its name;
- `root.json` is the only mutable file (1 file,
  150 bytes) and it only points at the current manifest;
- records remain canonical raw carrier bytes under digest paths, and mode B
  adds immutable pack segments only as an acceleration artifact while the
  canonical per-record objects stay published.

## 3) Reference publisher + reader/replicator

Module map:

- `src/staticpub/publisher.py` — deterministic immutable object build + atomic root swap
- `src/staticpub/reader.py` — GET-only replication with digest and carrier validation
- `src/staticpub/store.py` — valid MID-keyed store + candidate digest-keyed store
- `src/staticpub/httpsource.py` — dumb stdlib static file source
- `src/staticpub/harness.py` — node lifecycle wrapper
- `src/staticpub/carrier_io.py` — approved carrier/spatial import + framing helpers

## 4) Clean-room reader proof

- Implemented in `src/staticpub/cleanroom.py`.
- Equivalence test remains `test_20_cleanroom_reader_matches_reference_reader`.

## 5) Dumb-server / offline-daemon proof

- Static serving remains stdlib HTTP only.
- Replication does not require a running Punkti daemon.

## 6) Two-node and three-node convergence evidence

- `test_01_two_node_union_convergence`
- `test_10_three_node_partial_overlap_converges_to_union`

## 7) Index-only vs pack benchmark verdict

Bounded run profile: `bounded`, repeats=3.

- Recommended leaf depth: `2`
- Recommendation rationale: lowest combined median requests for dataset=1000 over scenarios=fresh_subscriber_allspace, xy_prefix_subscription; wall time tie-break
- 5k fresh wall median: A `24.785s`, B `21.255s`
- 5k XY-prefix wall median: A `7.494s`, B `5.966s`
- 5k incremental wall median: A `3.212s`, B `2.700s`
- Fresh subscriber request collapse at 5k atoms: A `5,005` vs B `26` (`192.5x` fewer requests in mode B).
- Fresh subscriber request collapse at 1k atoms: A `1,005` vs B `11` (`91.4x` fewer requests in mode B).
- Byte overhead for that collapse: 5k A `1,825,045` bytes vs B `1,846,765` bytes (`1.190%`), 1k A `365,619` vs B `370,108` (`1.228%`).
- 100k scale (from `scale_100k`): mode A replication `100,005` requests, `681.524s` wall, publish `402.939s` wall / `129.992s` CPU.
- 100k scale (from `scale_100k`): mode B replication `398` requests, `454.033s` wall, publish `425.057s` wall / `138.665s` CPU.
- 100k scale request/byte tradeoff: mode A `100,005` vs mode B `398` requests (`251.3x` fewer in mode B) with bytes `36,886,475`→`37,318,700` (`1.172%` mode-B overhead).
- 100k scale completion state: completed (budget `3300`s, elapsed `2837.912`s).
- Storage/rebuild at 1k atoms: mode A `365,619` bytes over `1,005` files (amplification `1.993x`, rebuild `0.864s`); mode B `553,537` bytes over `1,011` files (amplification `3.018x`, rebuild `0.390s`).
- Concurrency on one shared publication (1k atoms): A/1 reader `1,005` req in `5.997s`, A/8 readers `8,040` req in `31.271s`; B/1 reader `11` req in `4.151s`, B/8 readers `88` req in `19.600s`.
- Leaf-depth sweep shape: depth `2` has the lowest request score (`1,358`) while depth 10 is much worse (`5,664`), confirming that shallower leaves reduce index-object fanout and request count.

Verdict: mode B is the practical bootstrap profile for static origins because it collapses request count by ~two orders of magnitude with only low single-digit byte overhead.

## 8) Static profile vs dynamic Mesh baseline verdict

Matched-size comparison now includes 1k and 5k datasets with identical scenario names.

- Mesh 5k fresh wall median: `4.935s`
- Static A 5k fresh wall median: `24.785s`
- Static B 5k fresh wall median: `21.255s`
- Mesh 5k fresh pull requests: `157`
- Static B 5k fresh requests: `26` (`6.0x` fewer requests than Mesh in this scenario)

Verdict: this loopback pass shows Mesh wall-time advantage, but the dimensions diverge: Mesh minimizes elapsed time in this setup while static mode B minimizes origin request count. The wall gap is measured against a stdlib single-threaded static server on a one-vCPU/two-GB host and is not equivalent to a CDN-cached static origin result.

## 9) Failure/hostile results

Suite evidence from `evidence/test_results.json`: PASS (`status=OK`, `returncode=0`, `ran=34`, `seconds=16.56`).

- Truncation: `test_11_hostile_truncated_record_rejected` — PASS.
- Stale head/root detection: `test_07_stale_root_then_refresh_detected` — PASS.
- Missing referenced object/no false checkpoint admission: `test_08_missing_referenced_object_no_false_checkpoint` — PASS.
- Missing segment (mode B): `test_12_hostile_missing_segment_in_mode_b_fails` — PASS.
- Corrupt static object: `test_13_hostile_corrupt_root_object_rejected` — PASS.
- Mismatched digest: `test_14_hostile_mismatched_digest_rejected` — PASS.
- Replay/duplicate: `test_15_hostile_replay_duplicate_is_noop` — PASS.
- Reordered publication visibility: `test_16_hostile_reordered_publication_visibility` — PASS.
- Selective withholding: `test_17_hostile_selective_withholding_detectable_by_comparison` — PASS.
- Long offline/rejoin (source disappearance/reappearance): `test_09_source_disappearance_and_reappearance_is_idempotent` — PASS.
- Invalid variant cannot poison valid MID: `test_02_same_mid_invalid_variant_cannot_poison_valid` — PASS.
- Same XY with different Z filtering correctness: `test_03_same_xy_different_z_filter` — PASS.
- Negative and large Z preservation: `test_05_negative_and_large_z_values_preserved` — PASS.
- Dumb static server replication after source stop: `test_06_dumb_static_server_replication_works_after_node_stop` — PASS.
- Required convergence proof (two-node union): `test_01_two_node_union_convergence` — PASS.
- Required convergence proof (three-node partial overlap to union): `test_10_three_node_partial_overlap_converges_to_union` — PASS.
- Required clean-room equivalence proof: `test_20_cleanroom_reader_matches_reference_reader` — PASS.
- Required bounded-fetch proof: `test_04_xy_prefix_limited_replication_only_fetches_matching_region` — PASS.

## 10) What dynamic Mesh mechanisms become unnecessary (if static-first adopted)

- No required PUSH endpoint for correctness: a fresh subscriber converges from immutable static objects plus `root.json` discovery pointer.
- No required dynamic range-query API for correctness: static shard traversal + optional pack segments already complete state transfer.
- No required reciprocal callback/session state for correctness: no session coupling is needed between publisher and subscriber.
- No required live daemon at the serving side for correctness: publication can be served by dumb static hosting.
- These mechanisms remain useful as optional accelerators for wall-time-sensitive paths, but correctness does not depend on them.

## 11) What current Mesh still does materially better

- Lower measured loopback wall-time in this pass (5k fresh median `4.935s` vs static B `21.255s`).
- One-shot dynamic range pull path avoids object-by-object traversal in the current implementation.
- No publication rebuild step before serving updates.
- Simpler incremental catch-up path in the current Mesh prototype.
- Pull requests are dynamic-range API calls rather than per-object static GETs.

## 12) Recommendation

Evidence-derived recommendation: **hybrid with optional dynamic accelerator**.

- Three-way decision frame:
  - **Adopt static-first** when minimizing origin requests and static-host correctness is the primary goal.
  - **Keep dynamic Mesh normative** when wall-time-sensitive live synchronization is the dominant requirement.
  - **Hybrid (recommended for current evidence)**: static publication is the normative correctness path; dynamic Mesh range-pull/PUSH remains an optional accelerator for latency-sensitive environments.
- Use leaf depth `2` for the current static publication profile.
- Recommendation justification from measured evidence: request collapse (`5,005`→`26` at 5k) with small byte overhead (`1.190%`) supports static correctness; Mesh wall median (`4.935s`) supports optional acceleration.

100k bounded-step completion: completed (budget `3300`s, elapsed `2837.912`s).

## Limitations (explicit)

- Loopback-only measurements.
- Not production durability.
- No CDN vendor integration benchmark.
- Not protocol-frozen.
- Warm cache and stdlib server conditions mean comparative, not absolute-latency, claims.
- Host constraint for this run: one vCPU and ~2 GB RAM.
- 100k scale evidence status: completed (budget `3300`s, elapsed `2837.912`s). Interpret 100k conclusions from `scale_100k.completed` and `reason`, not assumptions.
