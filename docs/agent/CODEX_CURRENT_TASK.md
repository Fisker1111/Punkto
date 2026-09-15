# Codex Current Task

Status: **HOLD — glowing atom orb polish implemented, awaiting review/test1 deployment**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Context

Slice 5 is **human accepted** on test1.

Current accepted application release candidate:

`cbdf113359443e293f1d478396becc0ed0ca40cc`

Runtime marker:

`pilot1-slice5-finish-punkto-2026-09-06-1`

The accepted product flow, placement mechanics, identity, exact links, PDF/QR, board/replies, signing, relay and federation must remain unchanged.

Human acceptance found one final visual polish item before Slice 6:

> The hovering atom at the top of its stem currently reads as a flat circle/disc. It should read as a small glowing globe/orb in 3D space.

This is **visual polish only**, not a new feature.

## Goal

Make Punkto's primary atom marker feel like a **small luminous spherical orb** rather than a flat 2D disc.

The visual should reinforce the product idea:

> **A public message exists here.**

It should feel warm, spatial, calm, lightly alive, and unmistakably Punkto — not neon cyberpunk, not a game pickup, and not a glossy skeuomorphic marble.

## Required behavior

### Orb appearance

For the main atom marker rendered at its physical position:

- read immediately as a **sphere/orb**, not a flat filled circle;
- retain the atom/category color as the core identity;
- add a restrained luminous halo/glow;
- add subtle directional highlight/shading or layered depth so the object has volume;
- selected atoms may be slightly brighter/clearer, but do not introduce dramatic animation;
- elevated atoms must clearly remain at the top of their existing vertical stem;
- ground relation ring remains a separate flat ground cue;
- physical altitude remains the only meaning of Z.

The **yellow placement draft atom** must use the same spherical visual language and remain obviously distinct as the placement preview.

### Keep the current geometry semantics

Do not change:

- atom geographic x/y;
- physical altitude;
- stem endpoints;
- ground rings;
- selection identity;
- category semantics;
- click/pick target behavior;
- clustering/LOD rules;
- accepted create flow: **Aim → + → choose physical height → Done → Write → Publish**.

The camera must not move or zoom in response to this polish.

## Implementation guidance

Prefer the **smallest robust rendering change** inside the existing deck.gl rendering path in `pwa/ui-map.js`.

A literal 3D mesh is **not required**. A layered screen-space orb treatment is acceptable and probably preferable if it preserves performance and picking.

Good approaches may include:

- layered concentric deck.gl marker layers;
- a lightweight highlight/glow treatment;
- a small local/generated icon texture if needed;
- another simple deck.gl primitive already available in the bundled build.

Avoid:

- new remote assets or dependencies;
- large image files;
- custom 3D models;
- WebGL shader rewrites;
- changes to MapLibre camera/projection ownership;
- expensive per-frame DOM work.

Keep the existing `atoms` layer (or an equivalent single authoritative pickable layer) responsible for interaction so clicking/selecting atoms does not regress.

## Visual acceptance

At normal street-scale 3D view, a human should look at the top of an elevated stem and say:

> "That is a glowing point/orb floating there."

not:

> "That is a flat orange circle."

The orb should remain legible against:

- pale map backgrounds;
- buildings;
- green park areas;
- water;
- both normal and selected states.

Do not over-enlarge it. Keep roughly the same perceived footprint as the current marker, with glow extending modestly beyond it.

## Scope lock

Prefer changing only:

- `pwa/ui-map.js`
- this task file

Touch `pwa/index.html` only if strictly necessary for a local visual constant/style and avoid unrelated cleanup.

Do **not** change:

- `app.js` product behavior;
- create/height logic;
- board/replies;
- identity/key handling;
- exact-link logic;
- PDF/QR generation;
- storage schema;
- signing;
- relay/federation;
- node/server/deployment config;
- production/main.

## Checks

Run at minimum:

```bash
node --check pwa/ui-map.js
node --check pwa/app.js
node pwa/test-slice5.mjs
python3 relay/test_relay.py
git diff --check
```

Pilot CI must be green on the exact pushed SHA.

## Completion contract

Before commit, set status to:

`Status: **HOLD — glowing atom orb polish implemented, awaiting review/test1 deployment**`

Commit exactly:

`fix(pilot1): render hovering atoms as glowing orbs`

Push to `origin/pilot-1`, report exact SHA and checks, then stop.

Do not deploy. Do not merge to main. Do not start Slice 6.
