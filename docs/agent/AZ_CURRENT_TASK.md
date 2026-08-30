# AZ Current Task

Status: **ACTIVE — deploy B2-reference height-placement restoration to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed restoration of the last human-accepted Slice 4.5B2 height-placement render path to **test1 only**.

This task intentionally rolls the height-placement rendering/control architecture back to the proven B2 pattern while keeping the newer Punkto shell/board/composer and all protocol/signing/federation behavior intact.

Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`26d21a10d3f97b4e91c18cd4fcdb7290c0379d73`

Commit:

`fix(pilot1): restore proven height placement render path`

Pilot CI run `33322190329` / run #134 is green for this exact SHA.

Expected version marker:

`pilot1-slice45b2-render-restore-2026-08-30-1`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from the exact SHA above.

## Product behavior under test

Human testing established a known-good regression boundary: Slice 4.5B2 showed the draft atom correctly, before later local-lever / dedicated draft-layer work regressed it.

This restoration deliberately returns the draft to the normal deck.gl atom render path and returns the height lever to the fixed right-side B2 placement.

Expected behavior:

- `+` locks exact x/y from the center sight;
- height stage opens before writing;
- draft is rendered through the same `scatterData` / atom / ground-ring / lollipop layers as the proven B2 path;
- Ground shows the yellow draft object;
- positive height shows yellow ground anchor + stem + top beacon;
- lever is fixed at the right side, secondary to the world object;
- changing height does not dynamically change map zoom;
- building ghosting remains active during placement and restores afterward;
- Done opens Write; Cancel persists nothing;
- newer hero shell / board / composer remain intact outside the height stage;
- signing/storage/network/relay/federation are unchanged.

## Preserve current test1 state

- keep `punkto-relay-test1` and its isolated persistent volume intact;
- preserve node identity, peers, relay data, and all human-created atoms;
- do not modify/restart/deploy node1 or node2;
- do not fabricate a public atom;
- do not start Slice 5.

## Deployment / verification

1. Inspect current test1 PWA + relay health.
2. Back up the currently served stable-placement PWA tree.
3. Export only `pwa/` from exact SHA `26d21a10d3f97b4e91c18cd4fcdb7290c0379d73` using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files; preserve Caddy relay proxy and relay/container/volume state.
5. Verify exact served SHA-256 against Git object bytes for at least `app.js`, `ui-map.js`, `ui-create.js`, and `index.html` if served.
6. Confirm version marker exactly `pilot1-slice45b2-render-restore-2026-08-30-1`.
7. Fresh/private load: no uncaught module/runtime errors; map and existing atoms render.
8. If browser tooling permits without publishing, inspect height placement enough to confirm the right-side lever is back and no dynamic zoom is triggered by height changes.
9. Do not claim the draft atom visibility is accepted unless it can genuinely be seen; human verification is the decisive gate.
10. Confirm test1 relay health/topology/data remain intact and node1/node2 remain untouched.

## Completion report

Return:
- exact deployed SHA;
- backup/rollback path;
- served-file hash proof + version marker;
- browser/module result;
- any height-placement behavior verified automatically, or exact limitation;
- test1 relay/data/topology health;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do not deploy node1/node2 and do not start Slice 5.
