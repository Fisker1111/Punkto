# Pilot_1 Slice 1 — Review 1

Reviewed commit: `f0f4f053ec5b32f2b0cf8678c2636d476bb1be11`

## Decision

**Changes required before deployment.**

The implementation is disciplined and correctly limited to PWA shell files, but two behaviors do not yet satisfy the Slice 1 contract.

## Required fix 1 — make nearby-first real, not only Map-first

The current commit changes the default page state to Map, but the existing map boot still starts at the fixed fallback center and the first atom render may call `fitBounds()` across all atoms. The MapLibre `GeolocateControl` is present, but the Slice 1 implementation does not yet actively use a successful browser location as the initial nearby context.

Required outcome:

- On an ordinary non-deep-link open, attempt the existing browser geolocation path without blocking the UI or adding a permission wall.
- If location succeeds, center the initial Pilot_1 map on the user's location at an appropriate local/street scale.
- A later initial atom render must **not override that nearby context by fitting all atoms**.
- If location is denied/unavailable/times out, remain usable and keep the existing fallback map context.
- `/p/<id>` deep links remain higher priority and may override the ordinary nearby camera.
- Do not introduce a new location subsystem; use the existing MapLibre/browser geolocation architecture.

A simple acceptable strategy is to prevent normal Pilot_1 boot from auto-fitting the complete atom set, and use a one-shot existing geolocation request/control for ordinary opens. Exact implementation is up to the implementer after inspecting current lifecycle behavior.

## Required fix 2 — empty hint must reflect atoms, not bubble LOD

`updateBubbleVisibility()` currently sets `anyVisibleInViewport` only in the branch where DOM bubbles are displayed (`zoom >= 10`). At lower zoom, deck.gl atom dots can still be visible while the code concludes there are no visible atoms and shows:

> Leave the first note here.

That can produce a false empty-state message while real atoms are visibly present.

Required outcome:

- Determine whether any real atom/marker lies in the current viewport independently of whether its DOM chat bubble is hidden by zoom/LOD.
- Show the empty invitation only when there are genuinely no real atoms represented in the current viewport.
- Keep the hint lightweight and screen-space.

## Validation required before deployment review

After the fixes, rerun all Slice 1 automated checks.

The reported relay result was `55/57`. Because Slice 1 changes only PWA files, those failures may be accepted as pre-existing only after confirming the same two failures occur on the Slice 1 parent/baseline commit (`e8cc862fd857cb1ac2c92b34c4cdef2c418eb482`) in the same environment. Record that baseline comparison.

Then execute the manual browser matrix from `docs/PILOT_1_SLICE_1.md`, including:

- fresh/reset open → Map
- successful location → local camera
- denied/unavailable location → usable fallback
- atoms in viewport → no false empty hint, including low zoom
- genuinely empty viewport → empty hint
- Text, `+`, Settings unchanged
- Text → Show on map
- `/p/<id>` deep-link focus
- root/reply smoke test

## Handoff

Make one focused follow-up commit on `pilot-1`, push it, and report:

- follow-up SHA
- files changed
- exact nearby-first behavior
- empty-hint behavior at low and local zoom
- automated checks
- relay baseline comparison
- manual browser results

Then stop. **Do not deploy until explicitly approved.**
