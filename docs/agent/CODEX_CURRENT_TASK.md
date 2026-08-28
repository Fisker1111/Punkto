# Codex Current Task

Status: **HOLD — Slice 4.5B2 implemented, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Why this task exists

Human test of deployed Slice 4.5B (`7ce1cba2a35eb263d8d605c59d3828ab93153550`) proved that direct height manipulation can work technically, but the creation workflow is visually cluttered because map placement, height manipulation, and message composition happen at the same time.

The next product decision is now locked:

> **The sight chooses place. The lever chooses height. The world shows both.**

Punkto already has a sight/crosshair at the center of the map. The user moves the map under that sight before pressing `+`.

The revised creation flow is:

> **Aim with the center sight → press `+` to lock x/y → choose physical height with a floating vertical lever while the atom is rendered in the 3D world → Done → write → Publish.**

Do not show the writing composer while the user is choosing height.

## Starting state

1. Start from current `pilot-1` HEAD.
2. Read `AGENTS.md`, `pwa/ARCHITECTURE.md`, and current `pwa/app.js`, `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/index.html` before editing.
3. Preserve MapLibre as the one authoritative spatial camera and deck.gl as the Punkto spatial overlay.
4. Preserve all protocol/storage/signing/relay/federation behavior exactly.
5. Preserve Slice 4.5A selected-atom reading + board behavior.
6. Preserve the existing spatial atom grammar: ground anchor + vertical stem + beacon head.
7. Preserve the current Pilot scalar height range: 0–200 m.

## Product invariant

The vertical axis means **physical height only**.

No reply ordering, age, popularity, urgency score, or any other semantic may enter Z.

A placed elevated Punkti must still be one real atom. The ground anchor and stem are visual support, not extra persisted atoms.

## Required workflow

### Stage 0 — aim before pressing `+`

The existing center sight/crosshair is the proposed horizontal position.

The user pans/rotates/zooms the map normally until the sight is over the desired point.

Do not add a separate `Use this place` confirmation before `+`.

### Stage 1 — pressing `+` locks x/y immediately

When the user presses `+`:

- close any open board as today;
- stay in Map context;
- capture the exact geographic coordinate under the existing center sight / MapLibre center at that moment;
- freeze this draft `lat/lon` for the height-placement stage;
- do not open the writing composer yet;
- enter an explicit height-placement mode.

The locked ground anchor must remain at that exact world coordinate even if the camera is subsequently pitched or adjusted.

### Stage 2 — height-placement mode

Height placement is a focused full-map interaction.

Required visual elements:

- the locked ground anchor at the chosen x/y;
- the draft beacon head at the current physical height;
- the vertical stem connecting ground anchor to beacon head;
- a compact height readout (`Ground`, `+3 m`, `+10 m · ~Floor 3`, etc.);
- a large touch-friendly **floating vertical lever / hoverbar** in screen space for choosing height;
- a clear `Done` action;
- a clear `Cancel` action;
- optional `Ground` reset if it improves usability.

Do not show the message textarea, category form, author field, public notice panel, or `Location & options` during this stage.

The height lever is the primary control. It must not look like a CAD XYZ gizmo.

Suggested interaction character:

- a vertical track with a large draggable handle;
- readable metre markings or labels appropriate to the current range;
- ordinary building heights (0–30 m) should be easy to control precisely;
- taller heights may accelerate / compress the scale if needed;
- dragging up increases height;
- dragging down decreases height;
- clamp at 0 m and 200 m;
- update the actual 3D beacon/stem continuously while dragging;
- do not require grabbing the small world-space beacon itself anymore;
- map gestures should remain available when the user is not actively dragging the lever, but the lever gesture itself must never pan/rotate the map.

The previous direct-beacon drag may be removed or disabled during create if it competes with this new primary interaction. Do not leave two equally prominent height interactions.

### Stage 3 — camera for spatial comprehension

Entering height-placement mode should make vertical height visually understandable.

If the current camera pitch is too flat to read Z, gently move to a useful oblique pitch (rough target around 55–65 degrees) while:

- preserving the locked ground coordinate;
- preserving zoom and bearing unless a tiny adjustment is technically required;
- not flying to another place;
- not producing a cinematic transition;
- respecting `prefers-reduced-motion` with instant/minimal movement.

The selected x/y must remain the spatial truth throughout.

When leaving height mode, do not create a disorienting camera jump. Preserve the world context for the writing stage and after publish.

## Buildings are part of the height proof

This is a core acceptance requirement, not optional decoration.

If the chosen x/y lies in/under a rendered building and the user chooses, for example, `+10 m`, the user must be able to perceive **both ends** of the spatial relation:

- the ground anchor at the bottom / ground relation;
- the beacon head at +10 m;
- the stem connecting them.

The building must not visually hide the relationship.

During active height-placement mode:

1. Prefer making only the building containing/intersecting the locked x/y translucent / ghosted when technically reliable with the current MapLibre building source/layer.
2. If selective per-building transparency is not reliable because the source lacks stable feature IDs or equivalent support, use the smallest safe fallback that still proves the relation (for example temporarily reducing opacity of the current 3D building layer during height placement).
3. Restore normal building opacity immediately when height placement ends or is cancelled.
4. Do not add architectural interiors, custom building meshes, photogrammetry, or a new 3D engine.
5. Do not fabricate floor truth. Approximate floor text must remain marked with `~` when derived from the existing floor-height assumption.

The acceptance test is visual:

> At +10 m inside a building, the human can still see/understand the ground anchor, the elevated beacon, and their vertical relationship.

## Stage 4 — `Done` opens the writing composer

When the user taps `Done` in height-placement mode:

- freeze `lat`, `lon`, and chosen height in the draft;
- exit the height lever UI;
- restore any temporarily ghosted building styling;
- open the existing write composer only now.

The writing composer should focus on writing, not spatial manipulation.

Show a compact placement summary near the top, e.g.:

- the Punkto/location identifier already used by the app;
- `Ground` or `+10 m · ~Floor 3`.

Keep:

- message textarea;
- category;
- public-data acknowledgement / emergency warning behavior;
- author/options fallback if still needed;
- Publish / Cancel.

But the primary spatial choice is already complete.

The old altitude slider/floor/device-altitude controls may remain under `Location & options` as accessibility/fallback controls, but they must not make the primary composer feel like a second height-placement UI. If those fallback controls change height, the stored draft and placement summary must stay synchronized.

### Cancel semantics

- `Cancel` during height placement abandons the draft and returns to normal Map with no atom persisted.
- `Cancel` during writing abandons the draft and returns to the Map with no atom persisted.
- no public/network write occurs until Publish.

## Preserve fast ground posting

Ground remains the default.

The flow for a normal ground post should be:

> **aim → `+` → `Done` → type → Publish**

Do not require a height confirmation beyond `Done`, do not force the user to move the lever, and do not request device altitude automatically.

## Data / persistence

Use the existing draft/publish data path and current Pilot height scalar. Do not change protocol/schema/storage/signing/network semantics.

The height chosen in Stage 2 must be exactly the height published by the existing atom creation path and later rendered by the same spatial grammar.

Do not create an extra ground atom or helper record.

## UI / visual constraints

- The map is the dominant surface during height placement.
- Height UI should be calm, minimal, touch-friendly, and readable over varied map backgrounds.
- Avoid large dark translucent composer panels during height placement.
- Avoid developer/GIS language such as X/Y/Z, transform, altitude datum, etc. in user-facing text.
- Prefer `Height` / `Ground` / metres / approximate floor language.
- Keep the existing nav identity and obvious `+` outside placement mode.
- During height placement, it is acceptable to suppress/disable unrelated nav controls if that prevents accidental mode changes, as long as Cancel is obvious.

## Architecture

Keep responsibilities clean:

- `ui-map.js`: map camera, spatial draft rendering, building ghosting, height placement visualization, world-space geometry.
- `ui-create.js`: create-flow state/UI including height-stage controls and write-stage controls.
- `app.js`: narrow coordination between create state and map state; no spatial implementation logic.
- `index.html`: containers/CSS only as needed.

If useful, expose explicit map APIs such as entering/updating/exiting placement mode rather than reaching into map internals from `ui-create.js`.

Do not add Three.js. Do not replace MapLibre/deck.gl.

## Version marker

Update both console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45b2-sight-height-lever-2026-08-28-1`

## Expected scope

Prefer only:

- `pwa/ui-map.js`
- `pwa/ui-create.js`
- `pwa/app.js`
- `pwa/index.html`
- `pwa/ARCHITECTURE.md` only if module ownership/API meaningfully changes
- `docs/agent/CODEX_CURRENT_TASK.md`

Do not edit relay/protocol/storage/signing/sync/deployment/node configuration.

## Acceptance criteria

All must be true before committing:

1. Before `+`, existing center sight remains the horizontal aiming device.
2. Pressing `+` locks the exact coordinate under that sight immediately.
3. Pressing `+` does **not** open the write composer; it opens focused height-placement mode.
4. Height-placement mode shows ground anchor + stem + beacon in the actual MapLibre/deck.gl world.
5. A large screen-space vertical lever is the obvious primary height control.
6. Moving the lever changes only physical height; draft lon/lat stay fixed.
7. Ground is default; range clamps 0–200 m; ordinary 0–30 m placement is controllable.
8. If needed, camera becomes gently oblique without changing the chosen place.
9. At +10 m in a rendered building, both ground anchor and elevated beacon/stem relationship remain visually understandable via building ghosting/transparency or the narrowest reliable fallback.
10. Building styling restores after Done/Cancel.
11. `Done` freezes position+height and only then opens the writing composer.
12. Composer shows a compact spatial summary but does not compete with an active 3D height-control UI.
13. Publish uses exactly the chosen lat/lon/height through the existing signing/posting path.
14. Cancel from either stage persists nothing.
15. Existing manual/floor/device controls, if retained, are secondary fallbacks and stay synchronized.
16. Existing selected atom board, Text view, Settings, relay/sync/storage/signing behavior remain unchanged.
17. No extra helper atom is persisted.
18. Version marker is exactly `pilot1-slice45b2-sight-height-lever-2026-08-28-1`.

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

## Focused browser checks

Where practical without publishing a public atom:

- move map so a recognizable ground/building point is under center sight;
- press `+` and verify write composer does not open;
- verify locked x/y remains fixed while adjusting camera/height;
- move lever Ground → ~3 m → ~10 m → ~20 m → Ground;
- verify stem/head update continuously;
- verify map does not pan under lever drag;
- verify containing/intersecting building does not hide both ends of the atom relation at ~10 m;
- press Done and verify write composer opens with the chosen spatial summary;
- cancel from write and verify no persisted atom;
- repeat and cancel directly from height stage;
- verify no stuck building opacity, map padding, gesture lock, or create state;
- verify no uncaught MapLibre/deck.gl/module errors.

The final gameplay feel remains a human gate after test1 staging.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5B2 implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`feat(pilot1): add sight-locked height lever flow`

Then:

1. commit only this task's implementation + task status change;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, automated checks, focused interaction checks, and any remaining uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 4.5C or Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI first.
