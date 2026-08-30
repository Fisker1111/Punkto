# Codex Current Task

Status: **HOLD — B2 height-placement render path restored, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Human evidence

The deployed build is confirmed as:

`pilot1-slice45c4-stable-placement-2026-08-30-2`

Application SHA:

`0ed108d9e92d147a40ff1f9bb553d042ad72ecbb`

Human testing still shows **no yellow world-space placement atom** during the height stage.

The important historical clue is now explicit: the height interaction was human-accepted in Slice 4.5B2, when the lever was still on the right side. The regression appeared after the later work that moved the lever locally and changed draft rendering/projection.

Accepted B2 reference SHA:

`d6541b9f3cc67bcc7e302cc68201c52ba1b054ce`

Human acceptance of B2 was: the placement philosophy worked and a real elevated atom was successfully created.

## Code evidence

Compare current code against exact B2 SHA above before editing.

In B2, `renderAtoms()` placed the draft directly into the normal `scatterData` array, so the draft used the same proven deck.gl layers as real atoms:

- `atom-ground-rings`
- `atom-category-halos`
- `atoms`
- `atom-lollipops`
- selected/draft spatial label

B2 explicitly included `selectionId === 'draft'` in ground/stem/label filters.

Later C2/C3/C4 work detached the draft from `scatterData`, introduced `draftData`, dedicated `placement-draft-*` layers, custom render parameters, screen-projection callbacks, and local lever positioning. Human evidence says that later path is not trustworthy.

## Required fix — restore proven B2 placement behavior, not another new rendering experiment

Use exact B2 SHA `d6541b9f3cc67bcc7e302cc68201c52ba1b054ce` as the behavioral/reference baseline for the **height-placement stage only**.

### 1. Restore B2 world-draft rendering path

Restore the B2 principle exactly:

- draft is inserted into the normal `scatterData` alongside real atoms;
- draft uses the same normal ground-ring / halo / atom / lollipop layers;
- ground/stem/label filters explicitly include `selectionId === 'draft'`;
- no separate dedicated `placement-draft-*` layers are required for the world object;
- remove/disable the later dedicated draft render path if it competes with or replaces the B2 path;
- no special depth/render parameter experiment is needed unless B2 already used it.

Do not redesign published atom rendering semantics.

### 2. Restore the B2 height-control placement if necessary

Because the user specifically identified the regression as appearing after moving the lever away from the right-side B2 design, prefer restoring the **B2 right-side height lever behavior** for now rather than preserving the later local-lever positioning system.

The priority is correctness and the last known-good interaction, not preserving C2/C3/C4 lever-position polish.

Remove/disable later screen-projection/local-lever machinery if it is no longer needed after restoring B2 behavior.

### 3. Keep later shell improvements outside the placement stage

Do **not** roll the whole app back to B2.

Preserve later accepted improvements that are independent of height placement:

- current lower-left hero `+` shell;
- current Text / Map / Settings shell treatment;
- current board/composer behavior;
- current warm map/building presentation where unrelated;
- current signing/storage/network/relay/federation;
- current human atoms and protocol behavior.

Placement-stage declutter from current C4 may remain if it does not interfere:
- hide old blue center sight after x/y lock;
- hide `Leave the first note here.` during height placement;
- keep only placement controls + required attribution.

### 4. Camera rule

Do not reintroduce height-driven zoom/framing.

Moving height from Ground to 200 m must not change map zoom.

Preserve locked lon/lat and physical height.

### 5. Accepted interaction remains

> **Aim → `+` locks x/y → choose physical height → Done → Write → Publish.**

Ground remains default.

## Acceptance criteria

Before commit, verify as far as tooling allows:

1. Ground: yellow draft atom/ring is visible at locked location.
2. ~23 m: yellow ground anchor + stem + top yellow atom visible.
3. ~66 m: same; map zoom unchanged from height-stage entry.
4. ~200 m: same principle; map zoom unchanged.
5. Right-side/B2 lever remains visually a control, not the atom.
6. Draft is rendered through the same normal deck.gl atom/lollipop path used in B2.
7. No duplicate competing draft object from dedicated C3/C4 layers.
8. Done → Write still works; Cancel persists nothing.
9. Buildings restore after placement.
10. No protocol/storage/signing/relay/federation changes.
11. No uncaught runtime/module errors.

Human test1 verification remains mandatory.

## Version marker

Set exactly:

`pilot1-slice45b2-render-restore-2026-08-30-1`

## Expected scope

Prefer only:
- `pwa/ui-map.js`
- `pwa/ui-create.js`
- `pwa/index.html` only if needed to restore B2 lever layout / remove obsolete local-placement CSS
- `pwa/app.js` version marker
- this task file

Do not edit relay/protocol/storage/signing/sync/deployment/node configuration.
Do not start Slice 5.

## Checks

Run the normal Pilot CI-compatible JS/module checks, `python3 relay/test_relay.py`, and `git diff --check`.

## Commit contract

Before commit, set status to:

`Status: **HOLD — B2 height-placement render path restored, awaiting CI/review**`

Commit exactly:

`fix(pilot1): restore proven height placement render path`

Push to `origin/pilot-1`, report exact SHA/checks, then stop. Do not deploy and do not start Slice 5.
