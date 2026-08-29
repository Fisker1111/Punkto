# Codex Current Task

Status: **HOLD — Slice 4.5C3 implemented, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Why this task exists

Human testing of deployed Slice 4.5C2 accepted the local height lever direction, but exposed a visual regression:

> **When height selection starts / height is changed, the actual draft atom can disappear from view.**

In the human desktop screenshot at about `+23 m · ~Floor 8`, the ground sight and local lever are visible, but the yellow world-space draft beacon / stem relationship is not clearly visible. This breaks the core spatial promise of the placement step.

The lever is only a control. The atom is the thing being placed.

Locked rule:

> **During height placement, the user must always be able to see the ground anchor, the stem, and the actual draft beacon simultaneously whenever height > 0.**

Do not proceed to Slice 5 until this is fixed.

## Starting state

Start from exact current `pilot-1` HEAD:

`4bce1d71a21962398baf5e7b439405c76de7e18c`

The deployed application baseline is Slice 4.5C2 application SHA:

`169ff365edd9995354117d2bc02b1e976fa16dc6`

Read `AGENTS.md`, `pwa/ARCHITECTURE.md`, current `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/index.html`, and `pwa/app.js` before editing.

Preserve the accepted interaction exactly:

> **Aim → `+` locks x/y → choose physical height → Done → write → Publish.**

Preserve:
- local lever from 4.5C2;
- exact locked lon/lat;
- 0–200 m height mapping and fine 0–30 m behavior;
- building ghosting;
- hero `+` shell;
- `Done → Write`;
- protocol/storage/signing/relay/federation;
- board/Text/Settings/deep links.

## Primary requirement — the world-space draft must never disappear

During active height placement:

1. At `0 m`, show the ground anchor / draft beacon clearly at the locked place.
2. At any positive height, show all three clearly:
   - ground anchor at Earth;
   - stem from ground to selected physical height;
   - draft beacon at the top.
3. The lever handle must never be mistaken for or visually replace the world-space beacon.
4. The draft world object must remain visually legible over pale ground, roads, and ghosted buildings.
5. Published atoms must not be altered just to solve this draft-placement regression.

## Diagnose the actual cause before choosing the fix

Inspect the current MapLibre/deck.gl rendering and camera behavior rather than applying a blind CSS patch.

Likely areas to verify:
- draft scatter/stem layer depth ordering against MapLibre / fill-extrusion layers;
- whether the draft beacon/stem is being depth-occluded even when buildings are ghosted;
- camera pitch/zoom/frustum at ordinary zoom levels;
- deck overlay redraw/update timing when `altitude_m` changes;
- whether C2 projection/lever callbacks unintentionally affect the draft render;
- whether the top beacon visually collapses onto the ground anchor at lower zoom.

If depth ordering is the cause, prefer a focused solution such as dedicated draft-placement layers / render parameters so **only the active draft** can remain visually readable through the placement context. Do not make every published atom render permanently through all geometry.

If camera framing is the cause, use the smallest deterministic adjustment needed to keep both endpoints readable. Do not move the geographic anchor, do not perform cinematic camera movement, and do not continuously chase the lever.

## Spatial visibility / framing requirements

The user must be able to understand height at ordinary Pilot zooms.

- Ground → ~3 m: beacon may be close to anchor, but it must still read as the same object / selected height.
- ~10–30 m: top and bottom should be unmistakably distinct at normal street/district placement zoom.
- ~100–200 m: both endpoints should remain in the usable viewport where practical; if framing assistance is required, keep it calm and deterministic.
- The atom must not be hidden behind the lever, top readout, or bottom `Cancel · Ground · Done` bar.
- Lever positioning may respond to the actual visible draft object if that improves association, but the lever remains secondary.

Do not change the physical height value to make the visualization easier.

## 4.5C2 behavior to preserve

- lever remains local to the placement rather than docked at the far-right edge;
- lever flips side / clamps safely;
- zoom controls, 2D/3D toggle, onboarding hint, and unrelated shell are suppressed during placement;
- compact top height readout remains;
- all suppressed controls restore after Done/Cancel;
- building opacity restores correctly;
- no stale placement state after cancel.

## Visual priority

During height mode the hierarchy must be:

1. **world-space draft atom** — primary;
2. ground/stem relationship — primary spatial proof;
3. local lever — control for Z;
4. numeric height/floor label — confirmation;
5. Cancel / Ground / Done — workflow controls.

The lever must never become the visually dominant “atom”.

## Version marker

Update console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45c3-draft-visible-2026-08-29-1`

## Expected scope

Prefer only:
- `pwa/ui-map.js`
- `pwa/ui-create.js` only if lever avoidance/association needs adjustment
- `pwa/index.html` only for narrow presentation fixes
- `pwa/app.js` for version marker
- `docs/agent/CODEX_CURRENT_TASK.md`

Do not edit relay/protocol/storage/signing/sync/deployment/node configuration.
Do not start Slice 5.

## Acceptance criteria

All must be true before committing:

1. `+` still locks the exact current center sight x/y and opens height mode first.
2. At Ground, the draft placement remains visible.
3. At ~3 m, ~10 m, ~23 m, ~30 m, ~100 m, and ~200 m, the actual world-space draft beacon is visible and clearly separate from the lever handle.
4. For positive height, ground anchor + stem + top beacon are simultaneously understandable.
5. The world anchor never moves when height changes.
6. Building ghosting still permits reading top + bottom through/inside buildings.
7. Draft visibility is robust at both desktop and mobile portrait sizes.
8. Local lever remains near the placement and does not cover the beacon/stem/anchor.
9. Height mapping/range/resolution remain unchanged.
10. Done opens Write; Cancel writes nothing; controls/buildings restore correctly.
11. Published atom rendering semantics are not globally changed in a misleading way.
12. Board, Text, Settings, deep links, storage, signing, relay/sync remain unchanged.
13. Version marker is exactly `pilot1-slice45c3-draft-visible-2026-08-29-1`.

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

- desktop at a similar zoom/pitch to the human screenshot: press `+`, test Ground → 3 → 10 → 23 → 30 → 100 m and visually confirm the actual yellow world beacon remains present;
- verify stem and ground anchor remain visible with it;
- repeat over/inside a building with ghosting active;
- confirm lever remains local but never covers the world beacon;
- mobile portrait ~390×844 and narrow ~360 px: same basic visibility gate;
- Done → Write and Cancel restoration smoke test;
- no uncaught MapLibre/deck.gl/module errors.

Human visual acceptance on test1 remains required.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5C3 implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`fix(pilot1): keep placement atom visible`

Then:
1. commit only this fix + task status change;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, automated checks, browser checks, and any remaining visual uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI first.
