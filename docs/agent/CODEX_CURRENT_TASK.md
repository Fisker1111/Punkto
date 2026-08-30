# Codex Current Task

Status: **ACTIVE — Pilot_1 Slice 4.5C4 correction: stable camera + visible world draft**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Human evidence / diagnosis correction

The deployed C4 application SHA `eabb035481284b619a76db4803aeca3cf870cad5` is still wrong.

Two fresh human screenshots show:

1. At **Ground**, the locked center sight is visible but the yellow world-space draft atom is not visibly readable.
2. At **+200 m**, C4 dynamically zooms the map far outward while the yellow world-space draft still is not readable. The dark height-lever handle remains visually dominant.

Therefore the C4 framing hypothesis is not accepted. The product must not chase height by changing map zoom.

The original accepted interaction principle is stronger:

> **The sight chooses place. The lever chooses height. The world shows both.**

And the gameplay rule remains:

> **The camera must not fight the user during height manipulation.**

## Starting state

Start from exact current `pilot-1` HEAD at task activation. Read current `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/index.html`, `pwa/app.js`, and `AGENTS.md` before editing.

Do not start Slice 5. This is a correction to C4, not a new product slice.

## Required correction

### 1. Remove dynamic height-driven zoom/framing

During the height stage, changing the lever from 0 through 200 m must **not change map zoom**.

Remove/disable the C4 height-aware zoom policy and any recursive camera fitting that was introduced solely to chase the vertical relation.

A one-time gentle pitch setup on entering the height stage is acceptable only if already needed for the accepted B2 interaction. Height changes themselves must not continuously zoom/reframe the map.

Do not change locked lon/lat or selected physical height.

### 2. Make the actual world-space draft unmistakably visible

The yellow placement object must be visually present independently of the lever UI.

At Ground:
- the locked place must show a visible yellow draft beacon/anchor;
- the old blue center sight must not cover or visually replace it after x/y has been locked;
- once `+` locks x/y, either hide/de-emphasize the sight during the height stage or otherwise guarantee the yellow draft remains clearly visible over it.

At positive height:
- show yellow ground anchor;
- show yellow/cased stem;
- show yellow top beacon;
- all are one real draft at the locked world coordinate;
- the dark lever handle is only a control and may never masquerade as the atom.

Inspect the dedicated draft deck.gl layers added in C3. Confirm they receive finite `[lon, lat, z]` values and are actually included in `deckOverlay.setProps({ layers })` during the height stage. Fix the real rendering/UI-covering issue rather than adding more camera heuristics.

### 3. Keep lever separate from the world object

Do not position the lever handle directly over the top beacon, ground anchor, or stem.

The lever may remain nearby, but preserve a clear visual gap. Its connector may point toward the draft without covering it.

If C4 top-beacon-following makes the lever cover the world object, simplify it. Local and obviously associated is enough.

### 4. No placement-stage clutter

During height placement, suppress unrelated UI that competes with the spatial task, including the `Leave the first note here.` empty-state hint if it is currently visible.

Keep only the necessary placement elements: map/world, draft relation, height readout, lever, Cancel/Ground/Done, required attribution.

### 5. Preserve accepted behavior

Do not change:
- Aim → `+` locks x/y → choose physical height → Done → Write → Publish;
- 0–200 m mapping and fine 0–30 m control;
- building ghosting;
- signing/storage/network/relay/federation;
- published atom rendering;
- board/Text/Settings/deep links.

## Acceptance gate

Before committing, verify as far as local browser tooling allows:

- Ground: yellow draft is clearly visible at locked place; center sight does not hide it.
- ~23 m: yellow ground anchor + stem + top beacon visible.
- ~66 m: same, with no map zoom change caused by moving the lever.
- ~100 m and ~200 m: same principle; map zoom remains the entry zoom.
- Lever is visibly separate from the yellow top beacon.
- `Leave the first note here.` is not shown during height placement.
- Done opens Write; Cancel restores normal shell/camera controls and persists nothing.
- no uncaught runtime/module errors.

Human test1 verification remains mandatory.

## Version marker

Set exactly:

`pilot1-slice45c4-stable-placement-2026-08-30-2`

## Expected scope

Prefer only:
- `pwa/ui-map.js`
- `pwa/ui-create.js`
- `pwa/index.html` if needed for placement visibility/declutter
- `pwa/app.js` version marker
- this task file

No relay/protocol/storage/signing/deployment changes.

## Checks

Run the normal Pilot CI-compatible JS/module checks, `python3 relay/test_relay.py`, and `git diff --check`.

## Commit contract

Before commit, set status to:

`Status: **HOLD — Slice 4.5C4 correction implemented, awaiting CI/review**`

Commit exactly:

`fix(pilot1): stabilize height placement preview`

Push to `origin/pilot-1`, report exact SHA/checks, then stop. Do not deploy and do not start Slice 5.