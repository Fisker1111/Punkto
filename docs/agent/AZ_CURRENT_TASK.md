# AZ Current Task

Status: **HOLD — deck-overlay visibility fix deployed to test1; awaiting human acceptance**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Current state

The CSS-only deck-overlay visibility fix is deployed to **test1 only** from exact application SHA:

`71053f1743c9982f0ce1420ae99beedc0bdb440a`

Commit:

`fix(pilot1): keep deck overlay visible during height placement`

Served version marker remains:

`pilot1-slice45b2-render-restore-2026-08-30-1`

Deployment was verified by exact SHA-256 matches for `index.html`, `app.js`, `ui-map.js`, and `ui-create.js`. `index.html` carries the selector fix; the other three files remain byte-identical to the B2 restoration. Fresh browser load is clean. test1 relay/federation remains healthy, human-created atoms are preserved, and node1/node2 were not modified.

Confirmed root cause: height-placement CSS hid the MapLibre top-corner control containers, including the top-left container that hosts deck.gl's `MapboxOverlay`, so the entire deck.gl canvas disappeared during placement. The fix targets child `.maplibregl-ctrl` elements instead, preserving the deck.gl container.

## Human acceptance gate

Human visual/tactile verification is now decisive. Verify on test1:

- Ground: yellow draft atom is visible after `+` locks x/y;
- positive height: yellow ground anchor + stem + top atom are visible;
- existing published atoms remain visible during height placement;
- right-side lever remains usable;
- changing height does not dynamically change map zoom;
- Done opens Write; Cancel persists nothing.

## HOLD rule

There is no active AZ deployment task now.

- Do not redeploy a moving `pilot-1` branch tip.
- Do not modify/restart/deploy node1 or node2.
- Preserve test1 relay/federation topology and persistent data.
- Do not start Slice 5 until explicit ChatGPT/product instruction after human acceptance.
