# Codex Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C4: keep the full vertical relation in frame**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Why this task exists

Human testing of deployed Slice 4.5C3 shows the regression is **not solved**.

At about `+66 m · ~Floor 22`, the user can see the locked ground sight and local height lever, but the actual world-space draft beacon and stem are not visible in the usable viewport. The C3 dedicated draft layers likely solved depth/occlusion, but the spatial object is still leaving the visible frame.

The screenshot strongly suggests a **camera/framing problem at elevated heights**, not merely a color or depth problem. C3 also introduced a minimum placement zoom, which may make high vertical separation worse.

Locked product rule:

> **Height selection is valid only if the user can continuously see the physical relationship: ground anchor → stem → top beacon.**

The lever is secondary. The world-space atom is primary.

Do not start Slice 5 until this is fixed and human-verified.

## Starting state

Start from exact current `pilot-1` HEAD:

`ce4b2eff021923be5da819bedcce06836d92e919`

Deployed application baseline under test:

`4c1de6ad4e41183d6bbefe0cbff943cad7e8a17e`

Read `AGENTS.md`, `pwa/ARCHITECTURE.md`, current `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/index.html`, and `pwa/app.js` before editing.

Preserve the accepted interaction exactly:

> **Aim → `+` locks x/y → choose physical height → Done → write → Publish.**

Preserve:
- exact locked lon/lat;
- 0–200 m physical height mapping and fine 0–30 m control;
- dedicated draft placement layers from C3;
- building ghosting;
- local lever concept;
- hero `+` shell;
- `Done → Write`;
- protocol/storage/signing/relay/federation;
- board/Text/Settings/deep links.

## Browser-console evidence from the failing C3 build

Human Firefox console from the exact deployed C3 marker `pilot1-slice45c3-draft-visible-2026-08-29-1` shows the app/map booting normally with no uncaught application/module exception around the failed height placement.

Observed warnings:
- Firefox/WebGL deprecation and texture warnings;
- many MapLibre `Image "..." could not be loaded` style/sprite warnings;
- source-map 404 for `maplibre-gl.js.map`;
- `deck: Missing character: · (183)` from the TextLayer glyph atlas;
- three opaque worker/blob warnings: `Expected value to be of type number, but found null instead.`

Treat the WebGL deprecations, missing basemap icons, source-map 404, and missing `·` glyph as **non-causal unless code evidence links them to the disappearing geometry**. The missing glyph can affect the height label text, not the ground/stem/beacon geometry.

Do inspect the `Expected value ... number ... null` warning if you can trace it cheaply to a placement/camera numeric value, but do not let an opaque worker warning distract from the reproducible visual evidence: the C3 world-space draft leaves the usable frame at higher height while the rest of the UI remains responsive.

The absence of an uncaught runtime exception strengthens the hypothesis that this is primarily camera/projection/framing behavior rather than a crashed render loop.

## Primary fix — frame both endpoints of the vertical relation

During active height placement, maintain a **safe placement viewport** in which both endpoints remain visible:

- ground anchor at `[lon, lat, 0]`;
- top beacon at `[lon, lat, selectedHeight]`;
- stem between them.

### Required behavior

1. At Ground, the locked placement is clearly visible.
2. At positive heights, the ground anchor, stem, and top beacon must remain simultaneously visible.
3. The top beacon must not leave the viewport above the top HUD/readout.
4. The ground anchor must not be pushed behind `Cancel · Ground · Done`.
5. The vertical relation must not be hidden under the lever.
6. Keep the geographic x/y fixed. Camera framing may change; the world coordinate must not.
7. Do not change the selected physical height to make framing easier.

## Diagnose and remove the C3 framing regression

Inspect `easeCameraForHeightPlacement()` and the C3 `HEIGHT_PLACEMENT_MIN_ZOOM` behavior first.

Do not assume “more zoom” is better. At an oblique pitch, zooming in can push an elevated top point far outside the screen.

If the C3 minimum zoom causes the problem, remove or replace it with a **height-aware framing policy**.

Preferred principle:

> **Fit the relation, not a hardcoded zoom.**

## Use actual screen-space endpoint projection

Where practical, project both the ground and elevated draft positions into screen space using the authoritative MapLibre/deck.gl camera state.

MapLibre remains the spatial authority. It is acceptable to use deck.gl `WebMercatorViewport` or the overlay viewport, provided it is derived from the same MapLibre center/zoom/pitch/bearing/viewport and treats Z as physical metres.

The map module should be able to reason about:

- ground screen point;
- top-beacon screen point;
- safe top boundary;
- safe bottom boundary;
- current lever/readout/action exclusion zones.

Do not approximate the top point by simply subtracting arbitrary CSS pixels from the ground point.

## Framing policy

Implement the smallest calm deterministic camera adjustment needed.

### Desired behavior

- `0–30 m`: usually preserve a close street/building view; only adjust if either endpoint approaches an exclusion boundary.
- `30–100 m`: gently zoom out and/or shift camera framing enough to keep both endpoints visible.
- `100–200 m`: continue to fit the complete vertical relation; wider framing is acceptable.
- no cinematic orbiting;
- no repeated oscillation/jitter while dragging;
- no camera fighting the lever;
- no changing bearing unless absolutely necessary;
- pitch can remain around the current useful oblique value, but may be reduced slightly if that is the cleanest way to fit the relation.

Prefer stable hysteresis / threshold behavior so tiny height changes do not cause constant camera movement.

### Safe viewport

Respect practical UI exclusion zones:

- compact top height readout / Punkto header area;
- bottom `Cancel · Ground · Done` actions;
- safe-area insets;
- local lever footprint.

Keep a modest margin around both endpoints rather than letting them sit exactly on the edge.

## Lever association — follow the visible atom, not merely the ground point

C2/C3 position the lever from the locked ground projection. At high height, this can visually separate the lever from the actual top beacon.

Refine the placement-screen callback/API so the create UI can receive enough information to position the lever relative to the **visible top beacon** when height > 0.

Preferred mental model:

> **top atom ↔ height lever**

Requirements:
- when height > 0, prefer placing the lever locally beside the top beacon or the visible relation midpoint if that avoids overlap;
- at Ground, use the ground point;
- flip/clamp as today;
- never cover the top beacon, ground anchor, or stem;
- do not move the world coordinate to accommodate the lever.

A short restrained connector is fine.

## Keep the C3 visibility treatment

Do not remove the focused C3 draft render behavior unless it is proven harmful.

Preserve:
- dedicated draft layers;
- active draft readable through ghosted buildings;
- draft world object visually distinct from lever handle;
- published atoms unchanged.

This task is primarily about **framing**, not re-styling the atom again.

## Version marker

Update console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45c4-relation-framing-2026-08-30-1`

## Expected scope

Prefer only:
- `pwa/ui-map.js`
- `pwa/ui-create.js` for top-beacon-aware lever positioning if needed
- `pwa/index.html` only for narrow exclusion/margin presentation changes
- `pwa/app.js` for version marker / narrow callback coordination
- `docs/agent/CODEX_CURRENT_TASK.md`

Do not edit relay/protocol/storage/signing/sync/deployment/node configuration.
Do not start Slice 5.

## Acceptance criteria

All must be true before committing:

1. `+` still locks the exact current center sight x/y and opens height mode first.
2. At Ground, the draft anchor/beacon is visible.
3. At ~3 m, ~10 m, ~23 m, ~30 m, ~66 m, ~100 m, and ~200 m, **ground anchor + stem + top beacon are simultaneously inside the usable viewport and understandable**.
4. At ~66 m, reproduce the human screenshot scenario and confirm the top atom no longer disappears above/outside the frame.
5. Camera adjustment is calm and deterministic, with no jitter while dragging.
6. The locked lon/lat never changes because of framing.
7. The selected physical height never changes because of framing.
8. Buildings remain ghosted during placement and restore afterward.
9. Dedicated draft visibility layers remain effective through building geometry.
10. Lever remains local and preferably follows the visible top beacon when height > 0; it does not hide the world-space atom.
11. Ground/height mapping/range/resolution remain unchanged.
12. Done opens Write; Cancel writes nothing; controls/buildings/camera UI state restore correctly.
13. Published atom rendering semantics remain unchanged.
14. Board, Text, Settings, deep links, storage, signing, relay/sync remain unchanged.
15. Version marker is exactly `pilot1-slice45c4-relation-framing-2026-08-30-1`.

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

- reproduce desktop placement around the same geometry/pitch as the human +66 m screenshot;
- Ground → 3 → 10 → 23 → 30 → 66 → 100 → 200 m;
- verify both endpoints and the stem remain inside the usable viewport at every step;
- verify the camera widens/frames only as needed and does not jitter while the lever moves;
- test inside/near a ghosted building;
- mobile portrait ~390×844 and narrow ~360 px: test Ground, ~10, ~30, ~66, ~100 m;
- verify lever remains associated with the visible atom and does not cover it;
- Done → Write and Cancel restoration smoke test;
- no uncaught MapLibre/deck.gl/module errors.

Human visual/tactile acceptance on test1 remains required.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5C4 implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`fix(pilot1): keep height relation in frame`

Then:
1. commit only this fix + task status change;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, automated checks, browser checks, and remaining visual uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI first.
