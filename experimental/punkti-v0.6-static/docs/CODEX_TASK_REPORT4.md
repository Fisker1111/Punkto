# Codex follow-up #8 — refresh the suite evidence and re-render the docs

## Context

Follow-up #7 repaired the report generator. The suite now has **38 tests**
(was 34) because follow-up #7 added four report-rendering tests.

However `evidence/test_results.json` still records the OLD run:

```json
{
  "command": "python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -v",
  "returncode": 0,
  "status": "OK",
  "ran": 34,
  "seconds": 16.56
}
```

`docs/STATIC_PUBLICATION_REPORT.md` renders section 1 and section 9 from that
file, so it currently claims `ran: 34` while the suite actually runs 38
tests. That is stale evidence and must be corrected — never leave a stale
number in the founder-facing report.

## Files you own

- `experimental/punkti-v0.6-static/evidence/test_results.json` — the recorded
  suite result.
- `experimental/punkti-v0.6-static/docs/STATIC_PUBLICATION_REPORT.md` and
  `docs/BENCHMARK.md` — only as regenerated output.

Do NOT change any Python source or test file. Do NOT change any benchmark
measurement. Do NOT commit. Do NOT push.

## Required steps

1. From the repo root, run the suite and capture the real result:

   ```bash
   cd <repo root>
   python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -v
   ```

   It must end in `OK` with `Ran 38 tests`. If it does not, STOP and report
   the failure — do not record a passing result you did not observe.

2. Rewrite `experimental/punkti-v0.6-static/evidence/test_results.json` with
   the SAME JSON shape as now (`command`, `returncode`, `status`, `ran`,
   `seconds`), with the real observed values. `command` should stay the same
   command string. `status` should be `OK` (the literal the renderer already
   understands) and `returncode` the real exit code (0). `ran` must be the real
   number of tests that ran and `seconds` the real wall time of that run.

3. Re-render the docs from the CURRENT evidence:

   ```bash
   cd experimental/punkti-v0.6-static
   PYTHONPATH=src python3 -c "from staticpub import bench; bench.regenerate_docs_from_evidence()"
   ```

4. Re-run the command from step 3 a second time and confirm the two rendered
   files are byte-identical (idempotent).

5. Verify the re-rendered `docs/STATIC_PUBLICATION_REPORT.md`:
   - section 1 now shows the new `ran` value (38) and the new seconds;
   - section 9's suite line shows the same new values;
   - every hostile-case line still names its real test and shows the suite
     state derived from the evidence;
   - no `n/a` placeholder appears where a real value is expected;
   - the 12-section structure is unchanged.

6. Re-run the suite once more after the evidence/doc rewrite to confirm it is
   still green (`Ran 38 tests ... OK`).

## Stop condition

Report: the exact JSON content you wrote to `evidence/test_results.json`, the
md5sums of both rendered docs before and after the second render (proving
idempotency), the exact unittest summary lines from steps 1 and 6, and the
pasted section 1 and section 9 of the re-rendered report.
Do not commit. Do not push.
