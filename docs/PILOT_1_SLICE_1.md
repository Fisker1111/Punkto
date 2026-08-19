# Pilot_1 Slice 1 — Pilot shell

## Status

**Approved for implementation.** This is the first runtime slice for PR #110.

## Goal

Make Pilot_1 open into the nearby spatial world instead of the Text view, while preserving the current Text/Map/+ /Settings shell, existing deep links, sync/signing behavior, and current map architecture.

This slice is intentionally narrow. It must not redesign beacons, boards, protocol, sync, create flow, or deployment architecture.

## Required behavior

### 1. Default opening becomes Map

For a normal fresh/open Pilot_1 session:

- primary page is `Map`
- Map nav state is active
- map initializes immediately enough to support a nearby-first first impression
- `Text` remains one tap away
- `+` remains immediately visible
- `Settings` behavior is unchanged

Do not remove Text or turn it into a secondary product. It remains the equivalent readable representation of the same atoms.

### 2. Nearby-first behavior

Use the existing location/map logic. Do not introduce a new positioning subsystem.

- If geolocation succeeds, use it as the nearby context.
- If geolocation is unavailable/denied/times out, do not block startup.
- Fall back to the existing map context/current fallback behavior.
- Do not add a hard onboarding/location permission wall.

### 3. Humane empty-map state

When the currently visible/local map area has no real atoms, show a lightweight screen-space message:

> **Leave the first note here.**

Requirements:

- no fake atoms
- no fake counts
- no fabricated activity
- should not cover the map or compete with `+`
- hide automatically once real visible atoms exist
- keep implementation cheap: HTML/CSS overlay, not 3D geometry

If there is already an existing suitable empty/onboarding overlay, adapt/reuse it rather than adding a parallel system.

### 4. Deep links remain authoritative

`/p/<id>` must still open/focus the target atom correctly.

A deep link may override the ordinary nearby-first camera target as needed. Do not break existing delayed focus behavior while waiting for sync/map readiness.

### 5. Preserve current shell

Keep the accepted navigation and functionality:

`Text | Map | + | Settings`

Do not change nav proportions, add a hamburger, introduce new primary controls, or move settings/debug information into the first-use surface.

## Likely ownership / files

Inspect before editing. Prefer the smallest change set.

Expected primary ownership:

- `pwa/app.js` — boot/default page and coordination
- `pwa/ui-shell.js` — only if its initial page state must be aligned with Map
- `pwa/index.html` — empty-state markup/CSS only if needed
- `pwa/ui-map.js` — only if a minimal map-view hook is required

Do not touch relay/protocol/storage/network code unless a concrete Slice 1 blocker is proven and reported first.

## Explicitly out of scope

Do not implement in Slice 1:

- new beacon styling or stems
- bottom-sheet board redesign
- create-flow simplification
- urgency redesign
- semantic zoom / clustering redesign
- Three.js production integration
- new protocol fields
- server changes
- production deployment

## Version marker

Bump the Pilot_1 PWA hard/version marker to a clear Slice 1 marker, for example:

`pilot1-slice1-nearby-map-2026-08-19-1`

Use the repository's existing version-marker convention rather than introducing a second mechanism.

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

All relevant checks must pass before the commit is offered for deployment review.

## Required manual/local verification

Before asking to deploy:

1. fresh/reset browser opens on Map
2. Map nav is active
3. map tiles load
4. geolocation success does not block UI
5. denied/unavailable location does not block UI
6. Text opens and still shows the same atom set
7. `+` opens current create flow unchanged
8. Settings opens/closes unchanged
9. empty visible area shows **Leave the first note here.**
10. area with atoms does not show the empty invitation
11. Text card → Show on map still works
12. `/p/<id>` still focuses the target atom
13. root/reply behavior is not regressed
14. no relay/protocol behavior changed

## Commit and handoff

Make one focused Slice 1 commit on `pilot-1` and push it to origin.

Suggested commit message:

`feat(pilot1): open nearby-first map shell`

Then stop. **Do not deploy automatically.**

Report back with:

- commit SHA
- files changed
- concise behavior summary
- automated test results
- manual verification results
- any deviations from this slice contract
- whether the commit is ready for review/deploy

Deployment to `test1.punkto.xyz` happens only after the Slice 1 commit has been reviewed and explicitly approved for deployment in PR #110.
