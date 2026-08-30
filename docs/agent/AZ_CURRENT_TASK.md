# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C4 correction: deploy stable placement preview to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed Slice 4.5C4 correction to **test1 only** and verify the corrected height-placement behavior.

Do not edit Punkto application/product code.

## Exact approved application SHA

Deploy exactly:

`0ed108d9e92d147a40ff1f9bb553d042ad72ecbb`

Commit:

`fix(pilot1): stabilize height placement preview`

Pilot CI run `33305845786` / run #126 is green for the exact SHA above.

Expected version marker:

`pilot1-slice45c4-stable-placement-2026-08-30-2`

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy only `pwa/` from exact SHA above.

## Product correction under test

Human testing rejected the previous C4 dynamic framing behavior. The corrected interaction restores the accepted rule:

> **The sight chooses place. The lever chooses height. The world shows both.**

Expected behavior:

- `+` still locks exact x/y from the center sight;
- after lock, the blue sight and unrelated shell UI no longer compete with the draft;
- Ground shows a clearly visible yellow world-space placement object;
- positive height shows yellow ground anchor + yellow/cased stem + yellow top beacon;
- the dark height lever remains visually separate and secondary;
- moving the height lever from 0 through 200 m does **not change map zoom**;
- `Leave the first note here.` is hidden during height placement;
- building ghosting remains active during placement and restores afterward;
- Done opens Write; Cancel persists nothing and restores normal UI;
- signing/storage/network/relay/federation remain unchanged.

The exact high-height visual result remains a human/tactile gate. AZ should not fabricate public atoms to test it.

## Preserve current test1 state

- keep `punkto-relay-test1` and its isolated persistent volume intact;
- preserve node identity, peers, relay data, and all human-created atoms;
- do not modify/restart/deploy node1 or node2;
- do not fabricate a public atom;
- do not start Slice 5.

## Deployment / verification

1. Inspect current test1 PWA + relay health.
2. Back up the currently served C4 PWA tree.
3. Export only `pwa/` from exact SHA `0ed108d9e92d147a40ff1f9bb553d042ad72ecbb` using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files; preserve Caddy relay proxy and relay/container/volume state.
5. Verify exact served SHA-256 against Git object bytes for at least `app.js`, `ui-map.js`, `index.html`, and `ui-create.js` if served.
6. Confirm version marker exactly `pilot1-slice45c4-stable-placement-2026-08-30-2`.
7. Fresh/private load: no uncaught module/runtime errors; map and existing atoms render.
8. If browser tooling permits without publishing, inspect placement state enough to confirm shell/crosshair/empty hint declutter and that lever changes no longer trigger map zoom changes.
9. If tactile height manipulation cannot be automated reliably, report that explicitly; human verification remains mandatory.
10. Confirm test1 relay health/topology/data remain intact and node1/node2 remain untouched.

## Completion report

Return:
- exact deployed SHA;
- backup/rollback path;
- served-file hash proof + version marker;
- browser/module result;
- any placement-state verification possible automatically, or exact limitation;
- test1 relay/data/topology health;
- node1/node2 untouched verification;
- blockers/unexpected behavior.

Stop after test1 verification. Do not deploy node1/node2 and do not start Slice 5.
