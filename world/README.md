# Punkto World — V0 rapid prototype

Disposable product-discovery prototype: explore Punkti **atoms as objects in a
navigable world**, rather than a map/feed. Deployed to `https://test1.punkto.xyz`
for Founder visual review. It does **not** touch `punkto.xyz`, `main`, or the
existing PWA/relay.

## Data — FIXTURE ONLY

V0 uses a deterministic **fixture** atom set (18 places around Copenhagen:
Nyhavn, Tivoli, Rundetårn, Christiania, Amager Strand, ...). The live relay
returns empty atom arrays, so a fixture sits behind the `getAtoms(bounds, time)`
adapter boundary. No live or stored Punkti data is used. See
`src/atomsAdapter.ts`.

## Architecture

- **MapLibre GL JS** — geographic world, camera, pan/zoom/tilt/rotate, dark
  keyless CARTO raster basemap (only the basemap uses the network).
- **Three.js** — Punkti atoms as spatial 3D objects: glowing orbs with height +
  a vertical beam + a ground ring, sharing MapLibre's WebGL context via a
  `CustomLayerInterface`. Height = real altitude above ground, not a map pin.
- **`atomsAdapter.ts`** — the data boundary:
  `getAtoms(bounds, time) => Promise<WorldAtom[]>`; the renderer is
  independent of any specific Punkti DB/API.
- **`ui.ts / style.css`** — plain HTML/CSS. Compact detail panel, time-control
  slider (filters fixture timestamps), minimal dark HUD.
- **`main.ts`** — bootstraps MapLibre + the Three overlay + UI.

## Run / build

```bash
npm install
npm run dev      # local dev, http://localhost:5173
npm run build    # tsc --noEmit && vite build  → emits world/dist (static site)
npm run preview  # serve the build locally
```

`npm run build` must exit 0 and emit `world/dist/index.html`.

## Scope / non-goals

No publishing, identity creation, accounts, AI/chat, social metrics, native
packaging, or PWA polish in this slice. `main`, `pwa/`, `relay/`, `core/`,
`deploy/`, `.github/` are untouched.

## Deployment (nodes)

Static `world/dist` is served behind `https://test1.punkto.xyz` on node1/node2
via a dedicated Caddy `test1.punkto.xyz` site block + host bind mount, added
alongside the existing `punkto.xyz` configuration. Rollback: remove the added
site block/mount and reload Caddy; `punkto.xyz` configuration is untouched.