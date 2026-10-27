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
