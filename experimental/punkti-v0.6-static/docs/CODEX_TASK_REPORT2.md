# Codex follow-up #6 — final polish of the founder report (two gaps)

## Context

The report rewrite (follow-up #5) succeeded — sections 7, 8, 10, 11 and 12
are now evidence-derived and accurate. The 100k scale step completed
(`scale_100k.completed == true`, both modes) after the scale-only re-run.

Two gaps remain in the Founder-facing report. Fix only these; keep everything
else that now reads correctly.

Files you own:

- `experimental/punkti-v0.6-static/src/staticpub/bench.py` (the markdown
  generators only)
- `experimental/punkti-v0.6-static/tests/test_static_publication.py`
  (only ADD tests; never weaken or delete existing ones)

Do NOT change the publisher, reader, store, carrier, `run_scale_100k`,
`run_all`, `run_scale_only`, or any protocol/semantic behaviour.
Do not commit. Do not push.

## Gap 1 — Section 9 (failure/hostile results) names no tests

Section 9 currently reads only:

> Hostile/failure-path tests remain in place and green in the latest suite run.

Issue #20 explicitly requires the failure/hostile results as a deliverable,
and the issue enumerates the required hostile cases: truncation; stale head;
missing segment/object; corrupt static object; mismatched digest;
replay/duplicate; reordered publication visibility; selective withholding;
long offline/rejoin.

Rewrite section 9 so it lists, per hostile case, the exact test that proves
it and its current PASS/FAIL state, derived from the evidence
(`evidence/test_results.json`) and the actual test names in
`tests/test_static_publication.py`.

Map the issue's cases to the real test names. The real test names are:

- `test_02_same_mid_invalid_variant_cannot_poison_valid` (invalid variant
  must not poison a valid MID)
- `test_03_same_xy_different_z_filter`
- `test_05_negative_and_large_z_values_preserved`
- `test_06_dumb_static_server_replication_works_after_node_stop`
- `test_07_stale_root_then_refresh_detected` (stale head / stale root)
- `test_08_missing_referenced_object_no_false_checkpoint` (missing object →
  no false checkpoint/admission)
- `test_09_source_disappearance_and_reappearance_is_idempotent` (long
  offline/rejoin, source disappearance and reappearance)
- `test_11_hostile_truncated_record_rejected` (truncation)
- `test_12_hostile_missing_segment_in_mode_b_fails` (missing segment)
- `test_13_hostile_corrupt_root_object_rejected` (corrupt static object)
- `test_14_hostile_mismatched_digest_rejected` (mismatched digest)
- `test_15_hostile_replay_duplicate_is_noop` (replay/duplicate)
- `test_16_hostile_reordered_publication_visibility` (reordered publication
  visibility)
- `test_17_hostile_selective_withholding_detectable_by_comparison` (selective
  withholding)

Also keep the convergence and clean-room proofs visible in the report:
`test_01_two_node_union_convergence`, `test_10_three_node_partial_overlap_converges_to_union`,
`test_20_cleanroom_reader_matches_reference_reader`,
`test_04_xy_prefix_limited_replication_only_fetches_matching_region`.

Render the PASS/FAIL state from `evidence/test_results.json` (`status`,
`returncode`, `ran`, `seconds`). If the evidence shows the suite did not pass,
say so — do not claim PASS unconditionally. If the evidence file is missing,
say "suite result not recorded in evidence" rather than inventing a state.

## Gap 2 — the 100k result is not in section 7

The 100k scale run is the strongest single result in the experiment, and it
is currently only mentioned in section 12's status line and the limitations
list. Add it to section 7 (the index-only vs pack verdict), derived from
`evidence/bench_static.json` → `scale_100k`:

- mode A: `100,005` replication requests, `681.524s` wall, publish
  `402.939s` wall / `129.992s` CPU
- mode B: `398` replication requests, `454.033s` wall, publish `425.057s`
  wall / `138.665s` CPU
- i.e. ~`251x` fewer requests for ~`1.2%` more bytes at 100,000 atoms

Derive all of these from the evidence at render time (no hardcoded figures),
and derive the ratio/percentage the same way the other ratios are derived.

If the scale step is missing or truncated, render "not completed" plus the
reason instead of these numbers.

## Rendering rules (unchanged)

- Every number comes from the evidence JSON at render time.
- Never render a truncated/missing phase as 0 or as a blank that reads like a
  real measurement.
- Keep the 12-section structure and its headings.
- The report must remain readable standalone for the Founder.

## Tests

Add fast tests proving:
- the rendered report names each of the issue's required hostile cases with
  its real test name (e.g. `test_11_hostile_truncated_record_rejected` for
  truncation, `test_14_hostile_mismatched_digest_rejected` for mismatched
  digest);
- the rendered report states the suite status from `evidence/test_results.json`
  and, when that evidence says the suite failed, does NOT claim PASS;
- the rendered report contains the 100k mode-A vs mode-B request counts and
  the derived ratio;
- the rendered report degrades to "not completed" for a truncated/missing
  scale step (it must already do this — verify, and keep it working).

Keep all 34 existing tests untouched and green.

## Stop condition

Report: files changed, test counts before/after, and paste the rendered text
of section 9 and the new 100k lines in section 7 from a real
`regenerate_docs_from_evidence()` call against the CURRENT evidence files.
Do not commit. Do not push.
