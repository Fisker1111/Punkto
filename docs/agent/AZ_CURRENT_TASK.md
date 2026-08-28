# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5B2: deploy sight-lock + height lever flow to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed Pilot_1 **Slice 4.5B2 — Sight-Locked Height Lever** implementation to **test1 only** and verify the live spatial placement flow while preserving the existing independent test1 relay/federation topology and data.

This is deployment/verification only. Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`d6541b9f3cc67bcc7e302cc68201c52ba1b054ce`

Commit:

`feat(pilot1): add sight-locked height lever flow`

Pilot CI run `33189649724` / run #80 is green for exact SHA `d6541b9f...`.

Expected version marker:

`pilot1-slice45b2-sight-height-lever-2026-08-28-1`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from exact SHA `d6541b9f3cc67bcc7e302cc68201c52ba1b054ce`.

## Product behavior under test

The creation flow is now deliberately sequential:

> **Aim with the existing center sight → tap `+` to lock X/Y → use the floating height lever to choose Z while the result is rendered in the map/buildings → `Done` → write → publish.**

Expected behavior:

- before `+`, the existing center sight is the intended horizontal placement point;
- tapping `+` captures the current MapLibre center as the draft lon/lat and does **not** immediately open the writing composer;
- the height-placement stage keeps the map visible and spatially dominant;
- a large vertical height lever is visible at the side, with Ground / ordinary-building range / high-range feedback;
- changing the lever changes only physical height, not lon/lat;
- the map renders the draft as ground anchor + vertical stem + elevated beacon;
- around ordinary heights (0–30 m), lever resolution is intentionally finer than at large heights;
- the height readout updates live (`Ground`, `+N m · ~Floor N`);
- entering height placement gives the camera a useful oblique pitch without moving to another geographic place;
- 3D building extrusion layers become translucent during height placement so the user can visually understand both the ground anchor and elevated beacon when the atom lies in/behind a building;
- `Ground` resets height to 0;
- `Done` exits spatial placement and only then opens the writing composer;
- the writing composer shows the locked spatial summary and does not compete with active spatial manipulation;
- fallback numeric/floor/device controls remain available in `Location & options` and stay synchronized;
- cancel from height stage creates no atom;
- ordinary ground posting remains fast: `+` → `Done` → type → Publish.

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
- preserve test1 node identity and peer config;
- preserve existing relay buffer/data;
- do not clear browser-independent node data;
- do not modify/restart/deploy node1 or node2;
- do not start Slice 4.5C or Slice 5.

## Deployment approach

1. Inspect current test1 PWA + relay health before changes.
2. Back up the currently served Slice 4.5B PWA tree.
3. Export **only `pwa/` from exact SHA `d6541b9f3cc67bcc7e302cc68201c52ba1b054ce`** using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files. Preserve Caddy relay proxy behavior and relay/container/volume state.
5. Restart/reload only what is necessary for test1 static serving/cache invalidation.

## Exact-SHA proof

Compare SHA-256 from Git object vs served test1 bytes at minimum for:

- `app.js`
- `ui-map.js`
- `ui-create.js`
- `index.html`

All must match exactly. Confirm served marker exactly:

`pilot1-slice45b2-sight-height-lever-2026-08-28-1`

## Live staging checks

Verify as far as browser tooling allows:

1. Fresh/private test1 load has no uncaught module/runtime errors.
2. Map renders and normal navigation remains usable before placement.
3. Move map so the center sight is over a recognizable location; open `+` and verify the writing composer does **not** open first.
4. Confirm the height stage appears over a mostly unobstructed map with a visible lever and live `Ground` readout.
5. Confirm the draft ground anchor corresponds to the pre-`+` center location.
6. If browser tooling permits lever drag/click:
   - set approximately 3 m, 10 m, 20–30 m;
   - confirm lon/lat do not move;
   - confirm stem grows and upper beacon rises;
   - confirm live label updates;
   - confirm Ground resets to 0.
7. At a location with visible 3D buildings, confirm building extrusions are ghosted/translucent during height placement and both ground anchor and elevated beacon/stem remain visually readable as far as the renderer permits.
8. Press `Done` and confirm the height stage disappears and only then the normal `Write Punkti` composer appears with the chosen height summary.
9. Cancel height placement and confirm no public atom is fabricated or published.
10. Closing/canceling create restores ordinary building opacity/navigation state.
11. Existing 4.5A board/selected-atom behavior still loads without error.
12. `test1/health` and node info remain healthy; peers remain node1 + node2.
13. node1/node2 application versions remain untouched.

### Human acceptance limitation

The spatial interaction is still a **human visual/tactile product gate**. If AZ browser tooling cannot reliably operate the lever or inspect 3D occlusion, report that limitation explicitly rather than inventing a PASS. Operational deployment may still complete if exact-SHA proof and runtime health pass.

## Safety

- test1 only;
- no product-code edits;
- no relay/protocol/schema/config changes;
- no node1/node2 deploy/restart/config change;
- no fabricated public atom;
- preserve test1 relay data, identity, peers, and rollback path;
- stop if exact-SHA export or served-file proof fails.

## Completion report

Return a concise report with:

- exact deployed SHA;
- backup/rollback location;
- served-file hash proof + version marker;
- browser/module result;
- sight-lock / height-stage result;
- lever result or exact automation limitation;
- building-transparency/anchor+stem+beacon result or limitation;
- `Done → Write` sequential-flow result if testable;
- confirmation test1 relay/data/topology remain healthy;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do **not** deploy node1/node2 and do **not** start Slice 4.5C or Slice 5.