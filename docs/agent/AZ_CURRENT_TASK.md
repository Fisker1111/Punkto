# AZ Current Task

Status: **ACTIVE — Slice 6 production cutover and test1 retirement**

Repository: `Fisker1111/Punkto`
Coordination branch: `pilot-1`
Merged PR: `#110`
Owner: **AZ (deployment / operations)**

## Mission

Complete **Slice 6** and close the Pilot_1 staging era:

1. deploy the merged Pilot_1 release from `main` to `https://punkto.xyz`;
2. verify production end-to-end;
3. preserve/verify legitimate test1 data;
4. retire the standalone test1 app/relay only after production is proven good;
5. leave `node1` and `node2` untouched.

PR #110 is already merged to `main`.

Exact merged main release SHA:

`c25c6f1320206742d7d94b52496bc6be0a2e12dd`

Accepted visual application commit contained in that merge:

`6cd203c87de49d9322dae590b56fa8fee429c4c4`

The human has accepted Slice 5 including the glowing-orb polish. Pilot CI on the PR head was green before merge.

## Hard exact-SHA rule

**Do not deploy a moving branch tip.** Deploy production from exact merged main SHA:

`c25c6f1320206742d7d94b52496bc6be0a2e12dd`

Use Git-object/exact-SHA deployment discipline (`git archive` or equivalent). Do not rebuild product code manually on the server.

## Phase 1 — preflight and backups

Before changing production:

1. Fetch `origin/main` and verify `c25c6f1320206742d7d94b52496bc6be0a2e12dd` exists and is the PR #110 merge.
2. Record current `punkto.xyz` PWA, relay/container, Caddy/routing, volume, node identity and health state.
3. Make timestamped rollback backups of the currently served production PWA and any production relay/config that will be touched.
4. Record test1 state: PWA version, relay health, persistent volume, current buffer/legitimate human atoms and federation state.
5. Confirm node1/node2 current markers and do not modify them.
6. Inspect the actual production topology before changing anything. Preserve production identity, persistent data and federation configuration unless a change is strictly required for this release.

If production topology differs materially from expectations, stop and report rather than improvising a destructive migration.

## Phase 2 — deploy `punkto.xyz`

Deploy the PWA from exact main SHA `c25c6f1320206742d7d94b52496bc6be0a2e12dd` to `punkto.xyz`.

The release must include the accepted Slice 5 behavior, including:

- nearby-first spatial world;
- glowing Punkti orbs;
- physical-altitude stems/ground anchors;
- accepted Aim → `+` → height → Done → Write → Publish flow;
- board/replies;
- Your Punkto Identity UX and local persistence;
- exact `/p/<64-hex-atom-id>` links;
- client-side A4 Punkti PDF with QR and footer `punkto.xyz · leave a message here`.

Do not touch node1/node2. Do not make opportunistic product-code edits.

If the production relay component does not require a code/config change for this release, leave it intact. If a relay/runtime change is genuinely required, first prove why from the merged SHA/topology and preserve identity/data/volume.

## Phase 3 — production proof

Before retiring test1, verify `punkto.xyz` is healthy.

Required checks:

1. Served core files match exact Git-object bytes from `c25c6f1320206742d7d94b52496bc6be0a2e12dd` for at least:
   - `app.js`
   - `index.html`
   - `ui-map.js`
   - `ui-board.js`
   - `ui-text.js`
   - `ui-create.js`
   - `ui-settings.js`
   - `key-management.js`
   - `print-pdf.js`
   - `protocol/exact-link.js`
   - `lib/qrcode-generator.js`
2. Fresh/private browser loads `https://punkto.xyz` without uncaught module/runtime errors.
3. Map and glowing orbs render on a WebGL-capable browser if available.
4. Existing public atoms load/read correctly.
5. Create/cancel placement flow works structurally without camera regressions.
6. Identity settings load; do not expose recovery words/private material in durable logs.
7. Exact atom links under `https://punkto.xyz/p/<atom_id>` resolve correctly.
8. `Print this Punkti` generates an A4 PDF whose QR points to the exact `https://punkto.xyz/p/<atom_id>` URL.
9. Board/Text/Settings/reply UI smoke-checks pass.
10. Production relay/health/federation is healthy and normal peer visibility to node1/node2 is preserved.

Do not create fake public data merely for testing. If a harmless legitimate human action is required, leave it to the human.

## Phase 4 — test1 data safety gate

**Do not retire test1 until this gate passes.**

1. Enumerate legitimate currently retained human atoms on test1 by canonical atom ID.
2. Verify those legitimate atoms are available through the normal production/federated network or otherwise safely preserved.
3. If any legitimate retained atom exists only on test1, do not shut the relay down. Keep test1 online and report the exact gap so we can preserve it without re-signing/fabricating history.
4. Make a final archival backup of test1 PWA, relay data volume, identity/config and relevant Caddy config.

Aged-out atoms under the deliberate retention policy are not a retirement blocker if they are already outside the configured serving window; record that distinction clearly.

## Phase 5 — retire test1

Only after production proof and the test1 data-safety gate pass:

1. Disable standalone test1 writes/runtime.
2. Stop the standalone test1 relay/app containers as appropriate, but **preserve the relay data volume and final backup** for rollback/archive.
3. Configure `test1.punkto.xyz` as a permanent preserving redirect to `punkto.xyz`:
   - preserve path;
   - preserve query string;
   - `/p/<atom_id>` must therefore land on the same exact production path.
4. Verify several redirect cases, including `/`, an exact `/p/<atom_id>`, and a URL with query parameters.
5. Confirm node1/node2 remain untouched and healthy.

Do not delete the archived test1 data/volume during this task.

## Final report

Report:

- exact merged main SHA deployed;
- production backup/rollback paths;
- served-file hash proof;
- production browser/runtime result and any visual limitations;
- production relay/federation health;
- exact-link + PDF/QR proof;
- test1 retained-human-atom preservation result;
- final test1 archival backup/volume state;
- redirect proof;
- node1/node2 untouched status;
- any blockers/unexpected behavior.

If direct GitHub PR posting is unavailable, save the final DEPLOY/CUTOVER report locally for ChatGPT.

## Stop rule

After the full cutover and retirement verification, stop.

Do not begin new product work. Do not modify node1/node2. Do not delete archival test1 data. The goal is to end with:

```text
main @ c25c6f1320206742d7d94b52496bc6be0a2e12dd
        ↓
     punkto.xyz
        ↔
      node1
      node2

test1.punkto.xyz → permanent preserving redirect to punkto.xyz
standalone test1 runtime → retired
archival test1 data → preserved
```
