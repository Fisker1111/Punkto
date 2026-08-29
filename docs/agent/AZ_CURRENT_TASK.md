# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C3: deploy placement-draft visibility fix to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy reviewed Pilot_1 **Slice 4.5C3 — keep the placement atom visible** to **test1 only** and verify the focused draft-visibility regression fix.

Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`4c1de6ad4e41183d6bbefe0cbff943cad7e8a17e`

Commit:

`fix(pilot1): keep placement atom visible`

Pilot CI run `33264695626` / run #104 is green for the exact SHA above. Both PWA validation and relay regression report completed successfully.

Expected version marker:

`pilot1-slice45c3-draft-visible-2026-08-29-1`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from the exact SHA above.

## Product behavior under test

The accepted creation flow remains unchanged:

> **Aim with center sight → `+` locks x/y → choose height → Done → write → Publish.**

Slice 4.5C3 specifically fixes the human-observed regression where the world-space draft atom could disappear during height selection.

Expected behavior during height placement:

- the world-space draft remains primary and visible;
- at Ground, the draft anchor/beacon is clearly visible;
- at positive height, **ground anchor + stem + top beacon** are simultaneously understandable;
- the draft is rendered in dedicated placement layers so ghosted buildings do not visually hide it;
- the lever handle is visually distinct from the yellow world-space atom;
- the local lever from 4.5C2 remains near the placement;
- controls/declutter behavior from 4.5C2 remains intact;
- x/y, height mapping/range, signing/storage/network behavior are unchanged.

## Preserve current test1 state

- keep `punkto-relay-test1` and its isolated persistent volume intact;
- preserve node identity, peers, relay data, and all human-created atoms;
- do not modify/restart/deploy node1 or node2;
- do not fabricate a public atom;
- do not start Slice 5.

## Deployment / verification

1. Inspect current test1 PWA + relay health.
2. Back up the currently served Slice 4.5C2 PWA tree.
3. Export only `pwa/` from exact SHA `4c1de6ad4e41183d6bbefe0cbff943cad7e8a17e` using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files; preserve Caddy relay proxy and relay/container/volume state.
5. Verify exact served SHA-256 against Git object bytes for at least `app.js`, `ui-map.js`, `index.html`, and `ui-create.js` if changed/served.
6. Confirm version marker exactly `pilot1-slice45c3-draft-visible-2026-08-29-1`.
7. Fresh/private load: no uncaught module/runtime errors; map and existing atoms render.
8. If browser tooling permits, open `+` and inspect the draft at Ground and several positive heights. Confirm the world draft remains visible and visually distinct from the lever.
9. If tactile/3D visibility cannot be automated reliably, report that explicitly. Human verification at roughly 3 / 10 / 23 / 30 / 100 / 200 m remains the product gate.
10. Confirm test1 relay health/topology/data remain intact and node1/node2 remain untouched.

## Completion report

Return:
- exact deployed SHA;
- backup/rollback path;
- served-file hash proof + version marker;
- browser/module result;
- any draft-visibility result that can be verified automatically, or exact limitation;
- test1 relay/data/topology health;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do not deploy node1/node2 and do not start Slice 5.
