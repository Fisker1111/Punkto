# Codex Current Task

Status: **ACTIVE — Pilot_1 Slice 3: map bottom-sheet board**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Goal

Implement Pilot_1 Slice 3 from `docs/PILOT_1_IMPLEMENTATION.md`:

> Selecting a real atom/beacon on Map opens a calm bottom-sheet/public board. The selected world position remains visible behind it. The root message is primary and replies are sequential 2D content. No reply ordering or conversation state may be represented as 3D height.

This slice replaces the temporary map popup/detail behavior with the Pilot_1 board treatment. It must reuse existing real atom/root/reply semantics rather than inventing synthetic objects.

## Starting state

The launcher has already switched to and fast-forwarded `pilot-1` from `origin/pilot-1` before invoking Codex.

Before editing:

1. Read `AGENTS.md` and `docs/PILOT_1_IMPLEMENTATION.md`.
2. Confirm the working tree is clean.
3. Record `git rev-parse HEAD` in your final report.
4. Inspect the current Slice 2 beacon selection path in `pwa/app.js` and the existing root/reply board implementation in `pwa/ui-text.js` before choosing the smallest implementation.

Do not reset or discard the workflow/CI commits already on `pilot-1`.

## Product invariants for this task

- Every selected beacon still resolves to a real atom.
- Independent atoms stay independent; do not merge same-place atoms into a synthetic board.
- Selection must be exact enough that same-place/same-punkto atoms do not all become selected merely because they share a location/punkto string. Prefer the existing stable atom identity (`atom_id` / `id` / equivalent helper) for selected visual state.
- If a selected atom is a reply, resolve and display its real root board when the root is available; the clicked atom itself remains a real atom, not a fabricated aggregate.
- Root message is the primary object in the board.
- Replies are chronological/sequential 2D UI only.
- Author/time/source/trust metadata is secondary.
- Imported-source rendering must remain recognizable and must not lose its source badge/line.
- The selected map anchor/beacon must not move when the board opens.
- MapLibre remains the only authoritative map/camera.
- `+` remains obvious and usable while/after closing the board.
- Text remains an equivalent representation of the same atoms.

## Required behavior

### Map selection

On clicking/tapping a Slice 2 beacon:

1. select that exact real atom using stable identity rather than `selectedPunkto`-style broad grouping;
2. visually strengthen only the selected beacon where possible;
3. open the board sheet;
4. keep the map/world visible behind the sheet;
5. do not show the old temporary popup as the primary detail surface.

Deep-link focus should use the same selected-board path when practical. Do not redesign routing.

### Board sheet

Use a lightweight HTML/CSS sheet. On mobile it should read clearly as a bottom sheet, not a full-screen replacement. Desktop may use a constrained bottom/side treatment if that is the smallest responsive solution.

The board must provide:

- clear close/back control;
- root message/body as the dominant content;
- category and public-message context;
- secondary author/time/trust/altitude/source metadata;
- imported-source indication when applicable;
- sequential replies below the root;
- empty reply state when there are no replies;
- scrolling inside the board for long threads so the map does not become conversation geometry;
- existing public reply action if it can be reused without protocol/storage changes.

Prefer reusing/extracting the existing `ui-text.js` root/reply formatting and semantics rather than creating a second incompatible thread model. Keep refactoring narrow; do not redesign the entire Text view.

### Closing / switching

Closing the sheet returns to the map without losing the current spatial context. Switching to Text/Settings/+ must not leave stale board overlays or block navigation. Reopening the same atom should be deterministic.

## Allowed scope

Use the smallest set of files needed. Expected candidates are:

- `pwa/app.js`
- `pwa/ui-text.js`
- `pwa/ui-map.js`
- `pwa/ui-shell.js`
- `pwa/index.html`
- optionally one small new `pwa/ui-board.js` module if that materially reduces duplication/risk

If styling is colocated elsewhere in the current PWA, make only the board-related CSS changes required for this slice.

## Explicit exclusions

Do **not**:

- change relay/protocol/sync/storage/signing behavior;
- change the create-flow product design (Slice 4 owns that);
- add likes/follows/ranking/trending;
- add new reply protocol semantics;
- merge independent atoms;
- introduce Three.js or a second camera;
- redesign beacon visuals except what is required for exact selected-state identity;
- start clustering/semantic zoom work;
- deploy anywhere;
- touch node1/node2/test1 operations.

If a required board behavior appears to need protocol or storage changes, stop and report the blocker instead of expanding scope.

## Acceptance criteria

Implementation is acceptable when, from real stored atoms:

1. tapping a root beacon opens a board sheet for that root;
2. exactly one selected atom/beacon gets selected emphasis even when another real atom shares its punkto/location;
3. tapping/deep-linking a reply resolves to its real root board when possible;
4. root content is visually primary;
5. replies display in chronological 2D order and do not affect world altitude;
6. no-reply board has an honest empty reply state;
7. imported-source root content retains imported-source treatment;
8. long reply lists scroll in the sheet while map remains visible;
9. close returns to the same map context;
10. Text, Map, +, Settings still switch cleanly;
11. old permanent DOM chat bubbles remain disabled;
12. no synthetic atom/board object is created.

## Automated checks

Run all of these before committing:

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

Also parse the exact final `pwa/app.js` as an ES module using the same approach as `.github/workflows/pilot-ci.yml`, or otherwise run an equivalent local module-parse check.

Relay result may show the repository's known baseline failures; do not modify relay files to make this slice green. Report the exact result.

## Manual/local checks where practical

Serve the exact final PWA tree locally and verify at minimum:

- map initializes with no uncaught module/JS error;
- open/close board does not blank the map;
- nav remains usable;
- if local real atom data is unavailable, clearly state which board interactions could only be structurally verified and must be checked on test1 after review/deploy.

Do not fabricate fake live activity merely to satisfy the check.

## Commit / push contract

Make one focused implementation commit with message:

`feat(pilot1): add map bottom-sheet board`

Before committing, change this task file status to:

`Status: **HOLD — Slice 3 implemented, awaiting CI/review**`

Keep the task details below it intact for traceability.

Then:

1. commit only the scoped Slice 3 + task-status changes;
2. push to `origin/pilot-1`;
3. report the exact commit SHA, files changed, automated results, manual verification, and any visual uncertainties;
4. stop.

Do not deploy. Do not start Slice 4. ChatGPT will inspect the pushed SHA and GitHub CI before any AZ deployment authorization.
