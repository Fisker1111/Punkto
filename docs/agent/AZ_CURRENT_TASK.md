# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 3.6 live-atom acceptance gate**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (operations / live verification)**

## Goal

Verify the first real atom created by the human on test1 after the Slice 3.6 deployment.

The human has just published a real public atom with text:

`Test atom`

This is a **verification-only gate**. Do not edit or deploy product code. Do not create additional test/public atoms. Do not start Slice 4.

## Current approved/deployed application

Exact deployed application SHA:

`51c499a2a2812945eb94d32fa3d34b8275c6b85e`

Expected marker:

`pilot1-slice3-board-2026-08-20-1`

Slice 3.5 topology must remain unchanged:

```text
test1 PWA
   ↓ same origin
test1 local relay + isolated persistent volume + own node identity
   ↓ normal public peer/API sync
node1 + node2
```

## Verification steps

1. **Find the real atom on test1's own relay/store.**
   - Locate the atom whose text is exactly `Test atom` (or clearly the newly posted human atom if normalization adds surrounding fields).
   - Record its atom ID/stable ID, punkto/location ID, timestamp, author/signature presence, and category if present.
   - Do not expose private key/secret material.

2. **Verify local relay acceptance and serving.**
   - Confirm it is present in test1's persistent append-only store.
   - Confirm it is returned by the normal public same-origin relay API (`/feed`, `/latest`, or the appropriate existing endpoint).
   - Confirm `/health` remains healthy and `/node/info` still identifies the same test1 node identity.

3. **Verify browser/runtime behavior with this real atom.**
   In a fresh browser/session on test1:
   - confirm the atom appears in the UI / visible count becomes non-zero when in scope;
   - confirm its beacon renders on the Map without runtime/module/deck.gl errors;
   - select the beacon and confirm **exactly that real atom** opens the Slice 3 bottom-sheet board;
   - confirm the root message is primary and reads `Test atom`;
   - close the board and confirm the map camera/context does not jump/reset;
   - open Text view and confirm the same real atom is represented there;
   - return to Map and confirm the UI remains usable.

4. **Verify the Slice 3.6 runtime regression is actually closed.**
   - With the real atom rendered, confirm there is no `getCategoryMeta is not defined` or equivalent runtime error.
   - Confirm `ui-board.js` is loaded and board interaction works.

5. **Verify federation state without modifying production.**
   - Report whether test1's peer sync state remains healthy.
   - Check whether the new atom has propagated through the normal Punkto peer mechanism to node1 and/or node2 **only through their public APIs/logically observable peer state**.
   - Do not access production filesystems/databases and do not change/restart node1/node2.
   - If propagation has not occurred yet, report that honestly; do not force it with config changes.

6. **Preserve deployment proof.**
   - Confirm test1 still serves the approved Slice 3.6 application and marker.
   - No app file replacement is required for this task.

## Acceptance criteria

PASS when all of the following are true:

- the human-created `Test atom` exists in test1's own persistent relay store;
- the atom is served through the normal test1 public API;
- the real atom renders without the Slice 3.6 runtime regression;
- beacon selection opens the correct real bottom-sheet board;
- board close preserves map context;
- Text and Map both represent the same real atom;
- test1 relay/node identity and peer sync remain healthy;
- node1/node2 remain untouched;
- no additional fabricated atom was created.

Peer propagation to node1/node2 is useful evidence but is **not a blocker** if the normal sync mechanism is healthy and propagation timing/serving policy explains a delay.

## Completion report

Return a concise report with:

- discovered atom ID + punkto ID + timestamp + signature/category summary;
- local store/API proof;
- browser beacon/board/Text verification;
- confirmation the `getCategoryMeta` runtime regression is absent with a real atom;
- peer-sync/propagation observation;
- test1 health/node identity;
- node1/node2 untouched verification;
- any blocker or unexpected behavior.

Stop after verification. Do not deploy anything and do not start Slice 4.
