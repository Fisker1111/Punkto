# AZ Current Task

Status: **ACTIVE — deploy final Slice 5 glowing-orb polish to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Mission

Deploy the reviewed final Slice 5 visual polish to **test1 only** for one last human visual acceptance check.

Deploy exactly this application SHA:

`6cd203c87de49d9322dae590b56fa8fee429c4c4`

Commit:

`fix(pilot1): render hovering atoms as glowing orbs`

Pilot CI:

- Run: `34972455907`
- Number: `#169`
- Result: **green**
- PWA validation: PASS
- Slice 5 deterministic helper tests: PASS
- Relay regression suite: PASS

## Scope of this change

This is visual-only map rendering polish. Hovering atom markers should now read as small glowing spherical **orbs** rather than flat discs, while preserving:

- category/atom color identity;
- yellow placement draft identity;
- ground anchor/ring;
- vertical stem and physical-altitude meaning;
- selection/click behavior;
- accepted creation flow: Aim → `+` → choose height → Done → Write → Publish;
- existing camera/placement behavior.

No protocol, signing, identity, board/reply, PDF/QR, relay, federation, or server behavior is intentionally changed.

## Critical deployment rule

**Do not deploy the moving `pilot-1` branch tip.** This task-file activation advances the branch after the application commit. Deploy only `pwa/` from exact SHA `6cd203c87de49d9322dae590b56fa8fee429c4c4` using the same exact-SHA/Git-object deployment discipline as prior test1 releases.

## Before deploy

1. Confirm test1 currently serves the accepted Slice 5 RC (`cbdf113359443e293f1d478396becc0ed0ca40cc`) and relay health is OK.
2. Back up the currently served test1 PWA to a timestamped rollback directory.
3. Preserve relay data, node identity, federation configuration, persistent volume, and all human-created atoms.
4. Do not touch node1 or node2.

## Deploy

Replace only the test1 static PWA with `pwa/` from exact SHA `6cd203c87de49d9322dae590b56fa8fee429c4c4`.

No product-code edits. No production/main deployment.

## Required verification

After deployment:

1. Byte/hash-verify served `ui-map.js` against exact SHA `6cd203c87de49d9322dae590b56fa8fee429c4c4`; also confirm normal core files still match that exact application SHA.
2. Confirm the app boots without uncaught module/runtime errors.
3. In a real WebGL-capable browser if available, verify:
   - ordinary hovering atoms visually read as glowing spherical orbs, not flat circles;
   - orb category colors remain recognizable;
   - elevated atoms retain their vertical stems and ground anchors;
   - selected atom remains readable/clickable;
   - height-placement draft remains visible as a yellow glowing orb;
   - height lever and accepted placement flow remain unchanged;
   - no camera zoom/framing behavior was reintroduced.
4. Smoke-check existing board/Text/Settings/create/cancel behavior without fabricating public data.
5. Confirm test1 relay remains healthy and existing human atoms remain present.
6. Confirm node1/node2 are untouched.

If your browser environment cannot provide WebGL visual proof, state that limitation explicitly and leave final visual acceptance to the human.

## Report

Report exact deployed SHA, rollback path, served-file hash proof, browser/runtime result, relay/data health, and node1/node2 status. If direct PR posting is unavailable, save the DEPLOY block locally.

## Stop rule

After test1 verification, stop and set/consider this task complete. Do not merge PR #110, deploy main/punkto.xyz, retire test1, or start Slice 6. Human visual acceptance is the final gate.
