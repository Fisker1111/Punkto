# Codex Current Task

Status: **HOLD — Slice 4.5B implemented, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Goal

Implement **Pilot_1 Slice 4.5B — Direct Spatial Height Placement**.

This is the signature creation interaction for Punkto.

Core product statement:

> **Tap `+` → the geographic place is fixed → drag the atom upward only if height matters → type → publish.**

The user must not have to understand altitude forms, XYZ controls, CAD gizmos, or a separate 3D editor. The world itself is the height control.

Slice 4.5A already established the reading grammar:

```text
        ●  beacon / atom at physical height
        │
        │  vertical stem
        │
        ○  ground anchor at fixed lon/lat
```

Slice 4.5B makes the **draft beacon itself draggable vertically** during creation.

This task does **not** implement building translucency, floor slicing, indoor models, or custom 3D buildings. Those belong to 4.5C. Do not start Slice 5.

## Starting state

Before editing:

1. Read `AGENTS.md`, `docs/PILOT_1_IMPLEMENTATION.md`, `pwa/ARCHITECTURE.md`, and current `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/app.js`, `pwa/index.html`.
2. Confirm branch is `pilot-1` and working tree is clean.
3. Preserve Slice 4.5A spatial reading behavior and board sidecar behavior.
4. Preserve Slice 4 fast-create semantics: ground-level posting must remain fast and must not require height interaction.
5. MapLibre remains the single authoritative camera/projection; deck.gl remains the Punkto spatial overlay.
6. Do not change protocol, storage, signing, relay, federation, or node operations.

## The interaction to implement

### 1. Opening `+`

When the create flow opens on the Map:

- establish the draft ground anchor from the current create location exactly as the existing flow already does;
- initialize draft height to `0 m` unless an existing explicit draft value requires otherwise;
- render the 4.5A draft grammar immediately:
  - ground anchor at the chosen lon/lat;
  - draft beacon at current height;
  - vertical stem only when height > 0;
- show an obvious but restrained spatial affordance that communicates **the beacon can be dragged up/down to set height**.

Do not require a second "3D editor" screen.

Do not automatically request device altitude merely because `+` opened.

### 2. Direct vertical manipulation — the Punkto Move

The draft beacon is the handle.

When pointer/touch begins on the **draft beacon**:

- enter height-drag mode;
- freeze the geographic ground anchor (`lon/lat`) for the duration of the drag;
- disable conflicting map pan/rotate/zoom gestures while the drag is active;
- vertical pointer movement changes only physical draft height;
- horizontal pointer drift must not move the geographic anchor;
- update beacon, stem and height label live while dragging;
- on release/cancel, restore ordinary map interaction cleanly.

There must be **no XYZ arrows and no separate altitude slider as the primary interaction**.

### 3. Height mapping / feel

Prioritize intuitive human-building placement, not mathematical cleverness.

Requirements:

- upward screen drag increases height;
- downward screen drag decreases height;
- clamp at `0 m` minimum;
- use a conservative Pilot maximum around `200 m` to prevent runaway values;
- the `0–30 m` range must be easy to control precisely because ordinary floors/buildings matter most;
- a slightly accelerated response above ordinary building heights is acceptable if it improves usability;
- avoid large jumps from tiny finger movement;
- update on animation frames / smoothly enough to feel direct;
- choose the cleanest implementation compatible with current MapLibre/deck.gl architecture rather than hardcoding a brittle projection trick.

The mapping may be viewport-aware, but the interaction must remain monotonic and predictable.

### 4. Spatial label

During placement, show a compact label next to the draft beacon, for example:

- `Ground`
- `+3 m · ~Floor 1`
- `+9 m · ~Floor 3`
- `+12 m · ~Floor 4`

Use the same approximate floor convention as 4.5A. Floor is only a display hint; physical metres remain authoritative.

The label should follow the beacon and remain readable without obscuring the composer.

### 5. Ground remains the zero-friction default

A user who wants a normal ground-level public message must still be able to:

> **Tap `+` → type → Publish**

without touching the 3D placement control.

Do not insert a mandatory height-confirmation step.

At height 0, the draft reads as a compact grounded beacon/base. A small `Ground` cue is acceptable.

### 6. Composer coexistence

The create composer and spatial placement must work together rather than one replacing the other.

- message field remains obvious;
- category remains easy to reach;
- Publish remains the primary action;
- map area must remain large enough to manipulate the draft beacon;
- on mobile, do not let the composer cover the entire placement area;
- on desktop, avoid a giant centered modal that blocks the draft beacon;
- Cancel/close returns to the prior map context cleanly.

A narrow markup/CSS adjustment is allowed if needed to make the draft beacon directly manipulable while the composer is open.

Do not perform a broad visual redesign.

### 7. Manual / accessibility fallback

Preserve a non-gesture fallback under `Location & options`.

Existing ground/floor/manual/device-altitude controls may remain, but they are now secondary/fallback controls.

When fallback controls change height:

- the spatial draft beacon/stem/label must update immediately;
- when the beacon is dragged, the fallback value/readout must stay synchronized.

Do not remove accessibility or precision entry just because direct manipulation exists.

## Important interaction ownership

Keep module boundaries clear:

- `ui-map.js` owns spatial draft rendering and pointer/touch manipulation of the draft beacon;
- `ui-create.js` owns composer/form state and fallback controls;
- `app.js` coordinates draft state and publish orchestration only where necessary.

Prefer a small explicit callback/API between create and map modules over moving implementation back into `app.js`.

## Camera behavior

During a height drag:

- do not fly the camera to another location;
- do not silently alter the ground anchor;
- keep zoom/pitch/bearing stable;
- temporarily suppress only the map gestures that conflict with direct beacon dragging;
- restore map gestures after pointerup/pointercancel even if an error occurs.

If current pitch is too flat to make vertical placement understandable, a very small explicit placement-mode pitch assist is acceptable only if:

- it is deterministic;
- it preserves center/bearing/zoom meaning;
- it is not cinematic;
- it does not fire repeatedly while editing;
- closing create restores the user's prior camera state cleanly.

Prefer not to change camera automatically unless needed for usability.

## Building behavior

Do **not** implement 4.5C in this task.

Specifically do not add:

- translucent selected building;
- x-ray/cutaway rendering;
- floor planes or floor snapping based on building geometry;
- indoor rooms;
- new building providers;
- Three.js scene/camera.

The base → stem → beacon interaction must work beautifully even on empty terrain with no building data.

## Product invariants

Preserve all of these:

- one displayed beacon = one real atom;
- ground anchor is visual only, not a second persisted atom;
- vertical axis means physical height only;
- independent atoms remain independent;
- replies remain flat 2D board content;
- no engagement ranking or gamification;
- no protocol/storage/signing/sync/federation changes;
- no fake activity;
- MapLibre is the authoritative spatial context;
- Text view remains an equivalent/accessibility representation;
- ordinary ground posting remains fast.

## Version marker

Update both console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45b-direct-height-2026-08-23-1`

## Expected scope

Prefer the smallest coherent set, likely:

- `pwa/ui-map.js`
- `pwa/ui-create.js`
- `pwa/app.js` only for narrow draft-state/callback coordination + version marker
- `pwa/index.html` only for focused create-layout/placement affordance CSS/markup
- `pwa/ARCHITECTURE.md` only if module API/ownership changes materially
- `docs/agent/CODEX_CURRENT_TASK.md`

Touch another PWA file only if mechanically required.

Do **not** edit:

- relay/protocol files;
- storage schema;
- signing/key semantics;
- sync/federation behavior;
- deployment/Caddy/Docker configuration;
- node1/node2 configuration;
- Slice 5 field-hardening scope.

## Acceptance criteria

The task is acceptable only when all are true:

1. Opening `+` visibly presents a draft ground anchor/beacon in the Map world.
2. Ground posting remains valid without any height interaction.
3. The user can directly press/touch the draft beacon and drag upward to increase physical height.
4. Dragging down decreases height and cannot go below 0 m.
5. Geographic lon/lat remains fixed during height drag.
6. Conflicting MapLibre gestures are disabled only while dragging and restored afterward, including pointer cancellation/error paths.
7. The stem stretches live between ground anchor and draft beacon.
8. A live compact height label follows the draft (`Ground` / `+N m · ~Floor N`).
9. The 0–30 m range is controllable enough for ordinary building-floor placement; small finger movement does not create absurd jumps.
10. Height is conservatively capped around 200 m for Pilot_1.
11. Manual/floor/device-altitude fallback controls remain available and stay synchronized with the spatial draft.
12. Message/category/Publish flow remains simple; no mandatory separate height step is introduced.
13. Publish uses the selected draft physical height through the existing canonical signing/write/storage/network path.
14. Cancel/close restores ordinary map gestures and leaves no stuck drag state.
15. Slice 4.5A real-atom selection, board sidecar, LOD, Text view, Settings, sync, identity and federation remain unchanged.
16. No building x-ray/floor slicing is added.
17. Version marker is exactly `pilot1-slice45b-direct-height-2026-08-23-1`.
18. No deploy/ops files are changed.

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

Do not modify relay files to influence relay results.

## Focused interaction checks

Where practical in a local/static browser without publishing public network test atoms:

- open `+` and confirm draft starts at ground;
- drag draft beacon upward and verify live stem + label;
- drag back to ground and verify compact grounded state;
- verify lon/lat do not change while height is dragged;
- verify map does not pan/rotate under the finger during active beacon drag;
- verify map gestures work again immediately after release/cancel;
- verify fallback manual/floor controls and direct drag remain synchronized;
- verify Cancel/Escape leaves no stuck interaction state;
- verify composer remains usable on desktop and mobile viewport sizes;
- verify no uncaught MapLibre/deck.gl/module errors;
- do not publish a fabricated public atom merely to satisfy Codex testing.

The final interaction quality is a **human tactile gate** after exact-SHA test1 deployment. Code/CI success alone does not approve the feel of the gesture.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5B implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`feat(pilot1): add direct spatial height placement`

Then:

1. commit only Slice 4.5B implementation + task-status/doc changes;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, automated checks, interaction checks, and any UX uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 4.5C or Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI before test1 deployment authorization.
