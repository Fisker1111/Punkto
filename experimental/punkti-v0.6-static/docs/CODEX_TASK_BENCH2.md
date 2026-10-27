# Codex follow-up #2 — bounded benchmark run (the previous sweep was killed)

The previous full sweep (`LEAF_DEPTH_SWEEP` × 2 modes × 2 dataset sizes × all
scenarios × repeats=3) exceeded the time budget and was killed mid-run.
Nothing was lost in the code; only the measurement window was too large.

Keep everything already implemented (configurable leaf depth, matched-size
support, scale runner, storage-amplification/rebuild/concurrency helpers).
Change only the MEASUREMENT PLAN below, then regenerate evidence and docs.

## Bounded measurement plan (mandatory, in this order)

Budget: the whole run must finish within ~35 minutes of wall time.

1. **Leaf-depth sweep on the 1 000-atom dataset only.**
   `LEAF_DEPTH_SWEEP = (2, 4, 6, 8, 10)`, modes A and B, scenario
   `fresh_subscriber_allspace` + `xy_prefix_subscription`, `repeats = 3`,
   median reported.
   Purpose: pick the leaf depth. This is the key new finding.

2. **Matched static vs Mesh at 1 000 atoms**, all six scenarios, both modes,
   `repeats = 3`, medians, identical records and subscriptions on both sides.

3. **Matched static vs Mesh at 5 000 atoms**, all six scenarios, both modes,
   `repeats = 3`, medians. This is the expensive part: to keep it within
   budget, run it with **one** publication build per mode reused across
   scenarios (publish once, then only replicate), and reuse the generated
   records across both systems.

4. **100 000-atom scenario, hard budget 12 minutes**: publish and run ONE
   fresh-subscriber replication for mode A and mode B at the recommended leaf
   depth. Record requests/bytes/wall for the replication and wall/CPU for the
   publication. If a sub-phase exceeds the budget, stop it, keep the partial
   numbers and set an explicit `completed: false` + `reason` in the evidence.
   Never fabricate a number.

5. **Storage amplification + rebuild cost** for mode A and mode B at 1 000
   atoms: bytes on disk of the published tree vs sum of raw record bytes; and
   the wall time to republish the same store.

6. **Concurrency**: N = 1 and N = 8 concurrent readers against the SAME
   published tree, at 1 000 atoms, mode A and mode B, `repeats = 3`, medians.
   Record aggregate requests/bytes/wall and the per-request origin work done
   by the static server.

Rules:
- `repeats` stays ≥ 3 everywhere; report median + min + max.
- Every figure in the docs comes from the committed evidence JSON.
- If a step's budget is exceeded, degrade that step only and SAY SO in the
  evidence (`completed: false`, `reason: ...`) and in the report.
- Do not weaken or delete tests; keep the current suite green and add any
  test needed for the leaf-depth changes (it must already exist — verify).

## Docs

- `evidence/bench_static.json`: leaf-depth sweep, per-size scenario results
  with repeats/medians, scale-100k honesty flag, storage amplification,
  rebuild cost, concurrency results.
- `evidence/bench_mesh.json`: mesh baseline at 1 000 and 5 000 atoms with the
  same scenario names, repeats ≥ 3, medians.
- `docs/BENCHMARK.md`: the tables (leaf-depth sweep, matched static/mesh at
  both sizes, scale, concurrency) plus an explicit method note (loopback,
  stdlib static server, warm page cache → comparative, not absolute latency)
  and an explicit note about which steps completed and which were truncated.
- `docs/STATIC_PUBLICATION_REPORT.md`: update sections 1, 7, 8, 12 with the
  new numbers, the recommended leaf depth and its rationale, and state whether
  the recommendation changed. Keep the 12-section structure and the honest
  limitations list.
- `evidence/test_results.json`: re-run the suite and store the result.
- `README.md`: update benchmark command and expected runtime.

## Stop condition

Report: files changed, test counts, the leaf-depth sweep table, matched
static-vs-mesh tables at 1 000 and 5 000, the 100 000-atom outcome, the
recommended leaf depth, whether the report recommendation changed, and the
exact wall time of the benchmark run. Do not push.
