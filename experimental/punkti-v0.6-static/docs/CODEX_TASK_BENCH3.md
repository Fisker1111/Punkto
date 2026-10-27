# Codex follow-up #3 — make the benchmark safely bounded on a 1 vCPU / 1 GB host

## Context

The static publication prototype is implemented and green (22 tests). The
previous benchmark run was killed mid-sweep because the host has **1 vCPU and
~1 GB RAM**, so the 100,000-atom scale step alone cannot be executed to
completion inside any sane wall-clock budget.

Your job is **only** to make the measurement harness honest and bounded on
this host, and to capture the host environment in the evidence. Do NOT change
the publisher, reader, store, carrier or any protocol/semantic behaviour.

Files you own for this task:

- `experimental/punkti-v0.6-static/src/staticpub/bench.py`
- `experimental/punkti-v0.6-static/tests/test_static_publication.py`
  (only ADD tests; never weaken or delete existing ones)

Do not touch any other module. Do not commit. Do not push.

## Required changes

### 1. `--scale-count` CLI override

`staticpub.bench` currently hardcodes the scale attempt at 100000 records via
`BENCH_PLANS[plan]['scale_count']`. Add a `--scale-count` CLI argument
(default: the plan value) and a `scale_count` parameter on `run_all(...)`, so
the operator can size the scale attempt explicitly. The value must be
recorded in `evidence/bench_static.json` as `scale_100k.attempted_count`.

### 2. Deadline-aware scale step

`run_scale_100k` currently spends the whole budget admitting 100k records
before it can check the deadline. Change the admit loop so it checks the
deadline periodically (every 1000 records) and stops admitting when the
budget is exhausted.

When the admit loop stops early, the step MUST:
- still publish the records it did admit, and record that publish wall/CPU
  (this gives a real publish-scaling data point at a partial record count);
- set `mode_result['completed'] = False`;
- set `mode_result['reason']` to a string that names the budget exhaustion
  explicitly, e.g. `'budget_exhausted_during_admit'`;
- record `admitted_count` and `attempted_count` on the mode result so a
  reader can see the partial coverage.

Never fabricate a number: if a phase did not run, its value stays `None`.

### 3. Doc generators must survive a truncated scale step

`generate_benchmark_markdown` and `generate_static_report_markdown` read
`scale_100k` and the matched/concurrency blocks. Make both robust when:
- `scale_100k` is `None` or a mode is missing its `publish`/`replication`;
- a mode was truncated (`completed: false` with a `reason`);
- `concurrency.mode_results` lacks a mode or a reader count;
- a matched dataset size is missing.

When a step was truncated, the generated markdown MUST say so explicitly
("not completed", plus the reason string). Never render a truncated step as if
it had completed, and never render `None` as `0`.

### 4. Host environment in the evidence

Capture the measurement host into the evidence JSON (add a `host` block at the
top level of `evidence/bench_static.json` and `evidence/bench_mesh.json`):

```json
"host": {"cpu_count": <int>, "memory_total_kib": <int>,
         "platform": "<str>", "python_version": "<str>"}
```

Read these from the live machine (`os.cpu_count()`, `/proc/meminfo` MemTotal,
`platform.platform()`, `platform.python_version()`). Fall back to `None`
rather than guessing if a value is unavailable.

Print the same host block in the "Scope and method" section of the generated
`docs/BENCHMARK.md`, and add an explicit note that the host has a single vCPU
and limited RAM, so the absolute wall-time numbers are NOT comparable to a
normal multi-core developer machine and are comparative only.

### 5. Tests

Add fast unit tests (no long benchmark runs) proving:
- `run_scale_100k` with a tiny budget returns `completed == False`, a
  non-empty `reason`, and never raises;
- `run_scale_100k` with a small `count` and a generous budget completes and
  reports `completed == True`;
- the markdown generators do not raise when the scale step is `None`,
  truncated, or missing modes/readers, and the rendered text contains an
  explicit "not completed" marker for a truncated step;
- the `host` block is present in the generated evidence structure.

Keep the existing 22 tests untouched and green.

## Acceptance criteria

- `python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -v`
  exits 0 with the existing 22 tests plus your new ones.
- `PYTHONPATH=src python3 -m staticpub.bench --help` shows `--scale-count`.
- `PYTHONPATH=src python3 -m staticpub.bench --docs-only` runs without raising
  against the CURRENT (partial) evidence files in `evidence/` — i.e. it must
  handle the existing truncated sweep data without crashing. Do NOT overwrite
  `evidence/bench_static.json` or `evidence/bench_mesh.json` with fake data;
  if `--docs-only` needs a host block that the current evidence lacks, make it
  tolerant (missing host => omit or print `unknown`), and do not fabricate.

## Stop condition

Report: files changed, exact test counts (before/after), the new `--scale-count`
usage line, and confirmation that `--docs-only` did not crash. Do not commit.
Do not push. Do not run the full benchmark (the operator runs it).
