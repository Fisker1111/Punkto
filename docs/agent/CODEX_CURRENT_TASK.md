# Codex Current Task

Status: **HOLD — Slice 3.6 review fix implemented, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Goal

Repair the narrow runtime regression found during ChatGPT review of Slice 3.6 exact SHA `eb175784aa6e1fccb84e305ef67664224149f0b4`, and harden Pilot CI for the new module boundary.

This is **not a new feature slice**. Preserve Slice 1–3 behavior and the completed 3.6 architecture extraction.

## Review finding

`pwa/app.js` still calls `getCategoryMeta(a)` while rendering atom-list items, but Slice 3.6 moved/deleted the app-local helper and does not import a replacement. With any real atom in the list this will throw:

`ReferenceError: getCategoryMeta is not defined`

The empty test1 node currently has zero public atoms, so this runtime path was not exercised by the staging smoke test.

Also, `.github/workflows/pilot-ci.yml` does not yet syntax-check the new `pwa/ui-board.js` module or require it as a Pilot file.

## Required fix

1. Restore the exact existing category code/label/class behavior used by atom-list rendering without undoing the 3.6 modularization.
2. Prefer a small shared display/UI helper in an appropriate existing module over reintroducing duplicated category tables in `app.js`. Do not make `app.js` depend on `ui-map.js` solely for category metadata unless that is clearly the smallest safe option.
3. Keep map colors, category labels/classes, imported-source behavior, Text rendering, create behavior, storage/sync/protocol/signing, and board behavior unchanged.
4. Update `.github/workflows/pilot-ci.yml` so the hard PWA gate:
   - runs `node --check pwa/ui-board.js`;
   - runs `node --check pwa/ui-settings.js` if not already present;
   - parses `pwa/ui-map.js` and `pwa/ui-board.js` as ES modules in addition to `app.js`;
   - requires `pwa/ui-board.js` to exist.
5. Do not deploy. Do not start Slice 4.

## Expected scope

Use the smallest safe set, likely:

- `pwa/app.js`
- one existing shared display/UI module if needed (`pwa/core/display.js` or `pwa/ui-text.js`)
- `.github/workflows/pilot-ci.yml`
- `docs/agent/CODEX_CURRENT_TASK.md`

Do not edit relay/protocol/storage/sync/deploy/ops files.

## Acceptance criteria

- Rendering a real atom no longer references an undefined `getCategoryMeta`.
- Existing category code, label, and CSS class output remains behaviorally identical.
- Slice 3.6 map/board module ownership remains intact; do not move MapLibre/deck.gl or board-sheet logic back into `app.js`.
- `ui-board.js` and `ui-map.js` are covered by exact-SHA module/syntax CI.
- Existing Pilot CI and relay suite pass.
- No visual/product behavior changes.

## Checks

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
node --input-type=module --check < pwa/app.js
node --input-type=module --check < pwa/ui-map.js
node --input-type=module --check < pwa/ui-board.js
python3 relay/test_relay.py
git diff --check
```

If practical, perform a focused runtime parity check with at least one atom/list-render path. Do not fabricate production/staging network activity merely for this check.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 3.6 review fix implemented, awaiting CI/review**`

Commit with exactly:

`fix(pilot1): repair slice 3.6 runtime parity`

Push to `origin/pilot-1`, report exact SHA/check results, and stop.

Do not deploy. Do not start Slice 4.
