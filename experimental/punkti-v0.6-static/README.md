# Punkti v0.6 static publication prototype

This experiment implements a static-first publisher/reader profile from `docs/SPEC.md`.

## Layout

- `src/staticpub/` — reference implementation (`publisher`, `reader`, `store`, `httpsource`, `harness`, `cleanroom`, `bench`)
- `tests/` — real-HTTP `unittest` scenarios
- `evidence/` — machine-readable outputs
- `docs/BENCHMARK.md` — benchmark summary
- `docs/STATIC_PUBLICATION_REPORT.md` — founder-facing report

## Run tests

From repo root:

```bash
python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -v
```

Latest recorded run summary is in `experimental/punkti-v0.6-static/evidence/test_results.json`.

## Independent acid test

`tests/acid_test_independent.py` is a standalone script (not part of the
unittest suite) that proves the core Issue #20 claim without using the
prototype's own static server:

```bash
python3 experimental/punkti-v0.6-static/tests/acid_test_independent.py
```

It publishes with node A, stops A (there is no daemon to keep alive), serves
the generated directory with a plain `python3 -m http.server`, replicates
from a separate node over static GETs only, checks mutual convergence, and
re-parses the same origin with the independent clean-room reader.

## Run benchmark

From `experimental/punkti-v0.6-static/`:

```bash
PYTHONPATH=src python3 -m staticpub.bench
```

This writes:

- `evidence/bench_static.json`
- `evidence/bench_mesh.json`

## Notes

- The prototype is loopback-only and experimental.
- The static source is a plain stdlib static HTTP server; no dynamic Punkti daemon is required during replication.
- Approved carrier/spatial logic is imported from `experimental/punkti-v0.6-mesh/src` and not forked.
