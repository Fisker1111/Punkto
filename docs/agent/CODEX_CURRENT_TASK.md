# Codex Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C2: local height tool + placement-stage declutter**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Why this task exists

Human testing of deployed Slice 4.5C accepted the shell and the core spatial creation flow on both desktop and mobile.

The interaction philosophy is now locked and must not be redesigned:

> **Aim with the center sight → `+` locks x/y → choose height → Done → write → Publish.**

The remaining issue is specific and visual: during height placement, the height lever sits at the far-right edge of the viewport while the user's attention is on the atom near the center. The eye must search for the control, which weakens the direct-manipulation feeling.

The product decision is:

> **During height placement, the lever belongs to the atom.**

This is a narrow refinement task, not a new slice of product behavior.

## Starting state

Start from exact current `pilot-1` HEAD:

`0ef78e78a90fea060a085fd3920f4244baf1b3f4`

Read `AGENTS.md`, `pwa/ARCHITECTURE.md`, and current `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/index.html`, `pwa/app.js` before editing.

Preserve:
- current hero `+` shell from Slice 4.5C;
- center sight as horizontal placement truth;
- current 0–200 m height mapping, including finer 0–30 m control;
- exact draft lon/lat while height changes;
- ground anchor → stem → beacon grammar;
- building ghosting during height placement;
- `Done → Write` sequence;
- protocol/storage/signing/relay/federation behavior;
- board/Text/Settings/deep-link behavior.

## Required change A — position the height lever near the placed atom

The height lever must no longer be permanently docked at the far-right edge during active height placement.

### Desired behavior

During height-placement mode:

1. Project the locked draft atom / ground-anchor world coordinate into screen space using the authoritative MapLibre camera.
2. Position the floating lever locally near that projected placement, approximately **80–140 px to the right** when space allows.
3. If there is insufficient room on the right, automatically place it to the **left** of the projected placement.
4. Clamp the lever fully inside the usable viewport with sensible margins / safe-area insets.
5. Avoid covering the beacon, ground anchor, central height label, top height readout, or bottom `Cancel · Ground · Done` actions.
6. Reposition the lever when the viewport changes and when the camera changes during height placement.
7. Do not move the locked world coordinate to accommodate the lever. The world remains truth; the UI follows it.

The resulting mental model should be immediate:

> **this atom ↔ this height control**

rather than an atom in the center and an unrelated slider at the screen edge.

### Mobile behavior

On narrow portrait phones, local placement still applies, but practical ergonomics win:
- prefer the side with more available space;
- clamp so the handle remains easy to reach;
- never place it under browser/safe-area edges;
- never overlap `Done` actions;
- never force the lever directly on top of the atom because of insufficient room;
- if local placement cannot fit safely, use a deterministic nearest-safe fallback rather than returning to an arbitrary far edge.

## Required change B — visually associate lever with the atom

Use a restrained spatial association, not a new HUD system.

Allowed:
- shared accent/glow language;
- subtle short connector / guide line from lever toward the placement if it materially helps;
- matching visual emphasis between active beacon and lever handle.

Avoid:
- long heavy connector lines;
- CAD gizmos;
- arrows/XYZ language;
- large new panels;
- animation unrelated to actual height changes.

The map and beacon remain primary.

## Required change C — declutter height-placement mode

Human mobile testing showed unrelated controls still competing with the focused task.

While height placement is active:
- hide/suppress the normal MapLibre zoom `+ / −` controls;
- hide/suppress the normal `2D/3D` toggle if still visible;
- hide the onboarding instruction such as `Move the map, choose a place, then tap + to write a Punkti.`;
- hide normal shell/navigation as already intended;
- preserve attribution/legal text where required;
- preserve `Cancel`, `Ground`, and `Done` prominently.

All suppressed controls must restore immediately on Done or Cancel with no stuck state.

## Required change D — reduce duplicate height readout weight

The current large top `HEIGHT +N m · ~Floor N` panel and world-space height label repeat the same information.

Keep both only if useful, but make the top screen-space readout more compact and subordinate.

Requirements:
- `Ground` / `+N m · ~Floor N` remains immediately readable;
- world-space label stays close to the spatial object;
- top readout should function as confirmation, not dominate the map;
- do not remove accessible slider value / aria feedback;
- no semantic/data changes.

## Interaction invariants

Do not change these:

- `+` captures current center sight x/y;
- x/y remain fixed throughout height stage;
- lever changes only physical height;
- range remains 0–200 m;
- existing mapping/resolution stays unchanged unless necessary to fix a proven bug;
- Ground resets to 0;
- Done freezes placement and opens writing composer;
- Cancel writes nothing;
- building ghosting remains active during height placement and restores afterwards;
- no direct-beacon drag is reintroduced as a competing primary control;
- Z means physical height only.

## Architecture

Preferred ownership:
- `pwa/ui-map.js`: projection of draft placement into screen coordinates / camera events if needed;
- `pwa/ui-create.js`: height-stage lever DOM positioning/state;
- `pwa/index.html`: CSS for local positioning, compact readout, height-stage suppression classes;
- `pwa/app.js`: narrow coordination/version marker only if needed.

Prefer a clean callback/API over reading MapLibre internals directly from `ui-create.js`.

Do not introduce Three.js, a new renderer, new map provider, or new dependencies.

## Version marker

Update both console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45c2-local-height-tool-2026-08-29-1`

## Expected scope

Prefer only:
- `pwa/ui-map.js`
- `pwa/ui-create.js`
- `pwa/index.html`
- `pwa/app.js` for marker / narrow coordination
- `docs/agent/CODEX_CURRENT_TASK.md`

Touch architecture docs only if API ownership meaningfully changes.

Do not edit relay/protocol/storage/signing/sync/deployment/node configuration.

## Acceptance criteria

All must be true before committing:

1. Pressing `+` still enters the accepted height stage, not the write composer.
2. The locked draft lon/lat remains the exact pre-`+` center sight coordinate.
3. The height lever appears visually near the projected atom/ground anchor rather than permanently at the far-right edge.
4. Lever prefers roughly 80–140 px right of placement when safe and flips left when necessary.
5. Lever remains fully usable inside desktop and mobile viewports and respects safe areas.
6. Lever repositions appropriately after resize/orientation/camera movement during the height stage.
7. Lever never moves the world anchor; it follows the spatial placement.
8. Height mapping/range/resolution are unchanged: 0–200 m with current fine 0–30 m behavior.
9. Beacon/stem/ground anchor update continuously as today.
10. MapLibre zoom controls, 2D/3D toggle, onboarding hint, and unrelated shell chrome are hidden during height placement and restore on Done/Cancel.
11. Top height confirmation is visually more compact while remaining readable and accessible.
12. Building ghosting still works and restores.
13. `Done → Write → Publish` and Cancel semantics remain unchanged.
14. Hero `+` shell from Slice 4.5C remains unchanged outside placement mode.
15. Board, Text, Settings, deep links, storage, signing, relay/sync behavior remain unchanged.
16. Version marker is exactly `pilot1-slice45c2-local-height-tool-2026-08-29-1`.

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

Where practical without publishing another atom:

- desktop: aim at a clear point, press `+`, verify local lever sits beside placement rather than viewport edge;
- drag through Ground → ~3 m → ~10 m → ~30 m → ~100 m;
- verify anchor does not move and stem/beacon update;
- pan/rotate only if allowed outside lever drag and verify lever follows the projected placement;
- place near right viewport edge and confirm lever flips left;
- place near left viewport edge and confirm lever chooses safe side;
- mobile portrait around 390×844 and narrow ~360 px: verify lever is reachable, unclipped, and does not overlap bottom actions;
- verify normal zoom controls / 2D toggle / onboarding hint are absent during height stage and restored afterward;
- verify Done opens composer and Cancel returns to normal map with no stale CSS/state;
- verify no uncaught MapLibre/deck.gl/module errors.

Human visual/tactile acceptance on test1 remains required.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5C2 implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`fix(pilot1): attach height tool to placement`

Then:
1. commit only this task's implementation + task status change;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, automated checks, focused browser checks, and remaining uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI first.
