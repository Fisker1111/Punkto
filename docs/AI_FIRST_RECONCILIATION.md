# Spatial-only integration plan — no merges or deployments performed

Stage 0 imports the existing frozen implementations; it does not re-freeze them.
It enforces explicit spatial writes at its own entrance. #30 owns the full removal
of empty h and the legacy publication bucket. One integrator should land accepted
#30 first, reconcile #124/#125 next, then reconcile #127's copy/tests and promote
the Stage-0 entrance only after checks. No PR is merged, rebased onto, cherry-picked
or deployed by this task. #32 remains backlog pending #30 and #31 acceptance.

## PR #124: exact replacement wording

Reviewed the actual `origin/review-124:docs/AI_READ_BLOCK.md` via a read-only fetch.
Every pre-correction sentence in that file needing spatial-only replacement:

| Existing text | Exact replacement |
|---|---|
| `never guess Z. h="": unanchored, separate ~ index, not ground.` | `Never guess Z. Every v0.6 atom requires an explicit canonical h=XY_Z; an empty h is invalid and there is no nonspatial publication bucket.` |
| `The ~ index directly names an unanchored leaf.` | `The manifest index contains geographic XY prefixes only; follow each selected branch to its geographic leaf.` |

The brief also calls out the statement that unrestricted scope selects a hidden
global bucket. That sentence is **not present in the fetched #124 READ block**;
do not invent a quotation. If retained in another integration draft, replace it
with exactly: `Unrestricted scope traverses all published geographic branches;
it selects no hidden global bucket and makes no global completeness claim.`

Keep the existing warnings about bytes versus authorship, exact-h distinction,
non-normative paths, optional reader/packs, and independent verification. Recount
the prose word count after replacement. Keep ellipsoidal Z separate from AGL;
never introduce ground-elevation lookup into the Stage-0 client.

#124's companion evidence contains the old fifth/empty-h fixture and `h/~/`
requests. Preserve it as explicitly historical evidence, not new conformance.
Regenerate spatial-only evidence and remove empty-h support from its future
walkthrough tools after #30; do not silently relabel the old hashes as current.

## PR #125: derived navigation only

The optional static GeoHash density index must have **no unanchored terminal**
after #30. Replace `Unanchored records are listed separately.` in its READ
introduction with `Every listed record has an explicit canonical XY_Z address.`
Remove corresponding generator/client branches and obsolete fixtures/assertions
at integration; regenerate counts and evidence from anchored-only records.
Occupied-branch counts must equal traversed leaf-entry counts, including padded
short XY addresses and distinct heights; GET-only fallback to the frozen
publication must still work when the optional index is missing, stale or corrupt.
Test those cases before calling the prototype current.

This index is a derived **Layer-4 artifact**. Its navigation/counts do not change
the frozen Layer-3 manifest/shard/record contract, add atom types or authenticate
payloads. Stage 0 does not depend on it, add an index endpoint, or edit its branch.

## File overlap map for the integrator

This map is based on `git diff --name-only origin/main...origin/review-124`,
`...origin/review-125`, and `...origin/wip/v0.6-spatial-only-correction`.

| Files | Ownership / integration concern |
|---|---|
| `docs/AI_READ_BLOCK.md` | #124 addition; no literal #30 file overlap, but semantic empty-h/~ correction required. Stage 0 uses its own walkthrough. |
| `docs/evidence/issue-27/tools/ai-read-walkthrough.py`, `make-ai-read-fixture.py`, `docs/evidence/issue-27/walkthrough-summary.md`, `walkthrough-transcript.txt` | #124 evidence additions, no literal #30 overlap; regenerate spatial-only evidence rather than treating historical nonspatial fixtures as current. |
| `.github/workflows/pilot-ci.yml`, `docs/CODEX_TASK_28.md`, `docs/CODEX_TASK_28b.md` | #125-owned CI/task changes; no literal #30 overlap in inspected diff. Stage 0 touches none of them and adds no CI job. |
| `docs/DISCOVERY_AI_READ.md`, `docs/proposals/PUNKTO_DISCOVERY_INDEX_V1.md` | #125 additions, no literal #30 overlap; correct nonspatial narrative and terminal contract. |
| `experimental/punktto-discovery-index/**` | #125 prototype, vectors/tests/evidence; no literal #30 paths overlap in inspected diff, but all `experimental/**` is reserved during Stage 0. Remove nonspatial terminal and regenerate tests/evidence after #30. |
| `punkti_node/config.py`, `punkti_node/store.py` | #125 runtime integration; no literal #30 overlap in inspected diff. Reconcile against #30's carrier/publication/spatial dependencies. Stage 0 never edits these. |
| `pwa/punkti/{carrier,reader,spatial}.js`, `punkti_node/{carrier,publication,spatial}.py`, vectors and consumers | #30 owns semantic changes; #124 tools and #125 generator depend on them. Stage 0 imports them unchanged. |
| `docs/proposals/PUNKTI_0_6_{LAYER3_RESET,MESH,PUBLICATION,SPATIAL_XY_Z,STATIC_PUBLICATION,VECTORS}.md`, `docs/evidence/issue-30/archive-digests.json`, legacy archives | Additional #30 paths discovered in the remote diff; all left untouched. |

There is no literal #124/#125/#30 file intersection in these inspected snapshots;
there are significant semantic/dependency overlaps. Keep one integrator and rerun
this map if branch heads move. Stage 0's only existing-file edits are README,
CONTRIBUTING and the expressly permitted launch checklist.

## PR #127: file-by-file decision

Task brief identifies draft head `bcad9b4601607cf90e4212a1a2f2354cf0ccc42b`.
No merge, rebase or cherry-pick of #127 was performed.

| File | Version that should win and why |
|---|---|
| `pwa/ai.html` | #127 copy wins for narrative **only after #30 lands**. Preserve #30's spatial-only behavior/examples when reconciling. This file is in #30's change set; Stage-0 `pwa/ai-first/index.html` is the interim entrance. |
| `pwa/test-ai-hostile.mjs` | #127 version wins for the newer hostile-suite copy expectations, integrated with #30's mandatory-spatial checks. Do not discard either set of constraints. |
| `scripts/qa/tests/test_ai_entrance_copy.py` | #127 version wins as-is: additive copy conformance, no Stage-0 conflict. |
| `.github/workflows/ai-first-copy.yml` | #127 version wins as-is: additive gating of that test, no Stage-0 conflict. Stage 0 creates no second workflow. |

The interim entrance carries Explore / harvest, Publish / discuss, Store / serve,
Replicate / preserve as voluntary, overlapping, interoperable activities, not
Layer-3 atom types or required capabilities. Reading needs no SDK/account;
signing and the participation roles are not required for reading. Its in-suite
`pwa/ai-first/copy-conformance` check fetches the page over real local HTTP.
Punkti stays open/universal/CC0/provider-neutral; Punkto is one competing
commercial managed-service provider, without pay-to-own addresses, closed
Layer-3 features or artificial captivity. No eternal-persistence claim is made.
