# Codex Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5B review fix: make the height interaction visible and reachable**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Context

Slice 4.5B implementation commit `a9b58bf49341e31eb536d4038fdef65f4b5782fc` is **not approved for deployment yet**.

Pilot CI run #68 is green, and the direct pointer-drag machinery is structurally sound, but product review found two acceptance blockers before test1 staging:

1. The draft atom is created at the current MapLibre center while the create composer is still a bottom sheet. On common mobile/desktop viewport heights, the sheet can cover the map center, so the draft beacon/handle can be hidden or difficult to reach.
2. Before the first drag, there is no sufficiently obvious touch affordance explaining that the draft beacon itself is the height control. A yellow `Ground` label alone is not enough for a first-time user to discover the signature interaction.

The product requirement remains:

> **Tap `+` → see the draft atom in the world → grab it → drag up/down to set physical height → type → publish.**

Do not redesign the gesture. Fix the discoverability and viewport relationship around the already implemented gesture.

## Starting state

1. Start from current `pilot-1` HEAD and keep the existing Slice 4.5B direct-height code unless a small correction is required.
2. Read `AGENTS.md`, `pwa/ARCHITECTURE.md`, and current `pwa/app.js`, `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/index.html`.
3. Preserve MapLibre as the one authoritative camera and deck.gl as the spatial overlay.
4. Preserve protocol/storage/signing/relay/federation behavior exactly.
5. Preserve Slice 4.5A selected-atom reading + board sidecar behavior.

## Required fix A — the draft handle must remain visible and reachable

When `+` opens, the map must make visual room for the create composer so the fixed geographic anchor/draft beacon is visible in exposed map space rather than potentially sitting underneath the sheet.

Implement this with MapLibre-native viewport padding or an equivalent camera-safe approach.

Requirements:

- use the actual open composer rectangle/height rather than a brittle hard-coded phone height where practical;
- mobile bottom sheet should move the effective map center upward enough that the draft beacon at the current geographic center remains visible above the composer;
- desktop must likewise keep the draft beacon reachable and not buried behind the composer;
- preserve geographic center meaning, zoom, pitch and bearing;
- do not fly to another location;
- opening create may animate only very briefly/subtly, or instantly under reduced motion;
- closing/canceling create restores the prior map padding/context cleanly;
- changing first-use acknowledgement visibility or opening `Location & options` must not strand the draft handle behind the composer; if the composer height materially changes, recompute/reapply placement viewport accommodation;
- resize/orientation change must not leave stale padding;
- do not interfere with the existing board-sidecar padding because board is closed before create opens.

Prefer a small explicit API such as `setMapCreateViewport(open, composerRect)` owned by `ui-map.js`, with `ui-create.js` reporting the open composer rectangle through a callback coordinated by `app.js`.

Do not move spatial/camera implementation into `app.js`.

## Required fix B — obvious pre-drag affordance

A first-time user must understand that the draft beacon itself can be moved vertically **without opening Location & options**.

Add a restrained spatial affordance visible in the map world while create is open.

Examples of acceptable treatment:

- draft label: `Ground · drag ↕`
- elevated draft label: `+12 m · ~Floor 4 · drag ↕`
- or a compact two-line map label such as `Ground` / `↕ Drag height`

Use whichever is clearest with the existing deck.gl `TextLayer` and current visual language.

Requirements:

- the hint must be attached visually to the draft beacon, not buried in a settings form;
- it must work on touch (do not rely on cursor change/hover);
- keep it calm and compact;
- once dragging starts, height feedback must remain primary and live;
- do not add XYZ gizmos or a separate altitude slider as the primary interaction;
- existing numeric/floor/device controls remain fallback only.

## Preserve the existing direct drag behavior

Keep these behaviors from `a9b58bf...`:

- pointer/touch begins on the draft beacon;
- lon/lat remain fixed during drag;
- upward drag increases height, downward drag decreases it;
- min 0 m, max 200 m;
- 0–30 m remains precise enough for ordinary floors;
- map gestures are disabled only during active drag and restored on pointerup/pointercancel/close;
- live beacon/stem/height label updates;
- fallback controls and direct drag remain synchronized;
- ground posting remains `+ → type → Publish` with no mandatory height step.

## Version marker

Update both the console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45b-direct-height-2026-08-23-2`

## Expected scope

Prefer only:

- `pwa/ui-map.js`
- `pwa/ui-create.js`
- `pwa/app.js` for narrow callback coordination/version marker
- `pwa/index.html` only if focused layout/CSS is needed
- `docs/agent/CODEX_CURRENT_TASK.md`

Touch `pwa/ARCHITECTURE.md` only if the module API/ownership meaningfully changes.

Do **not** edit relay/protocol/storage/signing/sync/deployment/node configuration.

## Acceptance criteria

The review fix is acceptable only when all are true:

1. Opening `+` on a typical mobile viewport leaves the draft ground beacon visibly reachable above the composer.
2. Opening `+` on desktop leaves the draft beacon visibly reachable and the composer does not bury it.
3. The map keeps the same geographic anchor, zoom, pitch and bearing meaning while making room for the composer.
4. Closing/canceling create restores prior map viewport padding/context.
5. Composer height changes and resize/orientation do not leave the draft beacon hidden behind the sheet.
6. A first-time user gets an obvious touch-visible `drag height` affordance attached to the draft beacon before interacting.
7. Direct vertical drag still works and remains synchronized with fallback altitude controls.
8. Map gestures still restore correctly after release/cancel/close.
9. Ground posting remains zero-friction.
10. Slice 4.5A board/selection behavior and all network/storage/signing behavior remain unchanged.
11. Version marker is exactly `pilot1-slice45b-direct-height-2026-08-23-2`.
12. No deploy/ops files are changed.

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

Where practical without publishing public atoms:

- mobile-sized viewport: `+` leaves draft beacon visible and reachable above composer;
- desktop-sized viewport: same;
- first-use acknowledgement visible/hidden state does not bury the beacon;
- opening/closing `Location & options` does not bury the beacon;
- drag beacon to about +3 m, +9 m, +12 m and back to Ground;
- lon/lat stay fixed;
- map does not pan/rotate during drag and resumes immediately after;
- close/cancel restores viewport and gestures;
- no uncaught MapLibre/deck.gl/module errors.

The tactile feel remains a human gate after test1 deployment.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5B visibility fix implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`fix(pilot1): keep spatial height placement visible`

Then:

1. commit only this review fix + task status change;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, automated checks, focused interaction checks, and any remaining uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 4.5C or Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI first.