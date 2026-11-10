# CODEX_TASK_57 — Punkti two-node parity: static-first bidirectional replication, regression harness, operator runbook

> **Addendum (2026-11-10, answering Codex's first stop-and-report):**
> 1. "No network" in section D means **no external network**. Loopback-only HTTP
>    (`127.0.0.1`, ephemeral ports) is explicitly allowed and required by test
>    case 4. No DNS other than localhost, no internet, no production host.
> 2. `docs/agent/CODEX_CURRENT_TASK.md` is **superseded by this file** for this
>    run: its `Status: HOLD` applies to the unrelated visual-polish task. This
>    task (CEO-OS #57) is the active, authorized task. Do not stop because of
>    that file.
> 3. Do not commit and do not push (unchanged).

Source of truth: CEO-OS issue #57 (Fisker1111/CEO-OS#57).
Base branch: `main` (86fcb43b0c50224a87414e7f38734b6cae536f53).
This is a **review-only** PR. Do not merge. Do not deploy. Do not touch `origin/main`.

## Goal

Make two independently operated Punkti v0.6 nodes into **equal first-class peers**:

1. Each node owns its own durable store, signs/validates independently, and publishes
   its own static `punkti/pub/0.6` publication.
2. Each node can **ingest from the other** through two independent paths:
   - the existing live Mesh protocol (`/hello`, `/pull`, `/push`, `/sync`), and
   - the **static-first** path: read the peer's *published* objects over plain
     `GET` (`root.json` → `manifests/<head>.json` → `h/...` → `records/...`),
     verify every object independently, and republish locally.
3. The static-first path must work **while the peer's application daemon is stopped**
   (only a plain static file server for the publication directory is running).
   This is the missing capability today: `PersistentNode.replicate_publication()`
   exists but is **never called by the runtime** (`punkti_node/runtime.py` only
   calls `node.sync_known()`, which needs the peer's live daemon), and the
   publication is served by the node's own HTTP server, so there is no separate
   static origin.
4. A repeatable, hermetic **regression harness** proves the parity properties.
5. An **operator runbook** lets a human reproduce the proofs and bring node2 to
   peer parity without changing production.

## Non-negotiable protocol rules (do not redesign)

- Signed carrier, `punkti/0.6`, spatial-only `XY_Z`. `xy_z` is exact.
- **No unanchored atoms.** No legacy `punkti/0.5.1` adapter.
- Verification is always independent and local: the receiver validates
  `sha256`, the manifest/shard metadata and the carrier signature itself
  (`carrier.validate`). Never trust a peer-declared state, head or count.
- A peer-declared `head`/`seq` difference is **not** by itself a correctness
  divergence. Correctness = the union of *admitted, verified* records converges.
- Publication objects are immutable and content-addressed (`sha256`).
- `h`/spatial scope, `xy_lo`/`xy_hi`, `z_min`/`z_max` semantics stay as-is.
- Do not add a central registry, a leader, a database or any new dependency.
- Do not change the carrier, the store format, the publication profile
  (`punkti/pub/0.6`), or the Mesh wire protocol.

## Scope of code changes (minimal, additive)

### A. `punkti_node/config.py`
Add one new optional configuration section, e.g.

```yaml
replication:
  # Absolute http(s) base URLs of PEER PUBLICATION ROOTS (the directory that
  # contains root.json), e.g. "https://test2.punkto.xyz/publication".
  # Each node lists the other node's publication root here; the node then
  # performs static-first replication from that origin.
  static_peers: []
```

Requirements:
- Unknown sections are currently a hard error, so the new section must be added
  to `DEFAULTS` with validation (list of absolute `http(s)` URLs, no trailing
  slash, no credentials, no query/fragment) and an env override
  (`PUNKTO_STATIC_PEERS`, comma-separated) consistent with the existing style.
- Default `[]` = **zero behaviour change** for every existing deployment.

### B. `punkti_node/store.py`
- `PersistentNode.replicate_publication(peer_base)` exists but is unused and
  shares one `Reader`/store across peers while clearing it before each read.
  Make static-first replication safe for **multiple** peers (per-peer reader or
  equivalent), keep it idempotent, and keep every record locally verified.
- Do **not** change `Publisher`, the publication profile or the object layout.

### C. `punkti_node/runtime.py`
- In the sync loop, for every configured `replication.static_peers` entry, perform
  static-first replication from that publication root, independently of the live
  Mesh sync. Failures must be logged and must never kill the node or the loop.
- After a successful import the node republishes locally (so a third node can
  learn the union transitively) — reuse the existing `after_sync()` /
  `flush_publication()` path.
- Mesh sync behaviour must stay exactly as it is today.

### D. Hermetic regression harness — new file `punkti_node/test_two_node_parity.py`
Two nodes in-process, **temporary data dirs only**, **no production data**, no
external services.

**Networking rule (clarification):** the harness may use **loopback-only HTTP**
(`127.0.0.1` / `localhost`, ephemeral ports, e.g. the plain `http.server` static
origin required by test case 4 and the node's own HTTP server). **No external
network access is permitted**: no DNS beyond localhost, no internet, no
production host, no proxy. Anything that is not loopback is a test failure.

Use the existing test conventions of the
repo (`punkti_node/test_node.py`, `punkti_node/test_publication.py`):
`unittest`, `tempfile.TemporaryDirectory`, `sys.path` bootstrap as in the existing
tests, and the existing signing fixtures in
`experimental/punkti-v0.6-mesh/tests/support.py`.

Required test cases (each must be a separate, named test):

1. `test_bidirectional_signed_atom_replication`
   Signed atom A submitted to node 1 → node 2 imports it, verifies it, republishes
   it; and signed atom B submitted to node 2 → node 1 imports it, verifies it,
   republishes it. Assert equal `sha256` and equal MID (`address`) on both sides.
2. `test_union_convergence`
   Node 1 holds `{A,B,C,D}`, node 2 holds `{C,D,E,F}` (use the shared fixture
   generator so both sides are reproducible). After replication both nodes must
   hold the union `{A,B,C,D,E,F}` and no other record. Assert the union by
   (MID, sha256) sets, not by counts alone.
3. `test_repeated_sync_is_idempotent`
   Run the sync cycle repeatedly; the record set, the local store and the
   published objects must not grow or change (byte-identical publication root
   and manifests after the first convergence).
4. `test_static_replication_survives_source_daemon_stop`
   Node 1 publishes; node 1's **application daemon is stopped** while the
   publication directory is still served by a plain `http.server` (a static
   origin, not the node). Node 2 must still import and republish. This is the
   core "static-first" proof — it must fail without the change in C.
5. `test_peer_unavailable_then_restore_converges`
   One side is unreachable for a while, then becomes reachable again; both sides
   converge to the union afterwards.
6. `test_invalid_signature_same_mid_is_rejected`
   A record that reuses a valid MID but has a broken signature (and a variant
   with a wrong digest) must be rejected, not admitted, and must not change the
   published head.
7. `test_publication_race_and_stale_head_are_safe`
   A publication whose `root.json` changes between the root read and the manifest
   read (publication race) and a root whose `seq` goes backwards (stale root) must
   be rejected/retried safely — never partially applied, never a corrupt local
   publication.
8. `test_mixed_spatial_scopes_and_exact_z`
   Reproduce with mixed `h` values, exact `z` boundaries and the spatial-only
   `XY_Z` subscription bounds: records outside the subscription must not be
   admitted; records on the boundary must be.
9. `test_publication_content_addressed_objects_unchanged`
   The published object layout (`root.json`, `manifests/<sha>.json`,
   `h/<...>/<sha>.json`, `records/<xx>/<sha>`) and the `punkti/pub/0.6` profile
   are unchanged by this work (guard against accidental format drift).

### E. Operator runbook — new file `docs/operator/two-node-parity-runbook.md`
Operator-facing (not founder-narrative). Must contain, as copy-pasteable,
reproducible commands:

- How to start the hermetic two-node proof on a host with Python 3.12+ and
  `cryptography`/`PyYAML` installed (the exact `python3 -m unittest` invocation
  and what a green run prints).
- How to stand up two **isolated** nodes on a server with separate temporary data
  roots, separate test keys and loopback-only ports, and how to stop them
  (no systemd unit, no production port, no DNS change).
- How to serve a node's publication directory as a **static-only** origin and
  point the other node's `replication.static_peers` at it.
- The exact read-only checks an operator runs against the two real nodes
  (published root/manifest fetch, record comparison, `/hello` peer/epoch
  inspection) — all `GET`, no writes.
- The legacy `/opt/punkti/sync.sh` StarNode cron: state plainly that it is
  **obsolete** (2026-04 `log.ndjson` design, unanchored rows, not the v0.6 signed
  store), that it fails today (`www.punkti.net` → TLS failure → HTTP 000 on node2;
  `www.sunebech.com` → HTTP 302 on node1), that it does **not** feed the v0.6
  store, and that it must not be mistaken for replication. Do **not** instruct
  anyone to disable it in this PR — describe it and flag it for founder
  approval.
- Explicit statement of what is **not** covered: no DNS/HA change, no apex
  cutover, no production write, no new production replication job.

### F. CI
Add the new harness to the existing Python job in `.github/workflows/pilot-ci.yml`
so it runs on the exact pushed SHA. Follow the existing job style; do not add new
secrets or new services.

## Constraints / guardrails

- Do **not** merge, do **not** push to `main`, do **not** deploy, do **not** touch
  any production host, DNS, TLS or Caddy config.
- No new runtime dependency: stdlib + `cryptography` + `PyYAML` only (that is what
  `node/requirements.txt` already declares).
- Do not weaken any existing test; the whole existing suite must stay green.
- Keep the diff small and focused: one new config section, one runtime hook, one
  new test module, one runbook, one CI line. No refactors, no renames.
- Follow `AGENTS.md`. Run at least:
  ```
  python3 -m unittest punkti_node.test_node -v
  python3 -m unittest punkti_node.test_publication -v
  python3 -m unittest punkti_node.test_write_safety -v
  python3 -m unittest punkti_node.test_two_node_parity -v
  python3 -m unittest discover -s punkti_node -p 'test_*.py' -v
  ```

## Stop condition

- Implement, run the tests, and report: files changed, exact commands run, and
  the test results.
- **Do not commit and do not push.** Hermes commits and pushes from its own
  shell (a linked worktree's git dir is not writable from inside the sandbox).
- If the spec is contradictory or the required proof cannot be built as
  specified, **stop and report the concrete contradiction** instead of guessing.
