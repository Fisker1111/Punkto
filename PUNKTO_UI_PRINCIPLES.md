# Punkto UI Principles

## Core idea

Punkto has one world of atoms/punkti shown in two main ways:

> **Text** = read what is here.
> **Map** = see where it is in space.

They are not separate data models. They are two representations of the same atoms.

---

## Primary shell

Accepted bottom nav:

```
Text | Map | + | Settings
```

| Button | Role | Width |
|---|---|---|
| Text | Readable feed/list | 35% |
| Map | 3D/spatial view | 35% |
| + | Create/place atom | 15% |
| Settings | Identity, network, app/admin/debug | 15% |

Active states:
- **Text** highlights when `currentPage === "text"`
- **Map** highlights when `currentPage === "map"`
- **Settings** highlights when the settings panel is open
- **+** never has a persistent active state — tap/press feedback only

---

## Language rules

### Use in primary UI

- Text
- Map
- Show on map
- Open in text
- Leave note here
- Place atom
- Height
- Floor
- Nearby

### Avoid in primary UI

- `atom` as a primary nav label or heading (use Text / Map)
- `geohash` (internal)
- `append-only` (internal)
- `node` internals exposed to users
- `signature` internals exposed to users
- Protocol debug terms in the main UI
- `Atoms` as a primary nav label
- `Space` as a primary nav label
- `Network` as a primary nav label
- `Me` as a primary nav label

Advanced/settings pages may show technical details.

---

## Text view

Text view should:
- Be the default landing page
- Show nearby atoms as readable cards
- Show distance, altitude/floor, time, and category if available
- Have a **Show on map** action on each card
- Handle empty state (no atoms nearby)
- Handle location-denied state gracefully
- Avoid feeling like a generic social media clone

Text view should NOT:
- Be the only way to interact with atoms
- Expose raw protocol fields in card UI
- Require location permission before showing anything

---

## Map view

Map view should:
- Preserve MapLibre/deck.gl as the rendering engine
- Show 3D placement with lollipop/altitude markers
- Support atom focus from Text cards (Show on map)
- Support deep links (`/p/<id>`)
- Support free altitude/floor placement when creating
- Initialize lazily (only when first shown, not at boot)

Map view should NOT:
- Be initialized at boot while the container is hidden
- Replace or re-implement the existing MapLibre engine
- Block the Text view from loading

---

## Create flow

**+** opens creation.

Creation should be simple first, advanced only when needed:

1. Write text
2. Confirm location
3. Set height/floor (optional)
4. Place / save

Do not expose geohash or canonical form in the creation UI.

---

## Settings

Settings contains:
- Identity / keys (generate, import, export, save, load)
- Network status (node, peers, sync)
- App version and hard marker
- Cache reset / debug
- Advanced / internal info

Settings is **not the product** — it is management.

Settings panel should:
- Be closed by default on first load
- Slide up from the bottom (below the top of the bottom nav)
- Close when the user taps Settings again or taps outside
- Highlight the Settings button while open

---

## General design constraints

- Do not add a framework (React, Vue, etc.) without an explicit decision
- Do not introduce a server-side rendering layer
- Do not add social features (likes, follows, comments) without an explicit decision
- Do not expose protocol internals in the primary UI
- Keep Text and Map as **two views of the same atoms** — not separate sections
- Prefer progressive disclosure: simple first, detail on request
