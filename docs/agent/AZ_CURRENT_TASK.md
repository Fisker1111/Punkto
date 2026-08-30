# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C4: deploy height-relation framing fix to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy reviewed Pilot_1 **Slice 4.5C4 — keep the full height relation in frame** to **test1 only** and verify the focused framing fix.

Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`eabb035481284b619a76db4803aeca3cf870cad5`

Commit:

`fix(pilot1): keep height relation in frame`

Pilot CI run `33304141716` / run #118 is green for the exact SHA above.

Expected version marker:

`pilot1-slice45c4-relation-framing-2026-08-30-1`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from the exact SHA above.

## Product behavior under test

The accepted creation flow remains unchanged:

> **Aim with center sight → `+` locks x/y → choose height → Done → write → Publish.**

Slice 4.5C4 specifically replaces the C3 hard minimum zoom with height-aware framing derived from the MapLibre/deck.gl camera so the complete physical relation stays visible.

Expected behavior during height placement:

- geographic x/y remains fixed;
- selected physical height remains authoritative and unchanged by framing;
- Ground shows the locked draft clearly;
- positive height keeps **ground anchor + stem + top beacon** simultaneously inside the usable viewport;
- ordinary 0–30 m stays close enough for building-scale placement;
- 30–200 m calmly widens/reframes as needed rather than pushing the top atom off-screen;
- the local lever follows/associates with the visible elevated relation and avoids covering it;
- C3 dedicated draft visibility layers remain active through ghosted buildings;
- Done/Cancel restore normal controls/building opacity;
- signing/storage/network behavior is unchanged.

## Preserve current test1 state

- keep `punkto-relay-test1` and its isolated persistent volume intact;
- preserve node identity, peers, relay data, and all human-created atoms;
- do not modify/restart/deploy node1 or node2;
- do not fabricate a public atom;
- do not start Slice 5.

## Deployment / verification

1. Inspect current test1 PWA + relay health.
2. Back up the currently served Slice 4.5C3 PWA tree.
3. Export only `pwa/` from exact SHA `eabb035481284b619a76db4803aeca3cf870cad5` using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files; preserve Caddy relay proxy and relay/container/volume state.
5. Verify exact served SHA-256 against Git object bytes for at least `app.js`, `ui-map.js`, `ui-create.js`, and `index.html` if served.
6. Confirm version marker exactly `pilot1-slice45c4-relation-framing-2026-08-30-1`.
7. Fresh/private load: no uncaught module/runtime errors; map and existing atoms render.
8. If browser tooling permits, inspect height placement at Ground and several positive heights, especially ~23 / 66 / 100 / 200 m, verifying the whole relation stays inside the usable viewport and camera motion is calm.
9. If tactile/3D framing cannot be automated reliably, report that explicitly. Human verification remains the product gate.
10. Confirm test1 relay health/topology/data remain intact and node1/node2 remain untouched.

## Completion report

Return:
- exact deployed SHA;
- backup/rollback path;
- served-file hash proof + version marker;
- browser/module result;
- any relation-framing result that can be verified automatically, or exact limitation;
- test1 relay/data/topology health;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do not deploy node1/node2 and do not start Slice 5.
