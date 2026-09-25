# Codex Task — Punkto World V0 rapid prototype

Status: ACTIVE
Repository: Fisker1111/Punkto
Branch: world/prototype-v0 (already checked out, isolated from main)
Worktree: /home/hermes/.hermes/cache/scratch/punkto-world-v0

## Purpose / Spec source

This is a disposable product-discovery prototype. Build a browser-first "Punkto World"
experience where Punkti atoms feel like compelling 3D objects in a navigable world,
rather than the current map/feed UI. It will be deployed to https://test1.punkto.xyz
for Founder visual review. DO NOT touch punkto.xyz. DO NOT merge to main.

## Absolute rules (from AGENTS.md + this task)

- Put ALL new prototype code in a NEW self-contained directory: `world/` at the repo root.
- Do NOT modify any existing files (pwa/, relay/, core/, deploy/, .github/, docs/). This is
  an isolated prototype. The existing Punkto app must remain byte-for-byte unchanged.
- Do NOT change Punkti protocol/semantics, signing, identity, or stored data.
- Do NOT add publishing, identity creation, accounts, AI/chat, social metrics, or PWA polish.
- No new application backend. Static/client-side only.

## Architecture (required)

- TypeScript + Vite (build to `world/dist`).
- MapLibre GL JS for the geographic world/camera/terrain/vector context. Use a Vector tile
  or raster tile source that has a global dark style. If a tile URL needs an API key, use a
  keyless public source (e.g. demo tiles or OSM raster under a dark filter). Prefer a style
  that needs no key.
- Three.js for Punkti-specific 3D atom visuals (spatial objects with height/presence, NOT flat map pins).
- Simple HTML/CSS UI. No React.
- Keep world rendering separated from the data source via an adapter boundary,
  conceptually: `getAtoms(bounds, time): Promise<Atom[]>`.
  The renderer must not depend on a specific Punkti DB/API.
- DATA: The live Punkto relay returns EMPTY atom arrays (verified 2026-09-25). Use a small
  deterministic fixture behind the adapter. Multiple fixture atoms around Copenhagen.
  Clearly document that the data is fixture data (put a comment in the adapter and a note
  in README).

## V0 experience (acceptance criteria)

1. Landing view is a recognizable Copenhagen-area world (centered ~55.6761, 12.5683).
2. User can pan, zoom, tilt, rotate (MapLibre camera).
3. Restrained geographic styling; buildings/terrain visually subordinate to atoms.
4. Multiple Punkti/Punkto atoms rendered as spatial 3D Three.js elements with real height/
   presence (e.g. glowing vertical beams/columns or float-level markers with altitude), not
   flat pins.
5. Clicking/tapping an atom opens a compact detail treatment showing at least its
   message/content and whatever identity/time/location data the fixture provides.
6. Simple time-control concept (e.g. a slider scrubbing a time window that filters fixture
   atoms by timestamp). Acceptable to only filter fixture/current timestamps.
7. Mobile viewport usable.
8. Aesthetic: sparse, dark, architectural/world-like. Minecraft-exploration feel — NOT voxels,
   NOT a game engine. Atmosphere over clutter.

## Adapter interface

Define a TypeScript interface roughly:

```ts
export interface WorldAtom {
  id: string;
  x: number;           // lon
  y: number;           // lat
  altitudeM: number;   // metres above ground
  t: number;           // epoch ms timestamp
  message: string;
  identity?: string;   // optional display name
  color: string;       // category/tint colour
}

export interface AtomAdapter {
  // Returns atoms relevant to the given geographic bounds and time window.
  getAtoms(bounds: {minLon,maxLon,minLat,maxLat}, time: {from,to}): Promise<WorldAtom[]>;
}
```

Fixture adapter: ~12-25 deterministic atoms near Copenhagen (e.g. Nyhavn, Tivoli, Rundetårn,
The Lakes, Christiania, Amager Strand, etc.). Give each a plausible short message, an altitude,
a color, identity, and a timestamp spread across the V0 time window.

## Deliverables

- `world/` with package.json, tsconfig.json, vite.config.ts, index.html, src/
- `world/src/main.ts` — bootstraps MapLibre + Three overlay + UI
- `world/src/atomsAdapter.ts` (or similar) — the getAtoms adapter + fixture
- `world/src/three*` — Three.js atom rendering
- `world/src/ui*` — detail panel, time control, minimal HUD
- `world/src/style.css`
- `world/README.md` — how to run (`npm install && npm run dev` / `npm run build`),
  architecture summary, and explicit note that V0 uses FIXTURE atom data.
- `npm run build` must succeed and emit a static site into `world/dist` that works when
  served by any static file server at the site root.

## Commit

- Commit all `world/` additions with message:
  `feat(world): Punkto World V0 prototype (fixture atoms, MapLibre+Three) v0`
- Include a note that main/pwa/relay are untouched.
- DO NOT push to origin/main. You may push this branch to origin (world/prototype-v0) only if
  everything builds and works. If unsure, leave the commit local — Hermes will push.

## Checks before finishing

- `npm run build` (in world/) exits 0 and produces world/dist/index.html.
- No TypeScript errors in `npm run build`.
- You are running in the worktree directory; verify with `pwd`.