# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 3.6: deploy modularized PWA to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Deploy the reviewed Pilot_1 Slice 3.6 PWA refactor to **test1 only**, while preserving the independent test1 relay/federation state created in Slice 3.5.

This is a deployment/verification task only. Do not change Punkto product/application code.

## Exact approved application SHA

Deploy exactly:

`51c499a2a2812945eb94d32fa3d34b8275c6b85e`

Commit:

`fix(pilot1): repair slice 3.6 runtime parity`

Pilot CI run `32387860327` / run #42 is green for this exact SHA:

- PWA validation: PASS
- explicit ES-module parsing for `app.js`, `ui-map.js`, `ui-board.js`: PASS
- relay regression suite: PASS

**Do not deploy the moving `pilot-1` branch tip by name.** The branch may contain later task/control commits. Export/deploy the PWA tree from the exact SHA above.

## Important context

Slice 3.6 is behavior-preserving architecture cleanup:

- `app.js` is materially slimmer and acts more as coordinator;
- MapLibre/deck.gl presentation now lives primarily in `pwa/ui-map.js`;
- selected Map board state/events live in new `pwa/ui-board.js`;
- shared thread/root/reply semantics remain in `pwa/ui-text.js`;
- the review repair restored `getCategoryMeta()` through `pwa/core/display.js` and strengthened Pilot CI coverage.

The visible version marker intentionally remains:

`pilot1-slice3-board-2026-08-20-1`

Therefore **the marker alone is not sufficient proof of the deployed SHA**. Verify served file bytes against the exact Git SHA as described below.

## Preserve Slice 3.5 federation topology

Do not alter or replace the test1 relay topology established by Slice 3.5:

```text
test1 PWA
   ↓ same origin
test1 local relay + isolated persistent volume + own node identity
   ↓ normal public peer/API sync
node1 + node2
```

Requirements:

- keep `punkto-relay-test1` running;
- preserve the isolated `punkto-test1_relay_data` volume and node identity;
- preserve normal node1/node2 peer configuration;
- do not share or copy production relay volumes;
- do not modify, restart, or deploy node1/node2;
- do not start Slice 4.

## Deployment approach

1. Inspect current test1 PWA + relay health before changing files.
2. Back up the currently served test1 PWA tree/config if the existing deployment procedure does not already provide a safe rollback.
3. Export **only `pwa/` from exact SHA `51c499a2...`** using a Git-object-based method such as `git archive`, not the moving branch working tree.
4. Replace only the test1 static PWA files. Preserve test1 Caddy relay reverse-proxy behavior and the test1 relay/container/volume.
5. Restart/reload only what is necessary for test1 static serving/cache invalidation. Do not touch node1/node2.

## Exact-SHA served-file verification

Because the app version marker did not change, prove the deployed PWA matches the approved Git object.

For at least these files, compare the bytes from Git SHA `51c499a2...` with the bytes served from test1 (for example using SHA-256 on `git show <sha>:pwa/<file>` and on `curl` output):

- `app.js`
- `ui-map.js`
- `ui-board.js`
- `core/display.js`

All comparisons must match exactly after accounting for no server-side transformation. Also confirm `/ui-board.js` returns HTTP 200.

## Live acceptance checks

Verify and report:

1. test1 loads in a fresh/private browser with no uncaught module/runtime errors.
2. Map renders and `Text | Map | + | Settings` remains usable.
3. `window.PUNKTO_APP_VERSION` / console marker remains `pilot1-slice3-board-2026-08-20-1`.
4. `ui-board.js` loads successfully as a module.
5. `test1/health` still comes from the local test1 relay and reports healthy.
6. `test1/node/info` still identifies the existing test1 node identity, not node1/node2.
7. Peer sync with node1/node2 remains healthy (`last_error` null or equivalent).
8. Existing test1 relay atom/data count is preserved; do not fabricate public atoms.
9. If a real synced atom is available, verify beacon → bottom-sheet board → close behavior. If still zero real atoms, report that honestly; do not create fake network activity merely for this check.
10. node1/node2 application versions remain unchanged.

## Safety

- test1 only.
- no product-code edits.
- no relay/protocol/schema changes.
- no node1/node2 deployment/config/restart.
- no fake public atoms.
- preserve rollback path and Slice 3.5 relay data/identity.
- stop if the exact Git SHA cannot be exported or served-file hashes do not match.

## Completion report

Return a concise report containing:

- exact deployed SHA;
- backup/rollback location;
- served-file hash comparison results;
- browser/module result;
- test1 relay health + node identity + peer-sync result;
- atom count and real-atom board verification if possible;
- node1/node2 untouched verification;
- any limitation/blocker.

Stop after test1 verification. Do **not** deploy node1/node2 and do **not** start Slice 4.
