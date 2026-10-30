> Historical pre-correction draft, superseded by the 2026-10-29 spatial-only correction: every v0.6 record requires canonical XY_Z; empty h and publication key `~` are invalid. Signed historical evidence remains frozen in `legacy-unanchored/`.

# Revision 3 implementation evidence

Implemented on `draft/punkti-0.6-static-first`, starting from
`18fec4fbed16cd7bb623d91929079c1320ae52fe` (revision 3 contract).
This replaces the revision 2 blocker report: the 11-byte magic discrepancy is
resolved. No implementation work was discarded. No push, PR, deployment, tag,
or merge was performed.

Implementation commit: `2ee7bad18bac6e86b850c7d92e3767636b13d86a`.
Vectors/tests commit: `e17ff8e627bce88abd0c0e2d3aa76b44d06e54d5`.
The evidence-only commit follows those commits. The tested code/artifacts match
these committed objects; the only post-test edit was removing a blank EOF line
from a test file for `git diff --check`.

## Commands and actual output

All commands ran from the repository root. Required discovery command, exit 0:

```bash
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests -v
```

Actual captured stdout/stderr (70 tests; zero failures/errors; no skips):

```text
test_static_only_stopped_publishers_separate_readers (test_convergence.Convergence.test_static_only_stopped_publishers_separate_readers) ... STATIC CONVERGENCE packs=False: publishers exited; separate readers; 4 exact records; GETs=104
STATIC CONVERGENCE packs=True: publishers exited; separate readers; 4 exact records; GETs=104
ok
test_determinism_repair_and_no_root_rewrite (test_hostile.Hostile.test_determinism_repair_and_no_root_rewrite) ... ok
test_empty_publication (test_hostile.Hostile.test_empty_publication) ... ok
test_hash_valid_structural_record_is_per_record_rejection (test_hostile.Hostile.test_hash_valid_structural_record_is_per_record_rejection) ... ok
test_independent_import_boundary (test_hostile.Hostile.test_independent_import_boundary) ... ok
test_interrupted_publish_all_phases (test_hostile.Hostile.test_interrupted_publish_all_phases) ... ok
test_json_BOM (test_hostile.Hostile.test_json_BOM) ... ok
test_json_NaN (test_hostile.Hostile.test_json_NaN) ... ok
test_json_boolean (test_hostile.Hostile.test_json_boolean) ... ok
test_json_duplicate (test_hostile.Hostile.test_json_duplicate) ... ok
test_json_exponent (test_hostile.Hostile.test_json_exponent) ... ok
test_json_float (test_hostile.Hostile.test_json_float) ... ok
test_json_negative_zero (test_hostile.Hostile.test_json_negative_zero) ... ok
test_json_newline (test_hostile.Hostile.test_json_newline) ... ok
test_json_surrogate (test_hostile.Hostile.test_json_surrogate) ... ok
test_leaf_duplicate_entry (test_hostile.Hostile.test_leaf_duplicate_entry) ... ok
test_leaf_duplicate_pack (test_hostile.Hostile.test_leaf_duplicate_pack) ... ok
test_leaf_empty (test_hostile.Hostile.test_leaf_empty) ... ok
test_leaf_extra_member (test_hostile.Hostile.test_leaf_extra_member) ... ok
test_leaf_oversized_digest (test_hostile.Hostile.test_leaf_oversized_digest) ... ok
test_leaf_oversized_h (test_hostile.Hostile.test_leaf_oversized_h) ... ok
test_leaf_unanchored_mixed (test_hostile.Hostile.test_leaf_unanchored_mixed) ... ok
test_leaf_unsorted_entries (test_hostile.Hostile.test_leaf_unsorted_entries) ... ok
test_leaf_wrong_h (test_hostile.Hostile.test_leaf_wrong_h) ... ok
test_leaf_wrong_mid (test_hostile.Hostile.test_leaf_wrong_mid) ... ok
test_leaf_wrong_namespace (test_hostile.Hostile.test_leaf_wrong_namespace) ... ok
test_leaf_wrong_prefix (test_hostile.Hostile.test_leaf_wrong_prefix) ... ok
test_manifest_corrupt (test_hostile.Hostile.test_manifest_corrupt) ... ok
test_manifest_missing (test_hostile.Hostile.test_manifest_missing) ... ok
test_manifest_shape_boolean_count (test_hostile.Hostile.test_manifest_shape_boolean_count) ... ok
test_manifest_shape_dangling_shard (test_hostile.Hostile.test_manifest_shape_dangling_shard) ... ok
test_manifest_shape_extra (test_hostile.Hostile.test_manifest_shape_extra) ... ok
test_manifest_shape_negative_count (test_hostile.Hostile.test_manifest_shape_negative_count) ... ok
test_manifest_shape_wrong_count (test_hostile.Hostile.test_manifest_shape_wrong_count) ... ok
test_manifest_shape_wrong_index_depth (test_hostile.Hostile.test_manifest_shape_wrong_index_depth) ... ok
test_manifest_shape_wrong_prev (test_hostile.Hostile.test_manifest_shape_wrong_prev) ... ok
test_manifest_truncated (test_hostile.Hostile.test_manifest_truncated) ... ok
test_multiple_packs_257_and_independent_publication (test_hostile.Hostile.test_multiple_packs_257_and_independent_publication) ... ok
test_nonconsecutive_pack_partition (test_hostile.Hostile.test_nonconsecutive_pack_partition) ... ok
test_oversized_carrier_is_resource_failure (test_hostile.Hostile.test_oversized_carrier_is_resource_failure) ... ok
test_pack_corrupt (test_hostile.Hostile.test_pack_corrupt) ... ok
test_pack_missing (test_hostile.Hostile.test_pack_missing) ... ok
test_pack_truncated (test_hostile.Hostile.test_pack_truncated) ... ok
test_publisher_order_and_atomic_root (test_hostile.Hostile.test_publisher_order_and_atomic_root) ... ok
test_race_bounded_and_restarts (test_hostile.Hostile.test_race_bounded_and_restarts) ... ok
test_record_corrupt (test_hostile.Hostile.test_record_corrupt) ... ok
test_record_missing (test_hostile.Hostile.test_record_missing) ... ok
test_record_truncated (test_hostile.Hostile.test_record_truncated) ... ok
test_root_advanced_before_objects_and_retry (test_hostile.Hostile.test_root_advanced_before_objects_and_retry) ... ok
test_root_corrupt (test_hostile.Hostile.test_root_corrupt) ... ok
test_root_missing (test_hostile.Hostile.test_root_missing) ... ok
test_root_truncated (test_hostile.Hostile.test_root_truncated) ... ok
test_shard_corrupt (test_hostile.Hostile.test_shard_corrupt) ... ok
test_shard_missing (test_hostile.Hostile.test_shard_missing) ... ok
test_shard_truncated (test_hostile.Hostile.test_shard_truncated) ... ok
test_stale_equivocal_offline_rejoin (test_hostile.Hostile.test_stale_equivocal_offline_rejoin) ... ok
test_coarse_and_12_character_bounds (test_hostile.StagingAndGeometry.test_coarse_and_12_character_bounds) ... ok
test_late_missing_record_preserves_both_stores_and_checkpoint (test_hostile.StagingAndGeometry.test_late_missing_record_preserves_both_stores_and_checkpoint) ... ok
test_prefix_chain_and_empty_interior (test_hostile.StagingAndGeometry.test_prefix_chain_and_empty_interior) ... ok
test_root_change_during_read_keeps_immutable_snapshot_readable (test_hostile.StagingAndGeometry.test_root_change_during_read_keeps_immutable_snapshot_readable) ... ok
test_scope_can_skip_withheld_unselected_subtree (test_hostile.StagingAndGeometry.test_scope_can_skip_withheld_unselected_subtree) ... ok
test_V1 (test_vectors.Vectors.test_V1) ... ok
test_V2 (test_vectors.Vectors.test_V2) ... ok
test_V3 (test_vectors.Vectors.test_V3) ... ok
test_V4 (test_vectors.Vectors.test_V4) ... ok
test_V5 (test_vectors.Vectors.test_V5) ... ok
test_V6 (test_vectors.Vectors.test_V6) ... ok
test_V7 (test_vectors.Vectors.test_V7) ... ok
test_V8 (test_vectors.Vectors.test_V8) ... ok
test_V9 (test_vectors.Vectors.test_V9) ... ok

----------------------------------------------------------------------
Ran 70 tests in 24.119s

OK
```

The 70 top-level tests comprise 60 hostile/failure/geometry/publication tests,
nine V1–V9 tests, and one process-separated convergence test. V1–V9 contain 25
machine-checkable cases, each exercised through both implementations (50 case /
implementation combinations). Further mode, mutation, and implementation subtests
are not inflated into the top-level pass count.

Generator, exit 0:

```bash
python3 experimental/punkti-v0.6-publication/scripts/generate_vectors.py
```

```text
Generated vectors.json and docs/NORMATIVE_VECTORS.md (V1-V9)
```

Determinism check, exit 0:

```bash
python3 experimental/punkti-v0.6-publication/scripts/check_vectors.py
```

```text
vectors.json: byte-identical on two regenerations; SHA256=473a314f6a59627f429165aaf12184a40e4c19268a2abbd27085b1e0a5921c84
docs/NORMATIVE_VECTORS.md: byte-identical on two regenerations; SHA256=815aa4c72695bb9d4714303fec49666afde6f953349336ac4857416e136fb5e4
```

This check independently regenerates both artifacts twice into separate temporary
directories and compares every byte with the committed artifacts. It does not
merely hash an unchanged file twice. Artifacts contain no runtime ports, timestamps,
wall-clock measurements, or environment-dependent paths.

Whitespace checks, exit 0 with no output:

```bash
git diff --check
git diff --cached --check
```

## Static-only result

The convergence test creates disjoint two-record publications in separate
reference and independent publisher subprocesses. `subprocess.run` waits for each
publisher to exit before readers start. Two stdlib static file servers serve the
published directories. Separate reader subprocesses exchange and validate the
records; both implementations then republish the union and exit again. Final
separate readers recover exactly the same four MIDs and exact R bytes.

Both index-only and pack profiles pass. Each profile used 104 static GET requests
across the two origins and four replication sweeps. Request-path assertions allow
only root, manifest, shard, record, and pack retrieval. No handshake, session,
notification, callback, query service, or dynamic endpoint exists in the experiment.
The count is a measured test result, not a performance claim.

## Contract coverage and independence

- Canonical JSON checks reject duplicate members, floats/exponents/NaN, BOM,
  noncanonical spelling, booleans in integer fields, trailing whitespace, and
  invalid Unicode. Root/manifest/shard shapes and profile markers are exact.
- Depth-2 → depth-10 chains, nonempty interiors/leaves, padded coarse and
  12-character XY keys, the reserved unanchored leaf, inclusive/exclusive prefix
  bounds, exact negative/fractional Z, and post-fetch Z filtering are exercised.
- Exact R digests and recomputed MIDs are checked; valid, forged, and unsupported
  signature variants cannot poison each other's MID/candidate stores. Two
  unsupported signature variants sharing a MID remain separate candidates.
- Pack framing, count mismatch, truncation, trailing bytes, foreign/duplicate
  entries, reversed order, and nonconsecutive group partitioning are rejected.
  A 257-record XY leaf plus an unanchored leaf exercises multi-pack publication;
  independently produced files agree byte-for-byte in both profiles.
- Missing, truncated, and corrupt root/manifest/shard/record/pack objects fail
  without admission/checkpoint advancement. Hash-valid metadata and tree-shape
  attacks, oversized fields/carriers, root-before-objects visibility, late
  failures after valid/candidate staging, retry/idempotence, stale/equivocal roots,
  and long offline/rejoin are tested over real HTTP.
- Interrupted publication after objects, shards, and manifest preserves the old
  root and readable old state. Retry publishes the desired state. Repair/no-op
  publication leaves root bytes and modification time unchanged. Write-order
  instrumentation checks records → packs → shards → manifest → root.
- Root/manifest sequence mismatch retries from root, succeeds after repair, and
  fails after the bounded retry budget when unrepaired. A root legitimately
  advancing during a read leaves its previous immutable snapshot readable.
- Scope-limited reads can skip withheld out-of-scope content; unrestricted reads
  fail on missing referenced content. Neither outcome asserts global completeness
  or freshness.

The reference adapts accepted staticpub mechanisms, including its durable-write
and anti-poisoning store code. The independent module is separately written, has
its own recursive JSON encoder, queue traversal, pack handling, publisher, durable
writer, and stores; an AST test checks its import boundary. Both implementations
share only the approved carrier/spatial protocol codecs and standard libraries.
The independent publisher also matches the reference's generated bytes. This is
publication-layer independence, not independent cryptography.

## Findings and limits

No blocking contradiction remains and no normative contract deviation is known.
The literal `PUNKTIPACK1` and its 11-byte length agree in revision 3; entry counts
start at offset 11. The constants table and operative prose agree on the index
geometry and pack grouping implemented here.

One nonblocking editorial finding: the illustrative manifest JSON in section 3
has a stray quote after `<int>` in `record_count`. The section 0.1 member table,
section 3 prose, and integer-only canonical encoding unambiguously require an
integer. The implementation follows those rules. The contract was not modified.

Optional packs are absent in index-only publication; pack-enabled readers can also
read index-only publications through their canonical record objects. Invalid
carrier framing cannot provide a recomputed MID/h, so it receives the specified
per-record rejection; decoded records (including provenance-invalid ones) must
match index metadata before admission decisions. Local resource refusals abort the
attempt without labeling oversized carriers structurally invalid.

This is a single-writer experiment with in-memory read staging/head observations,
not a concurrent operational database. Readers impose an explicit 64 MiB HTTP
object budget and ten-second request timeout; carrier resource limits remain
unchanged. No scale, power-loss simulation, cryptographic independence, or global
completeness/freshness result is claimed.

Manual verification: reviewed generated logical-object/vector output, exact
changed-file scope, independent import boundary, captured HTTP convergence results,
and artifact equality. Browser/manual UX verification is not applicable: no PWA,
relay, core, deployment, accepted codec, earlier experiment, or proposal file was
changed. Those unrelated suites were not run. All changed files are confined to
`experimental/punkti-v0.6-publication/`.
