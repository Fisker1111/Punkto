# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C2: deploy local height tool to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy reviewed Pilot_1 **Slice 4.5C2 — local height tool + placement-stage declutter** to **test1 only** and verify the focused height-placement presentation.

Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`169ff365edd9995354117d2bc02b1e976fa16dc6`

Commit:

`fix(pilot1): attach height tool to placement`

Pilot CI run `33257588895` / run #96 is green for exact SHA `169ff365...`.

Expected version marker:

`pilot1-slice45c2-local-height-tool-2026-08-29-1`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from exact SHA above.

## Product behavior under test

The accepted create flow remains unchanged:

> **Aim with center sight → `+` locks x/y → choose height → Done → write → Publish.**

Slice 4.5C2 should only refine the focused height stage:

- lever sits locally near the projected locked placement instead of permanently at the far-right edge;
- it prefers roughly 80–140 px to the right when safe and flips left if necessary;
- it stays inside the usable viewport and away from the bottom actions/top readout;
- it follows camera/viewport movement while the world anchor stays fixed;
- a subtle connector visually associates lever and placement;
- normal MapLibre zoom controls, 2D/3D toggle, onboarding hint, and unrelated shell/navigation are suppressed during height placement and restored after Done/Cancel;
- the top height readout is smaller/quieter;
- height mapping, range, building ghosting, draft coordinates, Done→Write, signing/storage/network behavior are unchanged.

## Preserve current test1 state

- keep `punkto-relay-test1` and its isolated persistent volume intact;
- preserve test1 node identity, peers, and relay data;
- do not modify/restart/deploy node1 or node2;
- do not fabricate a public atom;
- do not start Slice 5.

## Deployment / verification

1. Inspect current test1 PWA + relay health.
2. Back up the currently served Slice 4.5C PWA tree.
3. Export only `pwa/` from exact SHA `169ff365edd9995354117d2bc02b1e976fa16dc6` using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files; preserve Caddy relay proxy and relay/container/volume state.
5. Verify exact served SHA-256 against Git object bytes for at least `app.js`, `ui-map.js`, `ui-create.js`, and `index.html`.
6. Confirm version marker exactly `pilot1-slice45c2-local-height-tool-2026-08-29-1`.
7. Fresh/private load: no uncaught module/runtime errors; map and existing atoms render.
8. If browser tooling permits, open `+` and verify:
   - height stage appears first;
   - lever is local to the placement rather than viewport edge;
   - lever flips/clamps safely near screen edges;
   - zoom/2D/onboarding/shell clutter is absent during height mode;
   - Cancel/Ground/Done remain clear;
   - Done opens Write and normal controls restore afterwards.
9. If tactile/position behavior cannot be automated reliably, report that limitation explicitly; this remains a human visual/tactile gate.
10. Confirm test1 relay health/topology/data remain intact and node1/node2 are untouched.

## Completion report

Return:
- exact deployed SHA;
- backup/rollback path;
- served-file hash proof + version marker;
- browser/module result;
- lever/local-position result or exact automation limitation;
- declutter/restoration result or limitation;
- test1 relay/data/topology health;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do not deploy node1/node2 and do not start Slice 5.
