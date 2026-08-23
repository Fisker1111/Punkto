# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5A: deploy spatial reading to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed Pilot_1 **Slice 4.5A — Spatial Reading** implementation to **test1 only** and verify the new spatial grammar in the live PWA while preserving the existing independent test1 relay/federation topology and its real `Test atom`.

This is deployment/verification only. Do not edit Punkto product/application code.

## Exact approved application SHA

Deploy exactly:

`cc687e509b7949c23b2410e930e971c0aa361c59`

Commit:

`feat(pilot1): add spatial atom reading`

Pilot CI run `32648441562` / run #58 is green for this exact SHA.

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy the PWA tree from the exact SHA above.

Expected version marker:

`pilot1-slice45a-spatial-reading-2026-08-23-1`

## Product behavior under test

Slice 4.5A introduces the first Punkto spatial-reading grammar for existing atoms:

- beacon = the real message position in space;
- ground anchor = the exact geographic ground position;
- elevated atoms can show a vertical stem connecting ground anchor to beacon;
- ground-level atoms collapse visually into a compact beacon/base treatment;
- far view stays calm; ground relation appears at closer zoom; stems become visible at near zoom;
- selected atoms always receive the strongest ground/stem/beacon treatment and a compact height label such as `+12 m · ~Floor 4`;
- selected-board desktop treatment becomes a narrower spatial sidecar rather than a large floating modal;
- opening the board adjusts MapLibre viewport padding so the world makes room for the board while preserving zoom/pitch/bearing;
- mobile remains a contained bottom sheet with map context still visible.

No direct-manipulation height drag is part of this task. No building translucency/floor slicing is part of this task. Those belong to later Slice 4.5 steps.

## Preserve current test1 state

Do not alter the Slice 3.5 federation topology:

```text
test1 PWA
   ↓ same origin
test1 local relay + isolated persistent volume + own node identity
   ↓ normal public peer/API sync
node1 + node2
```

Requirements:

- keep `punkto-relay-test1` and `punkto-test1_relay_data` intact;
- preserve the existing test1 node identity and peer config;
- preserve the human-created `Test atom` (`p:u07qskyuhbuw`) in the test1 relay store;
- do not clear relay data or browser-independent node data;
- do not modify/restart/deploy node1 or node2;
- do not start Slice 4.5B or Slice 5.

## Deployment approach

1. Inspect test1 PWA + relay health before changes.
2. Back up the currently served Slice 4 PWA tree.
3. Export **only `pwa/` from exact SHA `cc687e509b7949c23b2410e930e971c0aa361c59`** using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files. Preserve Caddy relay proxy behavior and relay/container/volume state.
5. Restart/reload only what is necessary for test1 static serving/cache invalidation.

## Exact-SHA proof

Confirm both marker and exact served bytes.

At minimum compare SHA-256 from Git object vs served test1 bytes for:

- `app.js`
- `ui-map.js`
- `ui-board.js`
- `index.html`

All must match exactly. Confirm the served marker is exactly:

`pilot1-slice45a-spatial-reading-2026-08-23-1`

## Live staging checks

Verify and report as far as the available browser tooling allows:

1. Fresh/private test1 load has no uncaught module/runtime errors.
2. Map renders and `Text | Map | + | Settings` remains present/usable.
3. Existing `Test atom` remains served from test1's own relay and visible after refresh/sync.
4. Selecting `Test atom` opens the board without leaving the board partly off-screen.
5. On desktop, board is a compact right-side sidecar (roughly 400–440 px) with internal scrolling and remains fully within the viewport.
6. Opening/closing the board must not reset zoom, pitch, or bearing; map context remains continuous.
7. Selected atom receives clearly stronger spatial cues than an unselected atom.
8. Selected ground-level atom should read as ground truth/base + beacon, with `Ground` label or equivalent ground-height treatment.
9. Zoom through the available map range and confirm spatial LOD remains calm: far view beacon-only; closer view can reveal the ground relationship; no forest of permanent stems.
10. Existing map click selection, board close, board reply UI, Text view, create flow, Settings, sync, and identity/key modules remain functional.
11. `test1/health`, `/feed`, `/latest`, and `/node/info` still come from the local test1 relay and remain healthy.
12. Peer sync remains healthy; node1/node2 remain untouched.

### Elevated-atom limitation

The existing real `Test atom` is at ground level. **Do not fabricate a new public atom merely for AZ testing.**

If test1 has no legitimate elevated atom available, report that the full elevated stem + height-label appearance cannot be live-verified by AZ yet. Do not manufacture a PASS. Human/product acceptance can create or use a legitimate elevated atom afterward.

If container browser tooling cannot reliably operate a control, report the exact limitation rather than inventing a PASS.

## Safety

- test1 only;
- no product-code edits;
- no relay/protocol/schema/config changes;
- no node1/node2 deploy/restart/config change;
- no fabricated public atom;
- preserve existing test1 relay data, identity, peers, and rollback path;
- stop if exact-SHA export or served-file proof fails.

## Completion report

Return a concise report with:

- exact deployed SHA;
- backup/rollback location;
- served-file hash proof + version marker;
- browser/module result;
- board sidecar / selected-atom / LOD observations and any browser-tool limitation;
- confirmation `Test atom` remains present;
- elevated-atom verification status (PASS if a legitimate one exists, otherwise honest limitation);
- test1 relay health/node identity/peer-sync result;
- node1/node2 untouched verification;
- any blocker or unexpected behavior.

Stop after test1 verification. Do **not** deploy node1/node2 and do **not** start Slice 4.5B or Slice 5.
