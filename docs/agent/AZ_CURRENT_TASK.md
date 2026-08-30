# AZ Current Task

Status: **HOLD — B2-reference height-placement restoration deployed to test1; awaiting human acceptance**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Current state

The B2-reference height-placement restoration is deployed to **test1 only** from exact application SHA:

`26d21a10d3f97b4e91c18cd4fcdb7290c0379d73`

Commit:

`fix(pilot1): restore proven height placement render path`

Served version marker:

`pilot1-slice45b2-render-restore-2026-08-30-1`

Deployment was verified by exact SHA-256 matches for `app.js`, `ui-map.js`, `ui-create.js`, and `index.html`. Fresh browser load is clean. The test1 relay/federation remains healthy, human-created atoms are preserved, and node1/node2 were not modified.

The height-placement implementation is intentionally restored to the last human-accepted B2 pattern:

- draft participates in the normal `scatterData` / atom / ground-ring / lollipop render path;
- height lever is fixed at the right side;
- height changes do not dynamically change map zoom;
- newer shell/board/composer remain intact outside placement;
- signing/storage/network/relay/federation are unchanged.

## Human acceptance gate

Human visual/tactile verification is now decisive. Verify on test1:

- Ground shows the yellow draft object after `+` locks x/y;
- positive height shows yellow ground anchor + stem + top beacon;
- right-side lever remains secondary to the world object;
- changing height does not dynamically change map zoom;
- building ghosting behaves correctly;
- Done opens Write; Cancel persists nothing and restores normal UI.

## HOLD rule

There is no active AZ task now.

- Do not redeploy a moving `pilot-1` branch tip.
- Do not modify/restart/deploy node1 or node2.
- Preserve test1 relay/federation topology and persistent data.
- Do not start Slice 5 until explicit ChatGPT/product instruction after human acceptance.
