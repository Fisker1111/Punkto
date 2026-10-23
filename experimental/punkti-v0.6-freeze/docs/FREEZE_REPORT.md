# Punkti 0.6 Founder-review freeze report

## 1. Scope, base and commits

CEO-OS Issue #17; branch `freeze/punkti-0.6-spec-revision`. Phase 2 starts at
`cee82627f7a2eed056aedcf692e9f520012b495e`. The Phase 1 comparison base is
`aea705e` (the Issue #13 hostile-network report).
Nothing is merged, pushed, deployed, released or frozen by this work. A freeze
requires separate Founder approval. This is an experimental conformance package,
not a production release or authorization to deploy.

Phase 1 committed objects inspected for this report:

- `9718d3c176172e3d97c51cd1bad99de34476436e`: focused specification revisions.
- `a8a3a977864d339eaee9d52882de46215ce57190`: reference implementation and tests.
- `535034b8a8a63b5e007a8deb283f201d20a3acd3`: independent clean-room alignment and tests.
- `cee82627f7a2eed056aedcf692e9f520012b495e`: revised hostile expectations and regenerated evidence.

Phase 2 vectors commit: `050012be0a6948a96bdab8d037c4bcb38644fa88`. The following report-only commit contains
this document; its exact SHA is recorded in the uncommitted root `PHASE2_REPORT.md`
and the final handoff (a commit cannot contain its own SHA).
`PHASE1_REPORT.md` and `PHASE2_REPORT.md` are deliberately not committed.
No protocol implementation source changed in Phase 2. The only shared tooling
changes are additive `import_json` and `pull_from` adapter commands. The Mesh
proposal receives only the requested wrapping and stray-space cleanup.

## 2. Exact specification changes

The N1–N11 crosswalk below groups the revised contract by topic. Section names
refer to the Phase 1 committed proposals, not the unrevised historical report.

| Item | File and section | Revised rule |
|---|---|---|
| N1: ranges | `docs/proposals/PUNKTI_0_6_LAYER3_RESET.md`, Synchronization semantics; `docs/proposals/PUNKTI_0_6_MESH.md`, Subscriptions and cursors | Reject equal/reversed MID, h and Z endpoints when both are present; null is unbounded; h comparison is literal; invalid subscriptions fail at construction. |
| N2: error tiers | Mesh, HTTP operations / Normative error tiers | Exactly address/sha256/record in each wrapper; descriptor errors are request-level 400 with no admission; content failures are per-record 200 rejection; unknown algorithms/versions remain candidates; legacy namespace is rejected per-record. |
| N3: resource limits | Mesh, Normative error tiers | Size/limit excess is 413, including page 33; malformed limit types or values below 1 are 400; an oversized decoded R is 413 with no admission from the request. |
| N4: HELLO | Mesh, Required hello.limits members | Required integer body/record/page/http/candidates names and units; additional members permitted, lower policy maxima permitted; both experiments advertise exactly the five specified maxima. |
| N5: cursors | Mesh, Subscriptions and cursors | Initial/empty MID after is null, nonempty MID continuation is an address/digest pair; spatial after is an integer initially 0; clients echo server tokens. |
| N6: timestamp import | Reset, Atom envelope / Canonical bytes and immutable addressing; Mesh, opening carrier rules | Exact unsigned spelling `0\|[1-9][0-9]*`, bounded by 9007199254740991; explicitly reject -0 and other noncanonical spellings without changing canonical bytes. |
| N7: discovery | Mesh, Discovery and convergence | Skip malformed/unreachable HELLOs and invalid individual origins, keep valid siblings, deduplicate and exclude self; never crawl, configure peers or admit records from hints. |
| N8: peer failures | Mesh, Peer failures and interrupted pages | Distinguish unreachable/timeout/protocol/resource semantically; wording is implementation-defined; use documented local deadlines, not a fixed protocol deadline. |
| N9: page atomicity | Mesh, Peer failures and interrupted pages | Truncated/unreadable/invalid JSON admits nothing; fully decoded pages prevalidate every descriptor and carrier; invalid content aborts the page without admission or checkpoint advancement. Earlier completed pages remain committed. |
| N10: reciprocal sync | Mesh, Peer failures and interrupted pages | connect is orchestration; each /sync runs one nonrecursive phase; bounded callbacks may exceed ordinary deadlines; failed operations do not advance their checkpoints. |
| N11: completeness | Mesh, final reconciliation paragraphs | Coverage, sync success, finite peer sets, cursors and end:true cannot establish global completeness or freshness. |

Canonical C/S/MID/address/R/signature framing is unchanged by Phase 1. The
specific N3 oversized-record rule takes precedence over generic N2 descriptor
400 wording. Ordinary requests use local 5-second deadlines; reciprocal /sync
requests use 300 seconds. Neither number is a universal protocol deadline.

## 3. Exact implementation changes

Reference (`experimental/punkti-v0.6-mesh/src/`), Phase 1:

- `carrier.py`: `unsigned_integer` parser enforces unsigned timestamp spelling
  during JSON import, including rejecting -0.
- `spatial.py`: existing equal/reversed rejection retained; error wording aligned.
- `mesh.py`: exact wrapper members/address/digest validation; validation-only
  admission pass for whole PUSH descriptors and decoded PULL pages; legacy
  per-record rejection; 413 for page/batch excess; bounded query size; null MID
  sentinel with pair validation; explicit short Content-Length detection and
  nonfinite-JSON rejection; discovery skips malformed peers/hints independently;
  sync failure handling expanded; reciprocal callback deadline set to 300 s.

Clean-room (`experimental/nairobidot-l3/src/nairobidot/`), Phase 1:

- `carrier.py`: carrier JSON integer parsing explicitly enforces unsigned spelling.
- `spatial.py`: normalized h/Z scopes reject equal or reversed bounds, also at
  construction through normalization.
- `node.py`: five HELLO limit names; exact descriptor members and request-level
  digest/address errors; validation-only admission pass before PUSH/PULL mutation;
  MID range rejection; short-response detection and resource-error preservation;
  independent filtering of discovery hints; 300 s reciprocal callback deadline.
  Its existing null MID sentinel remains unchanged.

Phase 1 tests changed in reference `tests/test_carrier.py`, `test_mesh.py`,
`test_store.py`, and new `test_revision.py`; clean-room `tests/test_node.py`,
`test_spatial.py`, and new `test_revision.py`; interop `test_interop.py`; hostile
`src/hostile/cases_protocol.py`, `tests/test_coverage_eclipse.py`,
`test_cursor_spatial.py`, and `test_replay_provenance.py`. The interop matrix/report
and hostile protocol/network evidence were regenerated in Phase 1.

Phase 2 adds `experimental/punkti-v0.6-freeze/README.md`, `src/vector_suite.py`,
`src/make_vectors.py`, `tests/test_vectors.py`, `vectors.json`,
`docs/NORMATIVE_VECTORS.md`, and this report. In the existing shared
`experimental/nairobidot-l3/interop/adapter_common.py`, `import_json` delegates
exact decoded bytes to the implementation; `pull_from` delegates to reference
`Node.pull` with Subscription and mode, or clean-room `Node._pull_from`, which owns
its checkpoint. Both commands expose ok/error through existing RPC plumbing.
The clean-room one-page `pull` RPC is deliberately not used to test V8 checkpoints.

## 4. Normative vectors and results

Ten normative vectors, twenty independent implementation executions, ten
ref/nb normative-output comparisons: all pass. Eleven freeze unittest methods
cover the ten vectors and an explicit exercised-ID inventory. One V5 empty-PUSH
subcase is labelled `non_normative: true`, recorded, and excluded from normative
pass/fail and equality totals.

| ID | Title | Reference | Clean-room | Normative equality |
|---|---|---|---|---|
| V1 | canonical-record | PASS | PASS | PASS |
| V2 | initial-mid-cursor | PASS | PASS | PASS |
| V3 | range-rejection | PASS | PASS | PASS |
| V4 | spatial-boundary | PASS | PASS | PASS |
| V5 | descriptor-errors | PASS | PASS | PASS |
| V6 | content-errors | PASS | PASS | PASS |
| V7 | timestamp-grammar | PASS | PASS | PASS |
| V8 | interrupted-page-atomicity | PASS | PASS | PASS |
| V9 | opaque-preservation | PASS | PASS | PASS |
| V10 | hello-limits | PASS | PASS | PASS |

[NORMATIVE_VECTORS.md](NORMATIVE_VECTORS.md) and [vectors.json](../vectors.json)
pin the exact JSON input bytes/request targets, expected statuses/results, state
transitions and seven canonical fixtures: atom, C, S, MID, address, R, sig and
sha256_R. Minting uses each implementation's own signing path with
SHA256(b"punkti-0.6-freeze-vectors"). Every fixture agrees byte-for-byte. Generation
runs all vectors before publishing either artifact, and a second generation
produced identical artifact SHA-256 hashes. Tests load the artifact without
regenerating expectations. Epochs and ports are runtime-bound, not fixed values.

V2 separately proves empty MID after:null and nonempty address/digest continuation.
V4 independently decodes Z bits and asserts the two adjacent s-cell altitude
ordering; its h scope excludes the extreme fixtures. V8 exercises both truncated
HTTP and a fully decoded mixed valid/forged page: no admission on failure, null
cursor on retry, one admission on success, then reuse of the successful token
without another log entry. V9 preserves the exact unsupported-algorithm R and
opaque Unicode/refs/extensions on both nodes while retaining a distinct VALID MID.

The harness imports neither implementation. It reuses the existing driver
Adapter/http/HERE, runs isolated subprocesses and uses actual loopback HTTP. V8's
controlled peer uses only stdlib http.server. No dependencies were added.
`import_json` intentionally exposes only ok/error: V7 verifies accepted exact
JSON equals the pinned atom and independently mints/checks its zero-timestamp C/R;
it cannot directly inspect the return bytes of import_json through that command.

## 5. Before/after ambiguity table

Before evidence is the committed Issue #13
[findings](../../punkti-v0.6-hostile/docs/FINDINGS.md#2b-adversarial-protocol-findings-308-cases-282-agree)
and [network report](../../punkti-v0.6-hostile/docs/HOSTILE_NETWORK_REPORT.md).
The latter lists discovery safety and eclipse/no-crawl separately; N7 covers both.
Existing revision/hostile tests supplement the ten published vectors where noted;
the new vectors alone are not claimed to cover every clause of N1–N11.

| Item | Before (#13 evidence) | Resolution | Implementation change | Vector | Status |
|---|---|---|---|---|---|
| N1 ranges | Ref rejects; nb returns empty MID page or nonmatching spatial scope for equal/reversed bounds. | 400; null unbounded; fail-fast subscriptions. | nb node.py/spatial.py rejection; ref existing rejection retained. | V3, V4; spatial tests | Resolved; PASS |
| N2 tiers | Digest/address mismatch: ref request 400, nb per-record structural rejection. Partial batch rules unclear. | All descriptors prevalidated; content remains per-record. | Both mesh.py/node.py validation-only passes, exact wrappers; nb errors promoted to request tier. | V1, V5, V6, V9 | Resolved; PASS |
| N3 limits | Page 33: ref 400, nb 413. | Resource excess 413, malformed limits 400. | ref page/batch/query limits; both retain resource refusals. | V10 advertises maxima; revision and hostile limit cases enforce refusal | Resolved; PASS |
| N4 HELLO | Different names/extras; no normative schema. | Five required integer members; experiments emit exact maxima. | nb LIMITS names aligned; ref already matched. | V10 | Resolved; PASS |
| N5 cursor | Empty first MID after was ["",""] in ref, null in nb. | Null initial MID; returned pair for nonempty; echo complete token. | ref sentinel and token validation. | V2, V8 | Resolved; PASS |
| N6 timestamp | JSON -0 accepted by ref, rejected by nb; wording implicit. | Reject all noncanonical timestamp spellings explicitly. | Both carrier parsers enforce unsigned grammar. | V7 | Resolved; PASS |
| N7 discovery | Poisoned HELLO raised KeyError/PeerError; 500-hint probe already demonstrated no auto-crawl. | Skip malformed HELLO/hints, retain good siblings; never auto-connect. | Both discovery implementations filter independently. | No new dedicated vector; both revision suites and hostile E-coverage | Resolved; PASS |
| N8 failures | Error strings/classes and timeout policy differed; no fixed taxonomy/deadline contract. | Semantic categories, implementation-defined messages, documented bounded local deadlines. | Both HTTP clients detect short bodies and propagate failure; nb preserves resource errors. | V8; hostile slow_peer/interrupted/corrupt cases | Contract clarified; tested subset PASS, no uniform exception API claimed |
| N9 page atomicity | Undecodable-page safe subset tested; decoded mixed-page transaction rule unspecified. | Validate whole page before admission; retain checkpoint on invalid page. | Both PULL receivers prevalidate and only commit cursor after processing. | V8; both revision suites | Resolved; PASS |
| N10 reciprocal sync | Reference 5000-record synchronous callback exceeded ordinary 5 s deadline; separately driven phases worked. | One nonrecursive /sync phase; longer bounded local callback deadline; no fixed-round promise. | Both connect helpers use 300 s callbacks. | Existing revision deadline assertions and hostile network suite; no new dedicated vector | Resolved contract; PASS; 5000-record scale matrix not rerun here |
| N11 completeness | Withholding/stale coverage can hide records despite end:true or successful sync. | Explicitly disclaim global completeness/freshness. | Documentation only; no dishonest detection mechanism added. | Existing hostile withholding/eclipsing cases; no new dedicated vector | Limitation explicit; PASS |

## 6. Test counts and retained hostile corpus

After counts below are from actual complete local Phase 2 runs on 2026-10-23,
with no failed assertions. Reported runtimes were reference 2.703 s, clean-room
2.340 s, interop 10.295 s, hostile 133.400 s, and freeze 7.017 s. Before counts are the actual historical runs recorded
in Issue #13's committed network report, not newly rerun baseline measurements.

| Suite | Before (#13) | After (this run) | Result |
|---|---:|---:|---|
| Reference | 27 | 32 | PASS |
| Clean-room | 23 | 28 | PASS |
| Interop | 13 | 13 | PASS |
| Hostile | 125 | 125 | PASS |
| Freeze | 0 (suite absent) | 11 | PASS |

The generator additionally passed all ten vectors on both implementations and all
ten equality checks; deterministic regeneration passed. Reference tests emitted
a non-failing ResourceWarning about HTTPError cleanup. No manual browser testing
was performed: this is protocol/tooling work with no UI change. Real loopback
HTTP and controlled failure/retry behavior were exercised automatically.

The freshly generated `experimental/punkti-v0.6-hostile/evidence/protocol.json`
contains 308 rows: **154 AGREE, 0 DIVERGE, 0 DEFECT per implementation**.
An exact set comparison of `(group, case, implementation)` against the committed
`aea705e` evidence confirms **308/308 pre-existing row keys retained**, no missing
or added keys. Its content is unchanged from Phase 1 HEAD after this rerun.
The original classifications were ref 141 AGREE / 13 DIVERGE / 0 DEFECT and nb
141 AGREE / 11 DIVERGE / 2 DEFECT; those were actual #13 observations under the
previous contract, not hidden failures removed from the corpus.

Hostile expectations were updated to the revised normative contract in Phase 1,
not silently dropped. In particular -0, descriptor errors, page limits, cursor
sentinel, equal/reversed bounds, HELLO limits and poisoned discovery now assert
the revised policy. Historical findings remain historical evidence, not the
current expected results. This Phase 2 adds no weakening of those assertions.
The 308 corpus rows are observations, distinct from the 125 unittest methods.

## 7. Remaining non-normative differences

The interop suite still explicitly tests and records these differences:

| Input | Reference | Clean-room | Why outside N1–N11 |
|---|---|---|---|
| Duplicate JSON keys in HTTP PUSH envelope | Last records key wins; HTTP 200 and record admitted. | HTTP 400; nothing admitted. | N2 fixes item descriptors and error tiers, not duplicate-key parsing of the outer HTTP envelope. Carrier JSON duplicate-key rejection is separate. |
| Unknown PULL query member | HTTP 200; member ignored, normal empty page on empty store. | HTTP 400 with kind=request, reason=query-fields. | The revision fixes ranges/limits/tokens; it does not standardize rejection of unknown query members. |
| Empty PUSH records array | HTTP 400, {"error":"push batch size"}. | HTTP 200, {"results":[]}. | Revision specifies maximum batch size and error tiers, not minimum batch cardinality. V5 records this without a normative assertion. |
| Request error envelope and exception text | E.g. wrong address: {"error":"address mismatch"}. | Same 400, {"kind":"request","reason":"address-mismatch"}. | Status/admission tier is normative; message text and exception class are implementation-defined. |

Reference and clean-room also have different local APIs: reference pull owns its
checkpoint; clean-room pull is one-page and _pull_from owns catch-up checkpoints.
This is a tooling distinction, not a wire divergence. The V8 adapter explicitly
accounts for it. No additional normative divergence was observed in this run.

## 8. Limitations

- Loopback only; no WAN or two-host run. The historical single-host constrained
  container run was not repeated in Phase 2, nor was the separate scale matrix.
- Finite generated corpus; agreement of two implementations is not a proof that
  either is universally correct. Shared RPC plumbing is reused, not reimplemented.
- Stores are in memory; no durability/crash-recovery guarantee or production budget.
- No global completeness or freshness; withholding and partitions remain possible.
- No peer authentication, TLS or rate limits in these experiments.
- No deletion/compaction/retention agreement.
- No proof of real-world location, time or identity; signatures establish key control.
- The spatial altitude mapping remains the proposal's provisional profile. Passing
  V4 pins this profile's behavior, not a claim that its real-world interpretation
  has received final product approval.

## 9. Recommendation and Founder decision

Recommendation: **freeze candidate**. No new protocol defect was exposed by the
required vectors or suites. Founder approval must explicitly choose the exact
specification/implementation/vector commits, accept the N1–N11 resolutions and
provisional spatial profile, and decide whether the documented non-normative
HTTP parsing/batch differences can remain unspecified for the freeze. If they
must be standardized, authorize a separate focused contract revision with tests.
Approval must also acknowledge the limitations above. This recommendation grants
no merge, release, deployment or freeze authorization by itself.

## 10. Reproduction

Run from the repository root with the existing Python environment (stdlib plus
already-installed cryptography; no new dependency):

```sh
PYTHONPATH="$PWD/experimental/punkti-v0.6-mesh/src" python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
PYTHONPATH="$PWD/experimental/nairobidot-l3/src" python3 -m unittest discover -s experimental/nairobidot-l3/tests
(cd experimental/nairobidot-l3/interop && python3 -m unittest discover -s .)
PYTHONPATH="$PWD/experimental/punkti-v0.6-hostile/src" python3 -m unittest discover -s experimental/punkti-v0.6-hostile/tests
PYTHONPATH="$PWD/experimental/punkti-v0.6-freeze/src" python3 -m unittest discover -s experimental/punkti-v0.6-freeze/tests
python3 experimental/punkti-v0.6-freeze/src/make_vectors.py
git diff --check
```

The interop/hostile suites rewrite their evidence artifacts. Timing/request-count
noise can change network evidence without changing conformance outcomes; review
those separately from the deterministic freeze artifacts. All new normative
inputs, results and transitions are published in the two generated artifacts.

Phase 2 run network captures were preserved in a local scratch directory before
restoring their tracked Phase 1 versions; their volatile ports, epochs, timings
and partition scheduling were not added to the two focused Phase 2 commits.
The deterministic protocol evidence was identical to the committed Phase 1 file.
