# CODEX_TASK_33 — Unbreak the canonical image workflow on `main` (CEO-OS #33 release blocker)

## Context

`main` is the consolidated Punkto release candidate for the Founder-authorised production
cutover of `punkto.xyz` (CEO-OS issue #33). The Founder pinned the release candidate to
`54a4dccfd59660191de295da6ef63168b28a388c`.

The canonical release image workflow `.github/workflows/punkto-image.yml` **cannot build on
`main`**: it fails fast on the first test step. Without a green image build there is no
release image, so the cutover cannot proceed.

## Observed failure (reproduce locally)

```
$ python -m unittest discover -s experimental/punkti-v0.6-mesh/tests
FAIL: test_06_wire_spec_exists (test_mesh.AcceptanceTests.test_06_wire_spec_exists)
AssertionError: 'PUSH' not found in '# Historical proposal superseded\n\n...'
Ran 37 tests in 3.396s
FAILED (failures=1)
```

GitHub Actions run `41034592139` (workflow_dispatch, `punkto-image.yml`, main `54a4dcc`):
`browser-e2e` = success, `image` = **failure**.

### Root cause 1 — the mesh wire-spec test asserts against a superseded document

`experimental/punkti-v0.6-mesh/tests/test_mesh.py::test_06_wire_spec_exists` reads
`docs/proposals/PUNKTI_0_6_MESH.md` and asserts it contains the terms
`PUSH`, `Range PULL`, `cursor`, `UNVERIFIABLE-alg`.

Commit `d5d53c0` ("wip(v0.6): spatial-only correction work in progress") replaced that
document's 204-line body with a 3-line stub titled "Historical proposal superseded", because
the Founder's spatial-only correction made the mesh proposal non-normative and moved the
normative mesh wire/sync semantics into `docs/proposals/PUNKTI_0_6_LAYER3_RESET.md`.

The test was never updated, so it now fails on a document that was *deliberately* superseded.
This is a stale test, **not** a protocol regression.

### Root cause 2 — vendored carrier drifted by one comment line

The same workflow runs:

```
cmp experimental/punkti-v0.6-mesh/src/carrier.py punkti_node/carrier.py
cmp experimental/punkti-v0.6-mesh/src/spatial.py punkti_node/spatial.py
```

`spatial.py` compares byte-identical. `carrier.py` differs by exactly one added comment line:

```
--- experimental/punkti-v0.6-mesh/src/carrier.py
+++ punkti_node/carrier.py
@@ -71,6 +71,7 @@
     if type(atom['t']) is not int or not 0 <= atom['t'] <= 9007194740991:
         raise ValueError('timestamp')
     h = atom['h']
+    # Spatial structure is mandatory even when the algorithm is unsupported.
     parse_h(h)
```

CI never reached this step because it failed at the earlier one. It is a real failure that
must be fixed for the image job to complete.

## Your task

Make the canonical image workflow pass on `main` **without changing any protocol,
wire-format, or normative semantics**. This is a CI/documentation-hygiene fix only.

### Requirement A — fix the stale wire-spec test

`experimental/punkti-v0.6-mesh/tests/test_mesh.py::test_06_wire_spec_exists` must assert the
wire/sync specification against a document that is **currently normative**.

The normative source for the mesh wire and sync semantics is now
`docs/proposals/PUNKTI_0_6_LAYER3_RESET.md`. Verified locally, that document contains all
four required terms:

| term | `PUNKTI_0_6_LAYER3_RESET.md` | `PUNKTI_0_6_MESH.md` (stub) |
| --- | --- | --- |
| `PUSH` | present | absent |
| `Range PULL` | present | absent |
| `cursor` | present | absent |
| `UNVERIFIABLE-alg` | present | absent |

Change the test to read `docs/proposals/PUNKTI_0_6_LAYER3_RESET.md` and keep the same four
required terms. Keep the test's intent — it must still fail if the normative wire/sync
semantics are missing from the normative document. Do **not** weaken the assertion to an
empty/skip/trivial check, and do not delete the test.

Additionally, the test should assert that the superseded stub still *points at* the
normative sources, so the pointer cannot silently rot. `docs/proposals/PUNKTI_0_6_MESH.md`
currently contains the links `PUNKTI_0_6_LAYER3_RESET.md`, `PUNKTI_0_6_SPATIAL_XY_Z.md`,
`PUNKTI_0_6_PUBLICATION.md`, `PUNKTI_0_6_VECTORS.md`. Assert that the stub references the
normative carrier/spatial documents it claims to defer to.

Do **not** restore or rewrite the old mesh proposal body. The Founder superseded it; the
historical proposal is preserved in Git history by design.

### Requirement B — make the two vendored copies byte-identical

`experimental/punkti-v0.6-mesh/src/carrier.py` and `punkti_node/carrier.py` must be
byte-identical so the workflow's `cmp` gate passes.

The drifted line is a comment in `punkti_node/carrier.py`:

```python
    # Spatial structure is mandatory even when the algorithm is unsupported.
```

Apply the **same** comment to `experimental/punkti-v0.6-mesh/src/carrier.py` at the same
place. Do **not** delete the comment from `punkti_node/carrier.py` — `punkti_node/` is the
shipped runtime and its current content is what has been reviewed, tested and deployed; the
vendored copy under `experimental/` is the one that should be brought into line with the
shipped runtime.

After the edit, `cmp` must report no difference for **both** carrier.py and spatial.py.

### Hard constraints

- **Do not change** any file under `punkti_node/` other than as specified in Requirement B
  (i.e. do not touch `punkti_node/carrier.py` at all).
- **Do not change** any normative document content
  (`docs/proposals/PUNKTI_0_6_LAYER3_RESET.md`, `..._SPATIAL_XY_Z.md`, `..._PUBLICATION.md`,
  `..._STATIC_PUBLICATION.md`, `..._VECTORS.md`).
- **Do not change** protocol behaviour, wire format, validation, limits, or publication code.
- **Do not** weaken, skip, xfail, or delete any test. Do not add `--exclude`, `xfail`, or
  `skip` decorators.
- **Do not** touch the workflow file `.github/workflows/punkto-image.yml` — the gate itself
  is correct and must keep gating.
- Do not modify `experimental/punkti-v0.6-mesh/tests/test_mesh.py` beyond
  `test_06_wire_spec_exists`.
- Do not add secrets, credentials, or tokens. Do not commit anything under `config/`,
  `data/`, or `backups/`.
- Do not bump any version number, tag, or CHANGELOG entry that would imply a release.

### Verification you must perform and report

Run these from the repository root and paste the real output in your final report:

```bash
# 1. The previously failing suite
python -m unittest discover -s experimental/punkti-v0.6-mesh/tests -v

# 2. The full set of test steps the image workflow runs, in workflow order
python -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python -m unittest punkti_node.test_spatial_only
python3 experimental/punkti-v0.6-mesh/tests/measure.py
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-slice5.mjs
node pwa/test-ai-coldstart.mjs
node pwa/test-ai-hostile.mjs
node pwa/test-ai-cli.mjs
for test in relay/test_*.py tools/test_*.py; do
  test_data=$(mktemp -d)
  PUNKTO_DATA_DIR="$test_data" PUNKTO_NODE_KEY="$test_data/key.json" \
    PUNKTO_ATOM_LOG_PATH="$test_data/atoms.jsonl" python "$test"
  rm -rf "$test_data"
done
for module in pwa/*.js pwa/*/*.js; do node --check "$module"; done
node --input-type=module --check < pwa/app.js
cmp experimental/punkti-v0.6-mesh/src/carrier.py punkti_node/carrier.py
cmp experimental/punkti-v0.6-mesh/src/spatial.py punkti_node/spatial.py
python -m punkti_node --check-config --config node-config.example.yml
PUNKTO_WEB_ROOT="$PWD/pwa" python -m punkti_node --check-config --config punkto-config.example.yml
```

Every one of these must pass with exit code 0. `cmp` must print nothing.

### Out of scope

Do not attempt any deployment, Docker build, image publish, tag, release, or network access.
Do not create or modify GitHub workflows. Do not touch the PWA or the AI-first client.
Do not attempt to fix anything you find that is unrelated to the two failures above — if you
find another genuine problem, report it in your final message instead of fixing it.

### Deliverable

Change **exactly two files**:

- `experimental/punkti-v0.6-mesh/tests/test_mesh.py` (Requirement A)
- `experimental/punkti-v0.6-mesh/src/carrier.py` (Requirement B)

**Do not commit and do not push.** The operator will review the diff and commit from a
shell outside the sandbox.
