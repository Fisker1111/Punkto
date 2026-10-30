# CODEX TASK 28b — wire the discovery prototype suite into PR CI

**Status:** ACTIVE
**Base branch:** `experiment/punktto-discovery-index-v1` (HEAD includes the
prototype implementation commit `6d03007` and the spec/brief commit `4ebed41`).
**CEO-OS issue:** https://github.com/Fisker1111/CEO-OS/issues/28

## Context

The prototype in `experimental/punktto-discovery-index/` has a stdlib
`unittest` suite (26 tests) that currently runs only locally. PR CI
(`.github/workflows/pilot-ci.yml`) does not run it, so a reviewer opening the
PR would see no automated verification of the new code.

## Task

Add CI wiring **only** — no changes to the prototype's own source or tests
unless a CI wiring defect makes them unrunnable.

1. In `.github/workflows/pilot-ci.yml`, add a **separate job** (do not modify
   the existing `pwa-validation` or `relay-tests` jobs) that:
   - runs on `pull_request` to `main` (same trigger as the existing workflow);
   - checks out the exact commit;
   - sets up Python 3.12 (`actions/setup-python@v5`);
   - installs the repo's existing dependencies only —
     `python -m pip install -r node/requirements.txt`;
   - runs the discovery suite:
     `python -m unittest discover -s experimental/punktto-discovery-index/tests -t .`
   - also runs the existing node publication suite, which the new
     `punkti_node/config.py` / `punkti_node/store.py` optional-`index` change
     touches:
     `python -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication`
   - prints a step summary line with the tested SHA.
2. Name the job something like `discovery-prototype` and give it a clear
   `name:` that says it is a prototype/experiment gate, not a production
   publish gate. It must NOT be added as a `needs:` dependency of any
   publishing/image job, and must not gate a release.
3. Do not change the triggers of the workflow, the existing jobs, or any other
   workflow file.
4. Verify locally that both commands still pass, then run
   `python3 -m unittest discover -s experimental/punktto-discovery-index/tests -t .`
   and the node suite from the repository root and report the real output.

## Boundaries

* No new dependency beyond `node/requirements.txt`.
* No changes to `experimental/punktto-discovery-index/**` source or tests.
* No changes to `punkti_node/**`.
* No push, no PR, no deployment, no merge.

## Git

Commit locally on the current branch with a focused commit message. Report the
exact SHA, the diff, and the real test output.
