# Issue #30: spatial-only v0.6 conformance

Date: 2026-10-29. Implementation base: `f4e6f87`; interrupted WIP: `d5d53c0`.
Normative authority: punkti-org/punkti Stage A
`47537960166e33ed806a4349b81b6a54c5ab3e00`, fetched as `punkti/spatial-only`.
No contradiction with the implementation brief was found. This is implementation
verification, not a protocol re-freeze, deployment approval, or manual UX acceptance.

## Before and after

| Input or behavior | Pre-correction draft | Corrected v0.6 |
|---|---|---|
| Signed empty h | Accepted, outside XY tree | INVALID-structural, including unsupported alg |
| Missing/null/malformed h | Empty/default paths existed in clients | Rejected before algorithm dispatch; never repaired |
| Canonical h | XY_Z or empty | Only XY_Z, total 6..32, XY 4..12, unchanged exact decimal Z |
| Publication `~` index/shard/child | Reserved unanchored routing | Rejected clearly, before scope pruning |
| Unrestricted scope | Anchored plus unanchored bucket | All anchored records, including `0000_0` |
| CLI without an address | Could write empty h | write/post/reply fail with the explicit spatial-address message |
| CLI post command | Unsupported | Alias of write; ref remains reply-only |
| Punkto reply | Location fallback could lack h | Exact parent h copied; invalid parent rejected |

The positive spatial round-trip test now uses a fractional Z that reaches exactly
32 characters with XY precision 12. It also explicitly rejects the former
34-character test address through both parse and encode. No limit or grammar was
relaxed. C/S/MID/R framing and the frozen v0.5.1 adapter are unchanged.

## Vector inventory

Counts are read from `pwa/punkti/test-vectors/*-vectors.json`; “before” is the
byte-identical base copy in `pwa/punkti/legacy-unanchored/test-vectors/`.
Publication case counts include successful reads, expected failures, and carrier
cases embedded in the normative V10/V12 groups, not just top-level group IDs.

| Inventory | Before | After |
|---|---:|---:|
| Carrier fixtures: verified positive / unknown-alg candidate | 17 / 1 | 17 / 1 |
| Publication vector groups | 9 | 12 |
| Publication cases: positive / negative / unknown-alg candidate | 13 / 12 / 0 | 16 / 58 / 1 |
| Publication cases, total | 25 | 75 |
| Spatial ground-truth rows (three XY precisions each) | 8 (24 encodings) | 8 (24 encodings) |
| Spatial measured-height inputs / ordered-Z values / scope groups | 13 / 10 / 4 | 13 / 10 / 4 |
| Spatial negative h / Z / scope inputs | 6 / 11 / 5 | 14 / 11 / 5 |

All 12 publication vector groups match Stage A JSON exactly after removing only
the four local V11 `source` fixture names. Two independent regenerations match
the committed publication JSON and generated vector documentation byte-for-byte.
New signed positive fixtures use explicit anchors (including `u3bu_23`,
`0000_0`, and the normative V4 addresses). Existing signed historical bytes are
never edited or re-signed.

## Independent agreement and immutable history

`pwa/test-spatial-only-agreement.mjs` invokes the real Python validators in
`punkti_node/test_spatial_only.py` and the browser JS carrier/reader. It checks
64 carrier cases (18 carrier fixtures + 42 V10 negatives + 4 V12 cases), all
29 publication read cases, and four A→B static replications (packs on/off ×
unrestricted/restricted XY+Z). Both implementations verify digests, MID and
signatures. Hash-valid `~` attacks, invalid signature variants, candidates,
missing/corrupt objects, stale roots and pack membership are covered. Seven
additional L4 assertions check exact-h replies and invalid parents. Pilot CI now
runs this harness; the existing publication harness still checks 119 assertions.

`archive-digests.json` inventories 20 frozen files across all six experimental
packages and the PWA vectors. Every archive was compared directly with its
original `git show f4e6f87:<path>` bytes and SHA-256: 20/20 identical. Archives
are copied into explicitly named `legacy-unanchored/` directories and excluded
from positive suites; old evidence reports retained at their historical paths
are explicitly labelled historical. Corrected fixtures are separate files.
The Python tests verify the old signature/MID directly, reject the same raw R
at store and `/submit` (also when claiming an existing valid MID), preserve the
log and publication root, and prove it is not silently republished.

Normative proposal documents are copied Stage A text, with provenance headers
and relative links adapted. Historical Mesh/static proposals point to those
sources. Old task briefs and experiment reports have superseded banners;
current `/ai`, integration and reply guidance describe anchored-only behavior.

## Final checks and exact commands

All commands run from the repository root; no remote node was contacted by tests.
“Suite pass” is used where the JS harness does not count individual assertions.

| Command | Final result |
|---|---|
| `python3 -m unittest discover -s . -p 'test_*.py' -t .` | 105 passed, 0 failures/errors |
| `node pwa/test-ai-cli.mjs` | 1 suite passed; write/post/reply missing/invalid h and successful post/exact-h reply |
| `node pwa/test-ai-coldstart.mjs` | 11 cold-start steps passed |
| `node pwa/test-ai-hostile.mjs` | 9 hostile cases and page checks passed |
| `node pwa/test-exact-identity.mjs` | 1 suite passed |
| `node pwa/test-punkti-publication.mjs` | 119 assertions passed |
| `node pwa/test-punkti-vectors.mjs` | 211 spatial + 288 carrier assertions; 18 fixtures byte-identical; JS/Python agree |
| `node pwa/test-slice5.mjs` | 1 suite passed |
| `node pwa/test-spatial-xy-z.mjs` | 219 assertions passed; reference/clean-room agreement |
| `node pwa/test-spatial-only-agreement.mjs` | 64 carrier + 29 publication + 4 replications + 7 L4 checks passed |
| `node pwa/test-punkti-static-e2e.mjs` | NOT RUN: Playwright not installed; dependency check exits 1 |
| `python3 relay/test_relay.py` | 57/57 passed |
| `python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests -p 'test_*.py'` | 70 passed |
| `python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests -p 'test_*.py'` | 37 passed |
| `PYTHONPATH="$PWD/experimental/nairobidot-l3/src" python3 -m unittest discover -s experimental/nairobidot-l3/tests -p 'test_*.py'` | 34 passed |
| `python3 -m unittest discover -s experimental/punkti-v0.6-freeze/tests -p 'test_*.py'` | 14 passed |
| `python3 -m unittest discover -s experimental/punkti-v0.6-static/tests -p 'test_*.py'` | 38 passed |
| `PYTHONPATH="$PWD/experimental/punkti-v0.6-hostile/src" python3 -m unittest discover -s experimental/punkti-v0.6-hostile/tests -p 'test_envelope_adversarial.py'` | 98 passed; 98/98 agreement per implementation, 0 divergences/defects |
| `python3 experimental/punkti-v0.6-publication/scripts/check_vectors.py` | 2 artifacts byte-identical on 2 regenerations |
| `python3 -m unittest punkti_node.test_spatial_only.SpatialOnly.test_frozen_archive_bytes` | 1 test passed, all 20 archive digests |
| `git diff --check` and `git diff --check f4e6f87` | Clean |

Syntax commands (12/12 exit 0):

```sh
node --check pwa/app.js
node --check pwa/ui-shell.js
node --check pwa/ui-text.js
node --check pwa/ui-map.js
node --check pwa/ui-board.js
node --check pwa/ui-create.js
node --check pwa/ui-settings.js
node --check pwa/key-management.js
node --check pwa/sw.js
node --input-type=module --check < pwa/app.js
node --input-type=module --check < pwa/ui-map.js
node --input-type=module --check < pwa/ui-board.js
```

During completion the reported overlength test and CLI ref mismatch were
reproduced. The CLI invalid-MID negative was given a valid h so it continues to
exercise reference validation. Experimental positive fixtures and scope tests
still relying on empty h were corrected to explicit addresses. NairobiDot's
internal `None` metadata for opaque future-version transport remains unchanged;
a v0.6 `h: null` remains structurally invalid. Final results above supersede these
intermediate failures. Test-generated historical report churn was discarded.

## Deliberately not performed

- Browser static E2E/manual UX: Playwright is absent. This is a pre-existing
  dependency, not a pass or a regression; that suite is not in Pilot CI.
- Docker static acceptance (`scripts/acceptance_static_first.sh`): Docker is not
  installed (`command -v docker` exits 1). Local static replication is tested by
  the Python/JS harness and experimental static/publication suites.
- Full optional hostile network/scale experiments and fresh benchmark reports: outside
  this bounded correction; only the changed envelope cases were rerun.
- No deployment, remote server changes, PR creation, or changes to draft PR #124
  or #125 branches. CI/deployment approval and human acceptance are separate gates.

See `files-changed.tsv` for per-file additions/deletions from the implementation
base, including the interrupted WIP. `completion-files.tsv` isolates this final
completion commit from `d5d53c0`. The inventory files omit their own rows.
