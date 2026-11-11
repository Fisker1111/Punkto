# CODEX TASK 63-B — addendum: the board-viewport `easeTo` cancels the camera `flyTo`

Repository: `Fisker1111/Punkto`
Branch: `feat/issue60-pwa-m8-ux` (HEAD is still `dfa29f1cbe753988300056ded01f7970cd400b22`
plus your uncommitted M8B work in the working tree)
Issue: https://github.com/Fisker1111/CEO-OS/issues/63

**Read first:** `docs/CODEX_TASK_63.md` (the normative M8B spec — this addendum is
normative and additive), `pwa/ui-map.js` (`setMapBoardViewport`),
`pwa/app.js` (`focusPunkto`), `pwa/ui-board.js` (`openMapBoardForAtom`,
`renderMapBoardSheet`).

This addendum is normative. If you believe any rule below is contradictory or
impossible, **stop and report** instead of silently choosing a different
design.

---

## 0. The defect Hermes reproduced in a real browser (read-only QA)

The founder-approved M8B flow is: pick a real published place → **the camera
flies to that place** → the existing board sheet opens for it.

Reproduced against the live read-only publication on a fresh profile with
geolocation denied (Chromium, map served from the branch with
`/publication` proxied read-only to `https://punkto.xyz`):

- Clicking the real place in the "Explore a real place" nudge **opens the
  correct board sheet** (exact address `s00000000000_0`, "Replies · 1", the
  genuine Null Island thread). That part works.
- But the **camera never leaves the default Copenhagen view**: the map stays
  at `center [12.5, 55.7], zoom 9` and never reaches the place.

Direct A/B proof in the same browser session:

```js
// A: flyTo alone — works
map.jumpTo({ center: [12.5, 55.7], zoom: 9 });
map.flyTo({ center: [0, 0], zoom: 16, duration: 1200 });
// -> after 4s: center [0, 0], zoom 16   ✔

// B: flyTo, then a viewport easeTo during the flight — the fly is cancelled
map.jumpTo({ center: [12.5, 55.7], zoom: 9 });
map.flyTo({ center: [0, 0], zoom: 16, duration: 1200 });
setTimeout(() => map.easeTo({
  padding: { top: 0, right: 0, bottom: 200, left: 0 },
  duration: 180, zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing(),
}), 100);
// -> after 0.6s and after 4.6s: center [12.5, 55.7], zoom 9   ✘ (camera never moved)
```

**Root cause.** `pwa/ui-map.js` `setMapBoardViewport()` calls
`map.easeTo({ padding, duration: 180, zoom: map.getZoom(), ... })` to give the
board sheet room. `easeTo` cancels any in-flight camera animation and animates
to the **current** camera position (which, 100 ms into the 1200 ms `flyTo`, is
still the old centre). The call order in the M8B flow is:

1. `focusPunkto(id)` → `focusPunktoOnMap(id)` → `map.flyTo({ center, zoom: 16, duration: 1200 })`
2. → `_onOpenMapBoardForAtom(atom, atoms)` → `openMapBoardForAtom()` →
   `renderMapBoardSheet()` → `setBoardViewport(true)` →
   `onBoardViewportChanged` → `setMapBoardViewport(true, rect)` → **`map.easeTo(...)`**

Step 2 therefore kills step 1.

Note this defect also affects the **pre-existing** M8 path (text feed → "Open
board" / `focusPunkto`), which is exactly why the board sheet currently opens
without the map ever going to the place. Fixing it here is in scope: the M8B
acceptance criterion is that selecting a place flies the camera to it and opens
the board.

---

## 1. Required fix (minimal, inside `pwa/ui-map.js` only)

`setMapBoardViewport()` must **never cancel an in-flight camera animation**.

Rules:

1. Keep the existing behaviour when the camera is **not** animating: apply the
   padding with the existing `map.easeTo({ padding, duration, pitch, bearing,
   zoom })` call, unchanged.
2. When the camera **is** animating (the `flyTo` from `focusPunktoOnMap` /
   `frameInitialExplorePlace`), **defer** the padding adjustment until the
   animation finishes, then apply it. Use the map instance's own API to detect
   motion (e.g. `map.isMoving()` when available) and to run the deferred apply
   (e.g. `map.once('moveend', apply)`).
3. If a deferred apply is still pending when a **new** `setMapBoardViewport()`
   call arrives, the **new** call replaces it: cancel/unsubscribe the old
   pending apply before registering the new one, so the padding is applied
   exactly once, with the latest values. Keep a module-level variable for the
   pending apply and unsubscribe it with the matching `map.off(...)` (or the
   equivalent the map instance supports) before setting a new one.
4. The `mapBoardBasePadding = null` reset on close, the
   `prefers-reduced-motion` handling, and every other existing behaviour of
   `setMapBoardViewport()` stay as they are.
5. Do not change the flight target: `focusPunktoOnMap()` keeps
   `flyTo({ center: [loc.lon, loc.lat], zoom: 16, duration: 1200 })`. The
   camera must end up **at the place** (for the Null Island place: the
   coordinates decoded from the exact address `s00000000000_0`, i.e. latitude
   and longitude ≈ 0, zoom 16).

Guard against a degenerate case: if the map instance is missing or has no
`isMoving`/`once`/`off` methods, fall back to today's behaviour (apply the
`easeTo` immediately) rather than throwing.

## 2. Required regression test

Extend `pwa/test-punkto-m8b-map-first.mjs` (do **not** create a second test
file) with a focused check of the deferral decision, without needing a real
MapLibre map.

To make the rule testable, export a small pure predicate from
`pwa/ui-map.js`, e.g.

```js
export function shouldDeferViewportPadding(mapLike) { /* boolean */ }
```

that returns `true` only when the map instance reports that it is currently
animating (i.e. `mapLike.isMoving()` is `true`), and `false` otherwise
(including when `isMoving` is missing or throws).

Add a check that:

- a fake map reporting `isMoving() === true` → deferral required,
- a fake map reporting `isMoving() === false` → no deferral,
- a fake map without `isMoving` → no deferral (safe fallback),
- a fake map whose `isMoving()` throws → no deferral (safe fallback),
- and the existing six M8B checks keep passing.

The test must remain a plain `node` script with no new dependency and no DOM.

## 3. Files you may touch

- `pwa/ui-map.js`
- `pwa/test-punkto-m8b-map-first.mjs`

Do not touch anything else. In particular **do not** change `pwa/app.js`,
`pwa/index.html`, `pwa/core/explore.js`, `pwa/ui-board.js` or the CI workflow
in this addendum — Hermes has already verified those and will re-verify them
after your change.

## 4. Definition of done

- Exactly these two files changed relative to your previous working tree state
  (plus your previous, already-uncommitted M8B work).
- `node --check pwa/ui-map.js` and
  `node --input-type=module --check < pwa/ui-map.js` pass.
- `node pwa/test-punkto-m8b-map-first.mjs` passes with the new check included
  (paste the exact output, including the final summary line and the new pass
  count).
- `node pwa/test-punkto-m8-ux.mjs` still passes (paste the exact output).
- Paste the exact `git diff` of your two files.
- State explicitly that you did **not** commit, push, merge, deploy, create a
  PR, or write to any remote host.
