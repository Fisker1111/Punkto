# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C: deploy hero create shell + visual polish to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed Pilot_1 **Slice 4.5C — hero create action + visual polish** to **test1 only** and verify the shell/3D presentation without changing the accepted Slice 4.5B2 creation philosophy.

This is deployment/verification only. Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`ec1d3d63689c66cbfb7e076c89da6c14305a791e`

Commit:

`feat(pilot1): make create the hero action`

Pilot CI run `33200096500` / run #88 is green for exact SHA `ec1d3d6...`.

Expected version marker:

`pilot1-slice45c-hero-shell-polish-2026-08-28-1`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from exact SHA `ec1d3d63689c66cbfb7e076c89da6c14305a791e`.

## Product behavior under test

The accepted creation sequence remains locked:

> **Aim with center sight → `+` locks x/y → choose height with lever → Done → write → Publish.**

Slice 4.5C should only improve emphasis and finish:

- `+` is now the unmistakable hero action in the lower-left control cluster;
- Text / Map / Settings remain available but visually quieter and smaller;
- both mobile and desktop shells preserve the same hierarchy;
- map remains spatially dominant and controls do not cover the center sight or normal atom-reading area;
- crosshair/sight is visually cleaner and precise;
- atom beacon / ground anchor / stem rendering is slightly crisper and more coherent;
- 3D building presentation is slightly lighter/refined while keeping enough solidity for spatial reading;
- height lever visual treatment is polished but its behavior remains unchanged;
- no new create steps or protocol/storage behavior are introduced.

## Preserve current test1 state

Do not alter the Slice 3.5 federation topology or persistent data.

Requirements:

- keep `punkto-relay-test1` and `punkto-test1_relay_data` intact;
- preserve test1 node identity and peer config;
- preserve existing relay buffer/data and browser-independent node data;
- do not modify/restart/deploy node1 or node2;
- do not start Slice 5.

## Deployment approach

1. Inspect current test1 PWA + relay health before changes.
2. Back up the currently served Slice 4.5B2 PWA tree.
3. Export **only `pwa/` from exact SHA `ec1d3d63689c66cbfb7e076c89da6c14305a791e`** using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files. Preserve Caddy relay proxy behavior and relay/container/volume state.
5. Restart/reload only what is necessary for test1 static serving/cache invalidation.

## Exact-SHA proof

Compare SHA-256 from Git object vs served test1 bytes at minimum for:

- `app.js`
- `ui-map.js`
- `index.html`

All must match exactly. Confirm served marker exactly:

`pilot1-slice45c-hero-shell-polish-2026-08-28-1`

## Live staging checks

Verify as far as browser tooling allows:

1. Fresh/private test1 load has no uncaught module/runtime errors.
2. Map renders and existing atoms remain visible.
3. Confirm the lower-left shell visibly makes `+` the dominant action while Text / Map / Settings remain readable and usable.
4. Confirm mobile-width shell does not cover the center sight, important map content, or bottom-right MapLibre controls excessively.
5. Confirm desktop shell appears as a compact lower-left cluster rather than the old mid-left rail.
6. Confirm Text, Map, Settings and `+` still trigger their original actions.
7. Confirm center sight remains precisely centered and readable over varied map/building backgrounds.
8. Confirm 3D buildings remain readable and the slightly refined styling does not flatten the spatial scene.
9. Confirm existing atom ground anchor / stem / beacon presentation still renders correctly, including an elevated atom if one is available locally.
10. Open `+` if tooling permits and confirm the accepted B2 sequence still starts with height placement rather than the write composer.
11. Confirm height-stage lever still renders and its polished visuals do not interfere with touch target or controls.
12. Cancel create and verify no public atom is fabricated/published.
13. `test1/health` remains healthy and relay topology/data remain unchanged.
14. node1/node2 application versions remain untouched.

### Human acceptance limitation

Visual hierarchy and overall polish remain a **human product gate**. If AZ browser tooling cannot reliably operate create or assess tactile quality, report the limitation explicitly rather than inventing a PASS.

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
- hero `+` shell result;
- 3D/crosshair/beacon visual result or automation limitation;
- confirmation accepted B2 create sequence is preserved if testable;
- confirmation test1 relay/data/topology remain healthy;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do **not** deploy node1/node2 and do **not** start Slice 5.