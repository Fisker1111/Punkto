# Codex follow-up #4 — scale-only benchmark path for the 100k atom measurement

## Context

The bounded benchmark run completed and produced good evidence for every
phase EXCEPT the 100k scale step. The scale step is budget-limited by design
(`--scale-budget-seconds`), and on this host (1 vCPU, 2 GB RAM) the 600s
budget was fully consumed by publishing 100,000 records (mode A publish alone
took ~386s wall / ~127s CPU). The result was:

- mode A: `completed: false`, `reason: budget_exhausted_after_publish`,
  `admitted_count: 100000`, publish wall `385.87s` — **no replication numbers**.
- mode B: `completed: false`, `reason: budget_exhausted_before_mode_start`,
  `admitted_count: 0` — never started.

The Founder's Issue #20 explicitly asks to measure "100,000 atoms if practical
within resource limits" and to report honestly what did and did not complete.
So we need a way to run JUST the scale step, with a larger budget, without
re-running the 51-minute bounded benchmark.

## Required change — a `--scale-only` CLI mode

Add a `--scale-only` flag to `staticpub.bench` that:

1. Loads the EXISTING `evidence/bench_static.json` and `evidence/bench_mesh.json`
   (do not start from scratch, do not re-run the leaf sweep, matched, storage
   or concurrency phases).
2. Reads the already-recorded `recommended_leaf_depth` from
   `evidence/bench_static.json` (fall back to the sweep-derived value via
   `choose_recommended_leaf_depth` if it is absent).
3. Runs ONLY `run_scale_100k(...)` with the operator-supplied
   `--scale-budget-seconds` and `--scale-count`, writing the result into
   `static_data['scale_100k']` and preserving every other key in the file.
4. Writes `evidence/bench_static.json` back atomically (the existing
   `write_json_atomic` helper) and then calls `regenerate_docs_from_evidence()`
   so `docs/BENCHMARK.md` and `docs/STATIC_PUBLICATION_REPORT.md` reflect the
   new scale numbers.

Hard requirements:

- The `--scale-only` path MUST NOT modify or invalidate any other phase's
  evidence. If `evidence/bench_static.json` cannot be loaded, exit non-zero
  with a clear error instead of writing a fresh/empty file.
- Never fabricate a number. A truncated scale step keeps `completed: false` and
  its `reason`, and the generated markdown must keep saying "not completed".
- Do not change `run_scale_100k` semantics, the publisher, reader, store,
  carrier, or any protocol behaviour. Only the CLI/plumbing.

## Additional measurement the Founder asked for

Issue #20 asks for the 100k scale measurement to record "requests; transferred
bytes; useful bytes; wall time locally; CPU/memory if practical".

`run_scale_100k` currently records `requests`, `transferred_bytes`, `wall_sec`,
`cpu_sec`, `origin_requests` and `origin_bytes` for the replication, but it does
NOT record `useful_bytes` or the peak memory (`maxrss_kib`) for the scale
replication. Add those two fields to the scale replication record so the scale
row carries the same useful-bytes signal the other scenarios carry, plus the
peak RSS. Use the same field names the other scenarios already use
(`useful_bytes`, `maxrss_kib`) so the doc generator can render them uniformly.

## Tests

Add fast tests (no long benchmark runs) proving:

- `--scale-only` against a missing/empty `evidence/bench_static.json` exits
  non-zero and does NOT overwrite the evidence file;
- `--scale-only` against a real evidence file preserves every non-scale key
  byte-for-byte (compare the loaded JSON before/after, ignoring the
  `scale_100k` key);
- the scale replication record now contains `useful_bytes` and `maxrss_kib`.

Keep all 26 existing tests untouched and green.

## Acceptance criteria

- `python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -v`
  exits 0 with 26 existing + your new tests.
- `PYTHONPATH=src python3 -m staticpub.bench --help` shows `--scale-only`.
- `--scale-only` with a tiny `--scale-count`/`--scale-budget-seconds` against
  the REAL current `evidence/bench_static.json` does not corrupt it and
  regenerates the docs. If it runs the scale step for real, that is fine, but
  the operator will re-run the real 100k measurement afterwards — so make sure
  a tiny run does not leave the evidence in a broken state.

## Stop condition

Report: files changed, test counts before/after, the `--scale-only` usage
lines, and confirmation that the real `evidence/bench_static.json` was not
corrupted by your test run. Do not commit. Do not push. Do NOT run the real
100k scale measurement (the operator does that).
