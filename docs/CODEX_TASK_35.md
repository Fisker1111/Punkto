# CODEX_TASK_35 — Republish the static publication after mesh replication

**Task:** CEO-OS Issue #35 (Punkto controlled public AI publishing) — operator gate blocker.
**Repo:** `Fisker1111/Punkto`, base `main` at `febe78f62b335c05b23d3e4ca551d8abebf9bc44`.
**Branch:** `fix/publication-refresh-on-replication`
**Do not commit. Do not push. Do not open a PR. Do not change any CI workflow.**

## Why this task exists (observed live defect, not a theory)

During the CEO-OS #35 canary on `test2.punkto.xyz` (node2), a signed atom was published
through `POST /submit` and replicated to the production node `punkto.xyz` (node1) over the
normal mesh path. Observed on the live hosts:

- node1 `/data/atoms.jsonl` contained **6** valid records (4 pre-existing + the 2 replicated
  canary atoms).
- node1 `/data/publication/records/**` contained only **4** record objects, and
  `https://punkto.xyz/publication/root.json` still reported `seq 4`
  (head `c97d3d9144fb49fe7e094db16c6f5cf97a0cc9d240431ae8e664e9eeb58cc585`).
- `GET https://punkto.xyz/publication/records/<sha256 of the replicated atom>` returned **404**,
  while the identical atom was served **200** from `https://test2.punkto.xyz/publication/records/<same sha256>`.
- The canary harness case `peer_replication` failed exactly this way (6 attempts, all 404).

This breaks Issue #35 acceptance criteria: *"static publication byte-identical R on both
origins"* and *"one valid MID+h+SHA256 served from both nodes"*. A record published on node1 and
replicated to node2 is likewise never served from node2's static publication, so a receiving
node can never serve a record it has replicated — only a restart makes it appear.

## Root cause (already diagnosed — verify, do not redesign)

- `punkti_node/store.py` — `PersistentNode` inherits `admit()` from `punkti_node/mesh.py`
  (`Node.admit`). `admit()` appends to the in-memory store and calls `persisted()`, which
  appends to the durable log. **It never calls `republish_publication()`.**
- `republish_publication()` has exactly three callers in the tree:
  1. `PersistentNode.__init__` (so every node republishes on **restart** — which is why this
     defect has been masked until now);
  2. `PersistentNode.submit_records()` (the local `/submit` path); and
  3. `PersistentNode.replicate_publication()` — a static-publication *reader* helper whose only
     caller in the whole repository is `punkti_node/test_publication.py`. It is **not** wired
     into the live mesh replication path.
- Therefore, in production, records that arrive by replication stay invisible on the static
  publication until the next process restart. The `replicate_publication()` helper does not
  change this: it is a different (static-publication) mechanism and is not invoked at runtime.

## Required fix (provider/publication behaviour only — NOT a protocol change)

Make the static publication reflect records admitted through **any** path, including mesh
replication. Do not change the carrier, the wire format, the record validator, the spatial
model, the MID/hash rules, the peer protocol routes, the publication file format, the
manifest/root format, or the admission guard.

Concretely, in `punkti_node/store.py` (`PersistentNode`):

1. Initialise a dirty flag (e.g. `self._publication_dirty = False`) in `__init__`, before the
   first `republish_publication()` call.
2. Override `admit(self, item)` in `PersistentNode`: call `super().admit(item)`, and when the
   result reports `admitted` is truthy and `self.publication` is not None, set the dirty flag.
   Return the super result unchanged otherwise. Do not alter the returned dict.
3. Make `republish_publication()` itself clear the dirty flag when it successfully publishes.
   That keeps the flag consistent at every one of its three call sites (`__init__`,
   `submit_records`, `replicate_publication`) without each call site having to remember it.
4. Add a `flush_publication(self)` method that, when the dirty flag is set and the publication
   is enabled, performs exactly one `republish_publication()`; otherwise it is a no-op. It must
   be safe to call concurrently — take `self.lock` (it is an `RLock`) and let
   `republish_publication()` set `self.publication_state`, exactly as it does today.
   The dirty flag exists precisely so that a node with no new records does **not** republish on
   every sync cycle.
5. Call `flush_publication()` from `PersistentNode.after_sync()` — `after_sync()` is already
   invoked at the end of a completed mesh pull (`Node.pull`) and at the end of `Node.push_to()`.
   This covers the `/pull` replication path.
6. In `punkti_node/mesh.py`, the `POST /push` handler admits records with `node.admit(item)`
   and never reaches `after_sync()`. After that admit loop, call the flush exactly once if the
   node exposes it, e.g.
   `flush = getattr(node, 'flush_publication', None); flush() if flush else None`.
   This covers the `/push` replication path. Keep the `/push` response shape unchanged.

### Constraints

- `flush_publication()` must not change the node epoch, the durable log, `cursors.json`, the
  record set, the store contents, or the admission guard behaviour.
- `republish_publication()` must remain the only writer of the publication tree, and the
  existing `Publisher.publish()` semantics (atomic publish, head/seq derivation) must not change.
- A failed publish (e.g. `OSError`) must not corrupt the store or the durable log. It is
  acceptable for the exception to propagate as it does today from `submit_records`; do not
  silently swallow errors, and do not add retry loops.
- Do not add timers, background threads, or scheduled tasks. The flush must be triggered by
  the replication events themselves.
- Do not make `after_sync()` republish unconditionally — only when new records were admitted.
- No new dependencies. No changes to `node/requirements.txt`.

## Required regression test

Add a test to the existing test suite (place it in `punkti_node/test_publication.py` unless a
more appropriate existing module is clearly better — read the file first and follow its
conventions) that proves the defect is fixed and would have failed before the fix:

- Start node A and node B (follow the existing two-node test helpers in that file).
- Publish one valid signed atom on A through the normal submit path.
- Replicate it to B over the mesh path (use the existing replication helper — inspect
  `punkti_node/test_publication.py` and `punkti_node/mesh.py` for how the existing tests move a
  record between two nodes; do not invent a new transport).
- Assert that **B's static publication now serves that record** (B's publication reader or
  publication tree contains the record / the record is fetchable at B's publication path) —
  **without restarting B**.
- Also assert the record is not published twice / the publication stays consistent (e.g. the
  record appears exactly once and the publication's record count and root `seq`/`head` are
  self-consistent).
- Keep the test deterministic and fast; it must not sleep for long.

## Test commands (these are the ones CI actually uses — verified against the workflow files)

Run **all** of these, from the repository root, and report each result:

1. `python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication`
   (this is the node test command in `.github/workflows/punkto-image.yml`)
2. `python3 -m unittest punkti_node.test_write_safety`
3. `python3 -m unittest punkti_node.test_spatial_only -v`
   (this is the independent spatial conformance command in
   `.github/workflows/punkti-spatial-conformance.yml`)

If the local Python cannot import `cryptography` / `yaml`, say so explicitly and report which
suites you could and could not run — do not claim a suite passed that you did not run.

## Definition of done

- The regression test exists, **fails on the unfixed code and passes with the fix** (report
  both results explicitly, e.g. by temporarily reverting the fix and running the test again).
- The test suites above pass.
- `git diff` shows changes limited to `punkti_node/store.py`, `punkti_node/mesh.py` and the
  test file (plus this brief file itself).
- You did NOT commit and did NOT push.

## Report back

State: the files changed, the exact test command(s) run with pass/fail counts, the
before/after evidence for the regression test, and any deviation from this brief. If you find
that this brief is technically wrong or contradictory with the code, STOP and report the
counterexample instead of guessing.
