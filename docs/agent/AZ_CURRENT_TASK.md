# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5B: deploy direct spatial height placement to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed Pilot_1 **Slice 4.5B — Direct Spatial Height Placement** implementation to **test1 only** and verify the live creation interaction while preserving the existing independent test1 relay/federation topology and data.

This deployment contains both the direct height-drag implementation and the follow-up visibility/reach correction. This is deployment/verification only. Do not edit Punkto product/application code.

## Exact approved application SHA

Deploy exactly:

`7ce1cba2a35eb263d8d605c59d3828ab93153550`

Latest application commit:

`fix(pilot1): keep spatial height placement visible`

This SHA includes the preceding 4.5B implementation commit:

`a9b58bf49341e31eb536d4038fdef65f4b5782fc` — `feat(pilot1): add direct spatial height placement`

Pilot CI run `32654778892` / run #72 is green for exact SHA `7ce1cba2...`:

- PWA validation: PASS
- Relay regression report: PASS

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy the PWA tree from exact SHA `7ce1cba2a35eb263d8d605c59d3828ab93153550`.

Expected version marker:

`pilot1-slice45b-direct-height-2026-08-23-2`

## Product behavior under test

4.5B makes the draft Punkto itself the height control:

> **Tap `+` → place is fixed → grab the draft beacon → drag vertically to set physical height → type → publish.**

Expected behavior:

- opening `+` stays in Map context;
- create composer remains present, but the map stays directly interactive outside the composer;
- the draft ground anchor/beacon is visibly reachable above the composer;
- before dragging, the draft spatial label explicitly includes a `Drag height` cue together with `Ground` / current height;
- pressing/touching the draft beacon and dragging upward changes only physical height;
- stem stretches live from fixed ground anchor to draft beacon;
- label updates live to `+N m · ~Floor N`;
- dragging downward decreases height and clamps at ground;
- ordinary 0 m posting remains the default and requires no height step;
- manual/floor/device-altitude controls under `Location & options` remain fallback controls and stay synchronized;
- conflicting map gestures are suppressed only during the active height drag and restored on release/cancel;
- maximum Pilot height is capped at 200 m;
- 4.5A selected-atom/board behavior remains intact.

The follow-up visibility correction also gives the MapLibre viewport bottom padding based on the live composer rectangle, so the draft beacon should be presented in usable map space instead of being hidden behind the sheet.

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
- preserve existing relay buffer/data, including the human-created `Test atom` if still retained;
- do not clear browser-independent node data;
- do not modify/restart/deploy node1 or node2;
- do not start Slice 4.5C or Slice 5.

## Deployment approach

1. Inspect test1 PWA + relay health before changes.
2. Back up the currently served Slice 4.5A PWA tree.
3. Export **only `pwa/` from exact SHA `7ce1cba2a35eb263d8d605c59d3828ab93153550`** using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files. Preserve Caddy relay proxy behavior and relay/container/volume state.
5. Restart/reload only what is necessary for test1 static serving/cache invalidation.

## Exact-SHA proof

Confirm marker and exact served bytes.

At minimum compare SHA-256 from Git object vs served test1 bytes for:

- `app.js`
- `ui-map.js`
- `ui-create.js`
- `index.html`

All must match exactly. Confirm the served marker is exactly:

`pilot1-slice45b-direct-height-2026-08-23-2`

## Live staging checks

Verify and report as far as available browser tooling allows:

1. Fresh/private test1 load has no uncaught module/runtime errors.
2. Map renders and `Text | Map | + | Settings` remains usable.
3. Tap/open `+` and confirm create opens while staying in Map context.
4. Composer must not make the height handle unreachable: the draft beacon should be visibly presented in usable map area above/outside the composer.
5. Before any drag, draft label shows `Ground` plus a clear `Drag height` affordance (or equivalent exact implemented text).
6. If browser tooling permits pointer drag: drag the draft beacon upward and confirm:
   - height increases smoothly;
   - stem stretches live;
   - label becomes `+N m · ~Floor N`;
   - geographic lon/lat remain unchanged;
   - map itself does not pan/rotate under the active drag.
7. Drag downward/back to ground and confirm it clamps at 0 m and returns to grounded treatment.
8. Release/cancel and confirm ordinary map pan/zoom/rotate gestures work again immediately.
9. Expand `Location & options`; changing manual height/floor updates the draft beacon/stem/label, and direct drag updates the fallback readout when browser tooling permits.
10. Opening/closing the composer should restore MapLibre viewport padding/context without a stuck offset.
11. Composer still allows ordinary ground posting flow (`+ → type → Publish`) without requiring height confirmation.
12. Do **not** click Publish merely to manufacture a staging atom. Human/product acceptance will perform any legitimate write afterward.
13. Existing 4.5A selected-atom board/sidecar should still open and remain contained if browser tooling can select an atom.
14. `test1/health`, `/feed`, `/latest`, and `/node/info` still come from the local test1 relay and remain healthy according to its configured serving window.
15. Peer topology remains node1 + node2; node1/node2 application versions remain untouched.

### Tactile acceptance limitation

The quality of the vertical-drag gesture is a **human tactile gate**. Container/browser automation cannot approve whether the movement actually feels natural on mouse/touch.

If browser tooling cannot reliably perform the beacon pointer drag, report that limitation explicitly. Do not invent a PASS. Exact-SHA deployment may still be operationally complete, but human/product acceptance remains required before 4.5B is considered product-accepted.

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
- create viewport / draft affordance result;
- direct height-drag result or exact automation limitation;
- fallback-control synchronization result if testable;
- confirmation test1 relay/data/topology remain healthy;
- node1/node2 untouched verification;
- any blocker or unexpected behavior.

Stop after test1 verification. Do **not** deploy node1/node2 and do **not** start Slice 4.5C or Slice 5.