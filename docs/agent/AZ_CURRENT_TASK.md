# AZ Current Task

Status: **ACTIVE — deploy confirmed deck-overlay visibility fix to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the confirmed CSS fix that keeps the deck.gl overlay visible during height placement to **test1 only**.

Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`71053f1743c9982f0ce1420ae99beedc0bdb440a`

Commit:

`fix(pilot1): keep deck overlay visible during height placement`

Pilot CI run `34029473029` / run #149 is green for this exact SHA.

The application version marker remains:

`pilot1-slice45b2-render-restore-2026-08-30-1`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from exact SHA above.

## Root cause now confirmed

Height-placement CSS was setting the MapLibre top-corner control containers to `opacity: 0`. deck.gl's `MapboxOverlay` mounts in the top-left control container, so entering height placement hid the entire deck.gl canvas — including all published atoms and the yellow draft.

The reviewed fix changes only two CSS selectors in `pwa/index.html` so they target child `.maplibregl-ctrl` controls rather than the top-corner containers themselves. This preserves the deck.gl container while still allowing actual MapLibre controls to be hidden.

## Preserve current test1 state

- keep `punkto-relay-test1` and its isolated persistent volume intact;
- preserve node identity, peers, relay data, and all human-created atoms;
- do not modify/restart/deploy node1 or node2;
- do not fabricate public atoms;
- do not start Slice 5.

## Deployment / verification

1. Inspect current test1 PWA + relay health.
2. Back up the currently served PWA tree.
3. Export only `pwa/` from exact SHA `71053f1743c9982f0ce1420ae99beedc0bdb440a` using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files; preserve Caddy relay proxy and relay/container/volume state.
5. Verify exact served SHA-256 against Git object bytes for at least `index.html`, `app.js`, `ui-map.js`, and `ui-create.js`.
6. Confirm served marker remains exactly `pilot1-slice45b2-render-restore-2026-08-30-1`.
7. Fresh/private load: no uncaught module/runtime errors; map and existing atoms render.
8. If browser tooling permits, verify the deck.gl canvas/control container remains visible when `body.create-height-placement-open` is active. Do not claim tactile placement acceptance unless genuinely observed.
9. Confirm test1 relay health/topology/data remain intact and node1/node2 remain untouched.

## Human acceptance gate after deploy

Human verification is decisive:

- Ground: yellow draft atom is visible after `+` locks x/y;
- positive height: yellow ground anchor + stem + top atom are visible;
- existing atoms no longer disappear during height placement;
- right-side lever remains usable;
- changing height does not dynamically change map zoom;
- Done opens Write; Cancel persists nothing.

## Completion report

Return:
- exact deployed SHA;
- backup/rollback path;
- served-file hash proof + marker;
- browser/module result;
- any deck-overlay visibility verification possible automatically;
- test1 relay/data/topology health;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do not deploy node1/node2 and do not start Slice 5.
