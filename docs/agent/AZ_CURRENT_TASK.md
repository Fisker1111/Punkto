# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 4: deploy fast-create PWA to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed Pilot_1 Slice 4 fast-create implementation to **test1 only**, preserve the existing independent test1 relay/federation topology and its real `Test atom`, and verify the staged create UI without fabricating additional public atoms.

This is deployment/verification only. Do not edit Punkto product/application code.

## Exact approved application SHA

Deploy exactly:

`e01a587ed9782f74750daa0cd6c0bb663fc5574b`

Commit:

`feat(pilot1): streamline fast create flow`

Pilot CI run `32400098204` / run #52 is green for this exact SHA:

- PWA validation: PASS
- relay regression suite: PASS

**Do not deploy the moving `pilot-1` branch tip by name.** Export/deploy the PWA tree from the exact SHA above.

Expected version marker:

`pilot1-slice4-fast-create-2026-08-20-1`

## What changed

Slice 4 is intentionally narrow:

- message field is the dominant create control;
- primary action says `Publish`;
- author + altitude/floor/location adjustment controls are collapsed under `Location & options` by default;
- category remains directly accessible, including Warning/Emergency;
- first-use public-data acknowledgement remains a blocking one-time gate;
- empty/whitespace-only text cannot publish;
- publish is disabled while a submission is in flight;
- optional device-altitude geolocation no longer runs merely because `+` is opened; it runs only after explicit user action;
- existing signing, normal relay write path, local storage, sync/federation, map/board behavior, and altitude semantics remain unchanged.

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
- preserve the human-created `Test atom` (`p:u07qskyuhbuw`) in the test1 relay store;
- do not clear relay data or browser-independent node data;
- do not modify/restart/deploy node1 or node2;
- do not start Slice 5.

## Deployment approach

1. Inspect test1 PWA + relay health before changes.
2. Back up the currently served Slice 3.6 PWA tree.
3. Export **only `pwa/` from exact SHA `e01a587e...`** using a Git-object-based method such as `git archive`.
4. Replace only test1 static PWA files. Preserve Caddy relay proxy behavior and relay/container/volume state.
5. Restart/reload only what is necessary for test1 static serving/cache invalidation.

## Exact-SHA proof

Because this slice has a new marker, confirm both marker and exact served bytes.

At minimum compare SHA-256 from Git object vs served test1 bytes for:

- `app.js`
- `index.html`
- `ui-create.js`

All must match exactly. Confirm the served marker is exactly:

`pilot1-slice4-fast-create-2026-08-20-1`

## Live staging checks

Verify and report as far as the available browser tooling allows:

1. Fresh/private test1 load has no uncaught module/runtime errors.
2. Map renders; `Text | Map | + | Settings` remains present/usable.
3. Existing `Test atom` still appears through the normal test1 relay/API and remains visible after refresh/sync.
4. Opening `+` shows a create sheet with:
   - message field prominent;
   - current location/anchor visible;
   - category immediately accessible;
   - primary `Publish` action;
   - `Location & options` closed by default.
5. For an acknowledged browser state, message field receives focus promptly and ordinary composition does not require opening advanced options.
6. Empty text leaves Publish disabled; valid non-empty text enables Publish.
7. Warning/Emergency remain quick to select; Emergency hint appears when EMGC is selected.
8. Opening `+` by itself must **not** trigger optional high-accuracy/device-altitude geolocation. If browser tooling cannot prove permission-call behavior directly, inspect runtime/network/permission behavior and report the limitation honestly.
9. Expanding `Location & options` exposes author and altitude/floor/ground/roof/device-altitude controls without runtime errors.
10. Do **not** click Publish merely to manufacture a staging atom. A human will perform the real write-path acceptance after deployment if needed.
11. `test1/health`, `/feed`, `/latest`, and `/node/info` still come from the local test1 relay and remain healthy.
12. Peer sync remains healthy; node1/node2 remain untouched.

If container browser tooling cannot reliably operate a control, report the exact limitation rather than inventing a PASS.

## Safety

- test1 only;
- no product-code edits;
- no relay/protocol/schema/config changes;
- no node1/node2 deploy/restart/config change;
- no fabricated public atom;
- preserve existing test1 relay data, identity, peers, and rollback path;
- stop if exact-SHA export or served-file proof fails.

## Completion report

Return a concise report with:

- exact deployed SHA;
- backup/rollback location;
- served-file hash proof + version marker;
- browser/module result;
- fast-create UI checks and any browser-tool limitation;
- confirmation `Test atom` remains present;
- test1 relay health/node identity/peer-sync result;
- node1/node2 untouched verification;
- any blocker or unexpected behavior.

Stop after test1 verification. Do **not** deploy node1/node2 and do **not** start Slice 5.
