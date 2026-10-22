# Codex Task — Punkti Mesh: generic discovery, sync and anti-entropy

Status: **ACTIVE — implement on this branch only. Do NOT merge to main. Do NOT deploy.**

## Task one-liner

Build an application-agnostic Punkti peer-discovery, replication and reconciliation
layer (a.k.a. the "Mesh") as a self-contained reference implementation **plus** a
concise wire/sync specification, on this isolated branch
`proposal/punkti-0.6-mesh` of `Fisker1111/Punkto`, exactly matching the approved
`docs/proposals/PUNKTI_0_6_LAYER3_RESET.md` contract that is already baselined in
this branch.

## Repository / layout (already prepared)

- Branch: `proposal/punkti-0.6-mesh` (isolated; upstream unset; based on `origin/main`).
- `docs/proposals/PUNKTI_0_6_LAYER3_RESET.md` — the **authoritative, founder-approved** L3
  carrier contract. Build the Mesh directly on this; do not invent a competing envelope.
- Create the Mesh under `experimental/punkti-v0.6-mesh/` (mirrors the existing
  `experimental/punkti-v0.6-first-identity/` convention).
- Write the wire/sync spec at `docs/proposals/PUNKTI_0_6_MESH.md`.

## Non-negotiable constraints (from the task gate)

1. **Codex performs all repository/code work.** You write the code and tests. You must
   NOT push to main, merge, deploy, or touch `pwa/`, `relay/` (except adding a
   self-contained test that does not break existing relay code), `deploy/`, or any
   production path. Isolated branch/test environment only.
2. **No central coordinator, no mandatory origin server.** Bootstrap may use configured
   peers; continued operation must not depend on Punkto the app.
3. **Unknown Layer-4 atom types are preserved and replicated byte-for-byte** with zero
   semantic interpretation.
4. **Invalid/corrupt atoms must never become valid through replication.** A receiver
   verifies locally per the L3 validation-state table; it must never trust a peer's
   validity claim as verification evidence.
5. **Separate atom validity/provenance from transport security and from semantic trust.**
6. Keep simple **PUSH + HTTP Range PULL**. The task says to add a transport-independent
   *missing-set reconciliation* mechanism **only if justified by measurement** — so
   implement PUSH + Range PULL, make the convergence measurement, and let the result
   decide (see Measurement below). Do not build unmeasured reconciliation bloat.

## Atom model (pin these exactly — do not redefine)

Use the L3 envelope from the reset spec: fields `v, t, h, x, alg, pk, refs, ext, sig`
with the exact canonical bytes `C`, MID, signing input `S`, transfer record `R`, and
the six validation states.
- Known profile: `alg = "ed25519"`, `pk` = 32-byte raw public key, `sig` = 64-byte
  Ed25519 over `S` (standard, not prehash). Use the `cryptography` Python library for
  real keygen/sign/verify (already installed, v50.0.1). Keygen must be **seeded and
  deterministic** in tests (see Determinism).
- The MID excludes the signature. Full address is `punkti/0.6:<mid>`.
- Validation states: `VALID`, `UNVERIFIABLE-alg`, `INVALID-structural`,
  `INVALID-provenance`, `UNVERIFIABLE-key` (legacy-only, not needed for v0.6 Mesh),
  `OPAQUE-version`. Only `VALID` atoms enter the main store.

## Spatial subscription — first-class (founder refinement — MUST build this)

Spatial subscriptions are native Mesh behavior, not a Punkto filter.

- A node declares a spatial range it wants to hold/query/reconcile. Support the
  semantic equivalent of `SUBSCRIBE h=gggh..gggi FROM <cursor>`.
- A spatial range selects atoms **by `h`** (the L3 geohash), independently of the
  opaque `x`. Range-scoped sync must work **without inspecting `x` or knowing any
  Layer-4 protocol**.
- Support an optional contiguous `h` interval `[lo, hi)` over the geohash alphabet,
  plus **optional Z/elevation constraints where applicable** (a `z_min..z_max`
  interval in metres, applied to the atom's encoded altitude). A subscription is the
  tuple `(h_lo, h_hi, z_min_opt, z_max_opt, cursor_opt)`.
- `FROM <cursor>` = resume catch-up from a point in a subscription's history
  (monotonic local sequence / high-water mark per subscription), so a space can be
  re-subscribed after disconnects without full re-scan.
- Range matching must be computed from the **addressed** `h` (and decoded altitude)
  alone — never from `x`.

## Sync = PUSH + HTTP Range PULL (+ conditional reconciliation)

- **PUSH:** a peer sends one or more verified-candidate atoms (or the `R` record bytes)
  to a peer; the receiver locally validates and admits `VALID` atoms, dedups by MID,
  rejects/quarantines the rest.
- **HTTP Range PULL:** a peer requests atoms over a range — MUST support both
  (a) a spatial range (subscription-driven: `h` interval [+ z interval]) and
  (b) an opaque MID lexicographic range (for catch-up / full sweep). Requests carry a
  cursor and a page size; responses return records + the next cursor + an end marker.
  Use real `http.server`/`urllib` in tests so it is an actual HTTP exchange (loopback),
  not a mocked function call — this is what makes the tests a genuine wire test.
- **PUSH direction on connect:** on peer (re)connect, immediately push each side's
  newly-admitted atoms relevant to the advertised subscriptions, then Range PULL to
  converge. No timestamps define reconciliation order.
- **Missing-set reconciliation (conditional):** produce a measurement (see below). If
  PUSH + Range PULL provably converges in the required scenarios, you MAY keep
  reconciliation as a clearly-marked optional/off capability with the measurement as
  justification, or omit it and document why. Do NOT ship it unless measured.

## Determinism / testability

- All crypto keygen in tests uses a fixed seed → deterministic keys, signatures, MIDs.
- Three independently-initialized nodes (in-process, each with its own store + its
  own loopback HTTP server on distinct ports) — no shared mutable state.
- Tests are runnable with the standard library test runner:
  `python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests -v`
  (stdlib only plus `cryptography`).
- A `requirements-test.txt` listing `cryptography` is acceptable.

## Required acceptance tests (from the task — all must pass)

Three independently-initialized nodes A/B/C:

1. **Differing subsets** — each node starts with a different subset/order of valid
   atoms. After connect, all three converge to the **same set of valid atoms**.
2. **Discover/reconcile missing valid atoms** — peers exchange and all end with the
   union of their valid atoms (deduped by MID).
3. **Invalid never becomes valid** — a structurally-corrupt atom and a
   forged-signature atom are introduced via replication; they are rejected and never
   become `VALID` on any node.
4. **Unknown atom byte-for-byte** — an atom of an unknown/future Layer-4 type (opaque
   `x`) is replicated and stored, and its canonical record bytes (`R`) are identical
   at both source and destination (compare raw bytes, not re-serialization).
5. **Offline / return** — node C goes offline while A and B keep exchanging; when C
   returns (same configured peers + subscriptions), convergence resumes and all three
   re-converge.
6. **Wire spec exists** — a concise `docs/proposals/PUNKTI_0_6_MESH.md`.

Spatial-subscription acceptance tests (the founder refinement — all must pass):

7. **Single-range node** — a node subscribes to one spatial range; it converges only
   for atoms whose `h` falls in range and carries them.
8. **Overlapping subscriptions** — two nodes with overlapping ranges both converge on
   the intersection without either gaining atoms outside its own declared ranges.
9. **Out-of-range not required** — convergence inside a subscribed range does not
   require (and is not blocked by) atoms outside the range.
10. **Z/elevation constraint** — a subscription with a `z` interval accepts atoms in
    the altitude band and excludes those outside it, selected purely by address.
11. **Catch-up same spatial scope** — after a disconnect, a node re-subscribes the
    same range and catches up on the atoms it missed (uses `FROM <cursor>`).
12. **Unknown L4 in-range** — an unknown Layer-4 atom is replicated *solely* because
    its `h` falls inside a subscribed range, even though `x` is never inspected.

## Measurement (drive the reconciliation decision)

Add `experimental/punkti-v0.6-mesh/docs/measurement.md` reporting:
- scenario: 3 nodes, different subsets (varied size), how many PUSH/Range-PULL rounds
  until convergence, and whether atomic (single-pass) or sweep needed;
- a larger-set / churn scenario (e.g. inserts behind a cursor) noting the L3 sweep-caveat;
- an explicit verdict: does PUSH + HTTP Range PULL suffice for the task's convergence,
  or is missing-set reconciliation justified? Cite the numbers.

## Cross-platform / portability note

Do **not** hard-depend on `relay/` or `core/punkto.py` internals — the Mesh must be
usable by Punkto, NairobiDot and unknown future apps alike. If you import the L3 state
machine, keep it a generic self-contained module inside the experiment (you may vendor
a minimal copy of the canonical-bytes/validate logic rather than couple to the PWA).

## Deliverables (in this branch)

- `experimental/punkti-v0.6-mesh/src/…` — Mesh reference implementation (Python).
- `experimental/punkti-v0.6-mesh/tests/…` — the deterministic test suite (all of the
  above acceptance tests).
- `experimental/punkti-v0.6-mesh/docs/measurement.md` — convergence measurement +
  reconciliation justification.
- `experimental/punkti-v0.6-mesh/README.md` — how to run tests, architecture sketch.
- `docs/proposals/PUNKTI_0_6_MESH.md` — the concise wire/sync specification.
- Commit your work on `proposal/punkti-0.6-mesh` in small, focused commits. Report the
  exact final SHA.

## Stop condition

Stop after all tests pass via `python3 -m unittest discover ... -v`, the measurement is
written, and work is committed on the branch. Report: exact SHA, files changed, tests
and their pass counts, the measurement verdict, and any deviations from this brief.
Do not deploy and do not open a PR to main.