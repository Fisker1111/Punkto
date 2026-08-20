# Codex Current Task

Status: **ACTIVE — Pilot_1 Slice 3.6: PWA module boundary cleanup**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Goal

Refactor the proven Pilot_1 Slice 1–3 frontend so `pwa/app.js` returns to its intended role as the app coordinator rather than continuing to accumulate Map and board implementation detail.

This is a **behavior-preserving architecture slice**.

> No new product behavior. No visual redesign. No protocol/storage/sync changes. Move existing proven behavior behind clearer module boundaries so later Pilot work can iterate safely.

The desired direction is already documented in `pwa/ARCHITECTURE.md`: UI modules own UI surfaces/interaction, core/storage/sync modules keep their existing responsibilities, and `app.js` coordinates data/lifecycle across them.

## Starting state

Before editing:

1. Read `AGENTS.md`, `docs/PILOT_1_IMPLEMENTATION.md`, and `pwa/ARCHITECTURE.md`.
2. Confirm the working tree is clean and branch is `pilot-1`.
3. Inspect the current Slice 3 implementation in `pwa/app.js`, `pwa/ui-map.js`, and `pwa/ui-text.js` before moving code.
4. Preserve all current Slice 1–3 semantics exactly.
5. Do not touch test1/node1/node2 operations. Slice 3.5 is an ops/federation state, not a product-code dependency for this refactor.

## Architecture target

### `pwa/app.js` — coordinator

After this slice, `app.js` should primarily:

- boot and wire modules;
- own cross-layer lifecycle/state that genuinely spans storage, sync, create, settings, Text and Map;
- obtain/store atom data and pass display-ready data into UI modules;
- coordinate callbacks between modules;
- retain protocol/network/storage orchestration already assigned to it.

It should **not** remain the main home for board-sheet DOM/event behavior or low-level MapLibre/deck.gl layer construction.

### `pwa/ui-map.js` — real map UI ownership

Expand `ui-map.js` from its current thin wrapper into the owner of Map presentation concerns that are currently in `app.js`, using explicit dependency injection/callbacks where app-level services are needed.

Prefer moving, where practical and low-risk:

- MapLibre/deck.gl initialization and map instance lifecycle;
- map show/resize handling;
- beacon/ground-ring/halo/stem layer construction;
- selected-beacon visual state;
- map click/tap delegation for exact real-atom selection;
- map-only focus/fly-to presentation behavior;
- map-only rendering state such as deck overlay / map loaded state / visual selection state.

The module may accept callbacks/helpers from `app.js` for things that remain cross-layer, such as obtaining atoms, stable atom IDs, opening a board, geolocation/create placement coordination, or notifying app state.

**MapLibre remains the single authoritative camera. Do not introduce another renderer/camera.**

### `pwa/ui-board.js` — selected map board ownership

Create `pwa/ui-board.js` if it remains the cleanest boundary.

It should own the selected-map-board UI behavior introduced in Slice 3, including as much of the following as can be cleanly isolated without changing behavior:

- selected board atom / board atom list / reply-status / reply-draft UI state;
- opening/closing/re-rendering `#map-board-sheet`;
- board click delegation (`close`, `copy link`, `show in 3D`);
- board reply form event handling;
- deterministic cleanup when navigating away;
- reuse of `resolveBoardAtom()` / `renderBoardSheetHtml()` from `ui-text.js` rather than duplicating thread semantics.

Cross-layer actions such as actually submitting a reply, refreshing stored atoms, focusing the map, or calculating a stable atom identity should be supplied as callbacks from `app.js`/`ui-map.js` rather than reimplemented.

### `pwa/ui-text.js`

Keep Text/thread semantics centralized here:

- root/reply resolution;
- chronological 2D replies;
- imported-source presentation;
- shared board/thread markup helpers.

Do not split thread semantics into incompatible Text-vs-Map models.

## Product invariants — must remain unchanged

- Every displayed beacon resolves to one real atom.
- Independent atoms remain independent; never merge same-place atoms into a synthetic story/board.
- Selected visual state remains exact enough that same-place/same-punkto atoms do not all become selected together.
- Selecting a reply resolves to its real root board when the root is available.
- Root is primary; replies remain chronological/sequential 2D content.
- The Z-axis still means **physical altitude only**.
- MapLibre remains the only authoritative map/camera.
- Imported-source treatment remains intact.
- `Text | Map | + | Settings` behavior remains intact.
- `+` remains obvious and usable.
- Closing a board returns to the same map context.
- Old permanent DOM chat bubbles remain disabled.
- No fake atoms, aggregates, popularity/ranking semantics, or visual redesign.

## Refactor rules

1. **Move, do not redesign.** Prefer mechanical extraction plus narrow interfaces.
2. Avoid creating a generic framework/state-management system. Vanilla ES modules are enough.
3. Avoid circular imports. Prefer callbacks/dependency injection from `app.js` into UI modules.
4. Keep public/module APIs small and explicit.
5. Do not duplicate existing logic just to move it later.
6. Do not change storage schema, relay protocol, network endpoints, sync cadence, signing, atom identity semantics, or create-flow product behavior.
7. Do not change CSS/markup unless a tiny non-visual adjustment is strictly required by the extraction.
8. Update `pwa/ARCHITECTURE.md` so it describes the **actual post-refactor ownership**, especially `ui-map.js` and `ui-board.js`.

## Expected scope

Expected files:

- `pwa/app.js`
- `pwa/ui-map.js`
- `pwa/ui-text.js` only if a small shared export/interface adjustment is needed
- new `pwa/ui-board.js`
- `pwa/ARCHITECTURE.md`
- `docs/agent/CODEX_CURRENT_TASK.md`

Only touch `pwa/index.html`, `pwa/ui-shell.js`, or another PWA file if the refactor cannot be completed safely without a small mechanical change. Do not broaden scope into product work.

## Acceptance criteria

The refactor is acceptable when all of the following hold:

1. `app.js` is materially slimmer and no longer owns the board-sheet DOM/event implementation.
2. `ui-map.js` owns substantially more of the actual MapLibre/deck.gl presentation instead of being only a thin wrapper.
3. Map board behavior is isolated behind `ui-board.js` (or an equally clear dedicated module if you find a better minimal boundary).
4. No duplicate root/reply/thread model is introduced; map board reuses `ui-text.js` semantics.
5. Root beacon selection still selects exactly one real atom.
6. Reply/deep-link root resolution behavior remains unchanged.
7. Selected beacon styling, altitude stems, imported-source colors/treatment, and map camera behavior remain unchanged.
8. Board open/close, reply form, copy link, Show in 3D, Escape, Text/Map/+ /Settings cleanup remain unchanged.
9. Create flow, sync, storage, settings and key behavior remain unchanged.
10. `pwa/ARCHITECTURE.md` accurately documents the resulting boundaries.
11. No new feature or visual behavior is introduced.
12. No deployment or ops files are changed.

## Automated checks

Run:

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
python3 relay/test_relay.py

git diff --check
```

Also parse the final `pwa/app.js` and the new/changed ES modules as ES modules using the same approach as `.github/workflows/pilot-ci.yml` or an equivalent local module parse check.

Do not modify relay files to influence the relay result. Report the exact relay test result.

## Manual/local parity checks where practical

Serve the final PWA tree locally and verify there are no uncaught module/runtime errors. If usable local atoms exist, verify:

- Map opens and renders beacons;
- exact beacon selection still opens the same bottom-sheet board;
- close keeps the map context;
- navigation clears stale board state;
- `+` still opens create;
- Text still renders the same atoms/boards.

If no real local atoms are available, report that honestly. Do not fabricate data just to satisfy this refactor check.

## Commit / push contract

Make one focused implementation commit with message:

`refactor(pilot1): modularize map and board UI`

Before committing, change this task status to exactly:

`Status: **HOLD — Slice 3.6 implemented, awaiting CI/review**`

Then:

1. commit only the scoped refactor + architecture/task-status changes;
2. push to `origin/pilot-1`;
3. report exact SHA, files changed, app.js before/after size or line count, automated results, and any parity checks/uncertainties;
4. stop.

Do **not** deploy. Do **not** start Slice 4. ChatGPT will inspect the pushed SHA and exact-SHA Pilot CI before any deployment authorization.