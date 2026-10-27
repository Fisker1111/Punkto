# Codex follow-up #7 — repair the evidence-driven report generator

## Context

CEO-OS Issue #20 (static publication + read-only node replication experiment)
prototype lives in `experimental/punkti-v0.6-static/`. The 100k scale run
completed and all evidence files are final:

- `evidence/bench_static.json`
- `evidence/bench_mesh.json`
- `evidence/test_results.json`
- `evidence/publication_example.json`

The founder-facing report is rendered from evidence by
`src/staticpub/bench.py::generate_static_report_markdown()`.

**Current defect (the only blocker):** the report template in section 2
("Exact directory/object examples") interpolates these names, none of which
exist in the function scope:

- `example_root_seq`
- `example_root_head`
- `example_root_updated`
- `example_manifest_seq`
- `example_record_count`
- `example_pack_count`
- `example_index_prefix`
- `example_index_digest`
- `example_leaf_prefix`
- `example_leaf_record_count`
- `example_leaf_pack_count`
- `example_record_path`
- `example_segment_path`
- `example_mutable_count`
- `example_mutable_bytes`

Result: `NameError: name 'example_root_seq' is not defined` at
`src/staticpub/bench.py` line ~998. This makes 7 of the 34 tests in
`experimental/punkti-v0.6-static/tests/test_static_publication.py` error out
(the report-rendering tests), and it makes
`regenerate_docs_from_evidence()` unusable.

Note: `docs/STATIC_PUBLICATION_REPORT.md` on disk was hand-assembled after an
earlier crash, so it does NOT match what the generator produces. After your
fix, the generator must be the single source of truth again.

## Files you own

- `experimental/punkti-v0.6-static/src/staticpub/bench.py` — ONLY the report
  generator (`generate_static_report_markdown`) and its new helper(s).
- `experimental/punkti-v0.6-static/tests/test_static_publication.py` — you may
  ADD tests. Never weaken, delete, skip or rename existing tests.

Do NOT change: publisher, reader, store, carrier_io, cleanroom, harness,
httpsource, `run_scale_100k`, `run_all`, `run_scale_only`,
`generate_benchmark_markdown`, `regenerate_docs_from_evidence`'s behaviour
beyond passing the new example data through, or any protocol/semantic
behaviour.

Do NOT commit. Do NOT push. Do NOT re-run the 100k scale benchmark.

## Required behaviour

1. `generate_static_report_markdown(static_data, mesh_data, test_data)` must
   keep its current 3-positional-argument signature working (existing tests
   call it that way). Add an OPTIONAL 4th parameter, e.g.
   `publication_example=None`.

2. When `publication_example` is `None`, the function must fall back to
   loading `evidence/publication_example.json` relative to the module's
   `ROOT`. If that file is missing or unreadable, the report must render the
   literal text `publication example not recorded in evidence` in section 2
   instead of raising.

3. Every `example_*` placeholder must be derived from the publication example
   data at render time. No hardcoded values. Mapping (from the real file
   `evidence/publication_example.json`):

   - `example_root_seq` <- `root.seq`
   - `example_root_head` <- `root.head`
   - `example_root_updated` <- `root.updated_at`
   - `example_manifest_seq` <- `manifest.seq`
   - `example_record_count` <- `manifest.record_count`
   - `example_pack_count` <- `manifest.pack_count`
   - `example_index_prefix` <- the single key of `manifest.index`
   - `example_index_digest` <- the single value of `manifest.index`
   - `example_leaf_prefix` <- `leaf_shard.prefix`
   - `example_leaf_record_count` <- `len(leaf_shard.records)`
   - `example_leaf_pack_count` <- `len(leaf_shard.packs)`
   - `example_record_path` <- `record_example_path`
   - `example_segment_path` <- `segment_example_path`
   - `example_mutable_count` / `example_mutable_bytes` <- the mutable-file
     count/bytes already computed in the function from the benchmark evidence
     (the same values used in section 1's mutable-file accounting line).

   If any individual field is missing from the example data, render a neutral
   placeholder such as `n/a` for that field only — never raise, never invent
   a number.

4. `regenerate_docs_from_evidence()` must pass the loaded
   `evidence/publication_example.json` into the generator.

5. Re-render the docs from the CURRENT evidence files and leave them on disk:

   ```bash
   cd experimental/punkti-v0.6-static
   PYTHONPATH=src python3 -c "from staticpub import bench; print(bench.regenerate_docs_from_evidence())"
   ```

   `docs/STATIC_PUBLICATION_REPORT.md` and `docs/BENCHMARK.md` must then be
   exactly what the generator produces (idempotent: running the command
   twice must produce a byte-identical file).

6. The rendered report must keep its 12 numbered sections and their headings,
   and must still render every issue-required hostile case with its real test
   name and the suite PASS/FAIL state taken from `evidence/test_results.json`
   (never an unconditional PASS claim).

## Tests

Add fast tests proving:

- the rendered report contains the real values from
  `evidence/publication_example.json` (e.g. the root head digest, the record
  example path, the leaf prefix) — i.e. no unresolved placeholder and no
  `NameError`;
- when the publication example is missing, the report renders
  `publication example not recorded in evidence` and does NOT raise;
- the report contains the 100k mode-A vs mode-B request counts and the derived
  ratio (keep/verify the existing coverage);
- the report states the suite status from `evidence/test_results.json` and, when
  that evidence says the suite failed, does NOT claim PASS (keep/verify the
  existing coverage).

Run the whole suite from the repo root:

```bash
cd <repo root>
python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -v
```

**All tests must pass (0 errors, 0 failures) — currently 34 tests with 7
errors.** Report the exact "Ran N tests ... OK" line.

## Stop condition

Report: files changed, test count before/after, the exact unittest summary
line, and paste the rendered section 2 and section 9 from a real
`regenerate_docs_from_evidence()` call against the CURRENT evidence files.
Do not commit. Do not push.
