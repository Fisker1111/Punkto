# Codex Current Task

Status: **HOLD â€” Slice 4.5A implemented, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Goal

Implement **Pilot_1 Slice 4.5A — Spatial Reading**.

This is the first part of the Punkto spatial-placement program. The purpose is to make an existing atom's physical relationship to the ground immediately understandable before we implement direct-manipulation height placement.

Core product statement:

> **Every atom has a true ground anchor. Elevated atoms show a physical stem from that anchor to the message beacon.**

The user should be able to look at an elevated atom and understand, without reading a form or entering a mode:

> **That point on the ground is its real place, and the message is physically above it.**

This task is **reading/selection only**. Do not implement the 4.5B vertical-drag placement interaction yet. Do not start Slice 5.

## Starting state

Before editing:

1. Read `AGENTS.md`, `docs/PILOT_1_IMPLEMENTATION.md`, `pwa/ARCHITECTURE.md`, and the current `ui-map.js` / `ui-board.js` implementation.
2. Confirm branch is `pilot-1` and working tree is clean.
3. Preserve the Slice 3.6 ownership boundary:
   - `ui-map.js` owns MapLibre/deck.gl presentation and selection visuals;
   - `ui-board.js` owns the selected-atom board sheet;
   - `app.js` remains coordinator.
4. Preserve Slice 4 fast-create behavior exactly. No create-flow redesign in this task.
5. MapLibre remains the single authoritative camera/projection.

## Spatial grammar to implement

A real atom is still one protocol object. Ground anchor, stem, ring and beacon are visual representations only.

For an atom at physical height `h > 0`:

```text
        ●  beacon / message at real height
        │
        │  stem = physical height relation
        │
        ○  ground anchor at same lon/lat, height 0
```

For a ground-level atom (`h == 0`), the beacon and base visually collapse into one compact grounded object; do not create a fake visible stem.

### Ground anchor

- exact same longitude/latitude as the atom;
- always at ground height 0 in the Punkto map coordinate model;
- subtle in normal state;
- stronger when selected;
- should read as the atom's true place on Earth, not as a second atom.

### Stem

- exactly vertical;
- connects the ground anchor to the atom's actual physical height;
- visible for elevated atoms at useful local/near zooms;
- stronger when selected;
- no reply/order/popularity/time semantics may affect stem height.

### Beacon

- stays at the atom's real physical height;
- remains the primary message object;
- selected beacon receives stronger visual emphasis than ordinary beacons.

## Level of detail / calm-world rule

Do not turn the map into a forest of antennae.

Implement a restrained level-of-detail strategy using current MapLibre zoom and selection state. Exact thresholds may be chosen from current map behavior, but the result should approximately follow:

- **Far:** beacon only; no full stem forest.
- **Medium:** beacon + subtle ground relation/base.
- **Near:** beacon + ground base; elevated stems become legible.
- **Selected:** full ground anchor + stem + beacon + compact height label regardless of ordinary LOD where practical.

Selection must remain visually obvious without making unselected atoms noisy.

## Selected atom depth treatment

When an atom is selected on the Map:

- ground anchor/ring becomes clearly visible;
- stem brightens and remains thin;
- beacon becomes slightly larger/brighter than ordinary state;
- show a compact spatial label near the beacon or stem such as:
  - `Ground` for 0 m; or
  - `+12 m · ~Floor 4` for elevated atoms.
- floor estimate may use the existing `FLOOR_HEIGHT_M` convention only as an approximate display hint; do not persist or reinterpret protocol data.
- selected visual must remain anchored to the actual atom; no synthetic offset that changes geographic meaning.

The selected atom should be understandable even in a dense 3D-building area.

## Board / sidecar correction

The current selected board can open partially off-screen or dominate too much of the world on desktop. Fix this as part of 4.5A because selection should read as one spatial interaction.

### Desktop

- board becomes a contained spatial sidecar, approximately `400–440px` wide when viewport allows;
- board must stay fully inside the viewport;
- internal content scrolls instead of the panel extending off-screen;
- when opening the board, apply MapLibre map padding (right side) or an equivalent MapLibre-native viewport accommodation so the selected atom remains visible beside the board;
- preserve zoom, pitch and bearing;
- do not perform an unrelated fly-to or recenter jump;
- closing the board restores prior padding cleanly and leaves the user's spatial context intact.

### Mobile

- keep a bottom-sheet treatment;
- cap it so a useful part of the map remains visible above it (roughly 55–65% viewport height maximum);
- use internal scrolling for long board content;
- selected atom should remain visually connected to the world behind the sheet.

### Important camera rule

> **The world makes room for the board; the board does not move the world to a different place.**

Use the existing MapLibre camera. No second camera and no Three.js camera synchronization.

## Building behavior in this task

Do **not** implement full building x-ray / floor slicing yet. That belongs to 4.5C.

Allowed in 4.5A only if very small and clearly helpful:

- modest selected-atom visibility treatment if an existing building extrusion completely occludes the selected beacon.

Do not add custom 3D buildings, new tile providers, photogrammetry, interiors, or floor meshes in this task.

## Product invariants

Preserve all of these:

- one displayed beacon resolves to one real atom;
- independent atoms remain independent;
- physical height is the only meaning of the vertical axis;
- replies remain flat 2D board content;
- no likes/followers/engagement ranking;
- no protocol/storage/signing/sync/federation changes;
- no fake activity or synthetic atoms;
- MapLibre is the authoritative spatial context;
- public content remains public;
- Text view remains an equivalent/accessibility representation.

## Expected implementation scope

Prefer the smallest coherent set, likely:

- `pwa/ui-map.js`
- `pwa/ui-board.js`
- `pwa/index.html` for narrow board/layout CSS if needed
- `pwa/app.js` only for narrow cross-module board-padding coordination/version marker if necessary
- `pwa/ARCHITECTURE.md` only if the actual module API/ownership changes materially
- `docs/agent/CODEX_CURRENT_TASK.md`

A small helper in an existing UI/core module is acceptable if it avoids duplicated height/floor display logic.

Do **not** edit:

- relay/protocol formats;
- storage schema;
- signing/identity semantics;
- peer discovery/sync cadence;
- deployment/Caddy/Docker files;
- node1/node2 configuration;
- create behavior except for a strictly mechanical integration required to keep it unchanged.

## Version marker

This is visible product behavior. Update both the console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45a-spatial-reading-2026-08-23-1`

## Acceptance criteria

The task is acceptable only when all are true:

1. A ground-level atom visually reads as grounded and does not show a fake tall stem.
2. An elevated atom can show a true ground anchor and a vertical stem to its real physical height.
3. Stem height comes only from the atom's physical altitude/height field already used by Punkto.
4. Far/medium views remain calm; 4.5A does not create a dense forest of stems.
5. Selected atom gets a clearly stronger base/stem/beacon treatment.
6. Selected atom shows a compact, understandable height label (`Ground` or `+N m · ~Floor N`).
7. Selecting a real atom still opens the correct board/root semantics from Slice 3.
8. On desktop, the board is fully inside the viewport and uses internal scrolling when needed.
9. On desktop, board opening makes room using MapLibre-native padding/viewport handling while preserving zoom/pitch/bearing and the selected atom's geographic context.
10. Closing the board restores map padding/context without an unrelated camera jump.
11. On mobile, board remains a bottom sheet with useful map area visible above it.
12. Existing `Test atom` / real-atom rendering path remains valid.
13. Text view, fast create, signing, sync, storage, settings and federation behavior are unchanged.
14. No 4.5B vertical-drag placement interaction is implemented yet.
15. No 4.5C building floor/x-ray system is implemented yet.
16. Version marker is exactly `pilot1-slice45a-spatial-reading-2026-08-23-1`.
17. No deploy/ops files are changed.

## Automated checks

Run at minimum:

```bash
node --check pwa/app.js
node --check pwa/ui-shell.js
node --check pwa/ui-text.js
node --check pwa/ui-map.js
node --check pwa/ui-board.js
node --check pwa/ui-create.js
node --check pwa/ui-settings.js
node --check pwa/key-management.js
node --check pwa/sw.js
node --input-type=module --check < pwa/app.js
node --input-type=module --check < pwa/ui-map.js
node --input-type=module --check < pwa/ui-board.js
node --input-type=module --check < pwa/ui-create.js
python3 relay/test_relay.py
git diff --check
```

Do not modify relay files to influence relay test results.

## Focused browser / implementation checks

Where practical without creating new public atoms:

- verify a ground atom renders without a tall stem;
- verify an elevated fixture/local test object, if available without network writes, has base → stem → beacon geometry at the correct height;
- verify selected styling is stronger but restrained;
- verify selected spatial label uses height only;
- verify board is fully visible at common desktop viewport sizes;
- verify board content scrolls internally;
- verify board open/close does not alter zoom/pitch/bearing unexpectedly;
- verify mobile CSS still produces a bottom sheet with map visible above;
- verify no uncaught MapLibre/deck.gl/module errors;
- do not fabricate a new public network atom merely for testing.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5A implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`feat(pilot1): add spatial atom reading`

Then:

1. commit only Slice 4.5A implementation + task-status/doc changes;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, checks performed, and any UX uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 4.5B, Slice 4.5C, or Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI before any test1 deployment authorization.
