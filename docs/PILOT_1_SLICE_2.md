# Pilot_1 Slice 2 — Beacon + spatial selection

## Status

**Approved for implementation after Slice 1 staging.**

Slice 1 established the nearby-first shell. Slice 2 restores Punkto's spatial identity inside the production Pilot_1 architecture.

## Goal

Make the map read as **public messages living at exact places**, not as a generic map with chat bubbles.

The signature object is the **Punkto beacon**.

> **One beacon = one real atom at one exact real-world position.**

This slice takes the useful visual grammar from the historical `test1-atomcloud` prototype — luminous point, exact ground contact, vertical altitude relation, selected emphasis — but implements it inside the existing MapLibre/deck.gl spatial context.

Do **not** transplant the old independent Three.js camera/world.

## Product invariants

1. **Beacon means atom.** Every beacon resolves to one real atom.
2. **Exact anchor.** Horizontal position is the atom's canonical geographic location.
3. **Vertical means physical altitude only.** Never use height for replies, popularity, age, urgency, category, or activity.
4. **No fake altitude.** A ground-level atom must not be visually lifted several metres just to make it easier to see.
5. **Independent atoms stay independent.** Do not merge same-place atoms into a fabricated combined story.
6. **MapLibre remains the authoritative camera/projection.** Deck.gl may render beacon geometry in that context.
7. **Message text does not float permanently in the world.** Message content belongs to selection/board UI, not large always-visible chat bubbles.

## Visual target

At street/neighborhood zoom the user should see geography first, then luminous Punkto objects attached to it.

A beacon consists of three semantic parts:

### A. Atom point

- small luminous orb/seed/dot at the atom's **true altitude**
- category may affect color
- glow/halo may make it legible against the map
- it must remain visually stronger than ordinary map POIs without becoming huge

### B. Ground contact

- subtle ring/disc at the atom's exact ground anchor (`z = 0`)
- visually communicates "this belongs here"
- selected state may enlarge/brighten this ring
- ring is not an extra atom

### C. Altitude stem

- only meaningful when physical altitude is above ground
- thin line from ground contact to the atom point
- stem height equals the atom's real altitude
- no minimum fake display altitude
- ground-level atom has no misleading elevated stem

The old AtomCloud experiment used a minimum display altitude for visibility. **Do not copy that behavior into Pilot_1.** Pilot_1's Z-axis is semantic truth.

## What to reuse conceptually from AtomCloud

The historical `test1-atomcloud/pwa/ui-cloud.js` is reference material for:

- emissive/luminous atom treatment
- subtle ground ring/disc
- dashed or restrained vertical stem
- stronger selected state
- category color continuity across point/stem/ring

Do not reuse its:

- independent Three.js camera
- raster-map floor
- custom orbit controls
- fake minimum display altitude
- fit-to-all-atoms camera behavior
- separate scene/HUD system

## Existing Pilot_1 architecture to use

The current `pwa/app.js` already has useful primitives:

- MapLibre map/camera
- deck.gl `ScatterplotLayer`
- deck.gl `LineLayer` for altitude lollipops
- canonical atom location/altitude data
- category colors
- focus/deep-link state

Prefer evolving these primitives over adding a new renderer.

## Required changes

### 1. Remove large permanent world chat bubbles as the primary map representation

The current DOM `.atom-bubble` cards make the scene read like a map with floating labels.

For Pilot_1 street view:

- do not permanently render full message cards over every atom
- beacon is the primary world object
- message text appears through selection/board behavior, not as the normal world layer

It is acceptable to retain the old bubble code temporarily behind a disabled path if removing it cleanly would create unnecessary risk, but it must not be the normal Pilot_1 map presentation.

### 2. Render a semantic beacon for every real atom

Use deck.gl layers or another lightweight MapLibre-aligned mechanism.

Suggested composition:

- **ground halo/ring layer** at `[lon, lat, 0]`
- **altitude stem layer** from `[lon, lat, 0]` to `[lon, lat, alt]` when `alt > 0`
- **atom point/halo layer** at `[lon, lat, alt]`

The exact deck.gl layer choice is implementation detail. Keep it simple and performant.

### 3. Selected state

Tapping/picking a beacon must create an unmistakable selected state while preserving the atom's exact anchor.

Selected state should use some combination of:

- brighter/larger atom point
- stronger ground ring
- stronger stem
- restrained pulse/glow

Do not move the point away from its real position.

Selection must be deterministic and tied to a real atom id/punkto.

### 4. Selection interaction for this transitional slice

Slice 3 owns the final bottom-sheet board treatment.

For Slice 2:

- selecting a beacon may use the existing lightweight popup/read path as a temporary detail surface
- do not build the final board in this slice
- do not force permanent message cards into the world
- preserve deep-link focus behavior

If the current popup/open behavior needs a minimal change so the selected beacon remains visibly selected while its temporary detail UI is open, make only that minimal change and report it.

### 5. Same-place atoms

Do not collapse independent atoms into one synthetic beacon.

If multiple atoms share an exact `punkto`, they may visually overlap in this slice. That is preferable to inventing a merged object.

A small count/concentration treatment may remain only if it is clearly a **view aggregation** and still lets the user resolve to real underlying atoms. Do not make this a large subproject in Slice 2.

### 6. Urgent category

Do not redesign urgency protocol here.

Existing warning/emergency category colors may continue. If easy, use a redundant simple shape/outline distinction for emergency without creating a new semantic system. Full urgency validation remains later Pilot work.

### 7. Keep the basemap subordinate

The current recognizable basemap/building extrusion remains valuable.

Do not replace it with a custom black floor or AtomCloud raster plane.

Beacon contrast should be tuned so the map remains readable but does not visually dominate Punkto objects.

## Performance / accessibility

- no new heavy rendering dependency
- no custom global assets
- no Three.js import for the production path
- reduced motion: selected pulse may become static emphasis
- beacon identity/location/altitude must remain understandable without animation
- color must not be the only urgent-state signal if emergency distinction is touched

## Scope exclusions

Do **not** implement in Slice 2:

- final bottom-sheet board
- reply UX redesign
- create-flow changes
- relay/protocol changes
- semantic zoom/world Flow
- global clustering architecture
- custom tile pipeline
- independent Three.js world
- media/profile/social features
- production node deployment

## Version marker

Bump the existing marker to:

`pilot1-slice2-beacon-2026-08-19-1`

or the next equivalent repository-convention marker.

## Required automated checks

Run at minimum:

```bash
node --check pwa/app.js
node --check pwa/ui-shell.js
node --check pwa/ui-text.js
node --check pwa/ui-map.js
node --check pwa/ui-create.js
node --check pwa/key-management.js
node --check pwa/sw.js
python3 relay/test_relay.py
```

The two known relay baseline failures may be reported as unchanged if they remain byte-for-byte/same-test failures and no relay files were touched.

## Required manual verification before staging approval

1. fresh open still lands on nearby Map
2. recognizable basemap/buildings remain visible
3. large permanent chat bubbles are no longer the default world representation
4. one ground-level atom reads as a beacon attached to the exact place
5. one elevated atom visibly has point at true altitude + ground contact + stem
6. ground atom does **not** appear artificially elevated
7. selecting a beacon visibly strengthens that same beacon
8. selected atom resolves to real message/detail content
9. same-place independent atoms are not silently fused into fabricated content
10. Text still shows the same underlying atoms
11. `+` and Settings unchanged
12. `/p/<id>` still focuses the correct real atom
13. empty-map hint still behaves correctly
14. map pan/zoom remains smooth on the available test device/browser

## Implementation ownership

Expected primary changes are likely in:

- `pwa/app.js`
- `pwa/index.html` (remove/disable old bubble styling and add only minimal beacon-related UI if needed)

Do not create a new production `ui-cloud.js` path unless a concrete blocker proves the existing MapLibre/deck.gl path cannot satisfy the contract.

## Commit / handoff

Make one focused Slice 2 implementation commit on `pilot-1` and push it.

Suggested commit message:

`feat(pilot1): add invariant spatial beacons`

Then stop. **Do not deploy automatically.**

Report:

- exact SHA
- files changed
- renderer/layer composition used
- how altitude truth is preserved
- how selected state works
- what happened to the old DOM chat bubbles
- automated checks
- manual verification
- any deviations or unresolved visual questions
- whether the commit is ready for review/staging
