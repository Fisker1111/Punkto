# Punkto UI Principles

## Core idea

Punkto has one world of atoms/punkti shown in two main ways:

> **Text** = read what is here.
> **Map** = see where it is in space.

They are not separate data models. They are two representations of the same atoms.

---

## Visual language (dark / glass / modern)

Punkto uses ONE visual language across ALL surfaces: dark, glass, modern.
The map is the only light element; everything floating over it is dark glass.

This is a HUD over reality, not a light document app.

### Shared tokens (single source — reuse everywhere)

| Token | Value | Applies to |
|---|---|---|
| Surface base | dark ink/navy @ 60–70% opacity | bubble, pill, cards, sheets, toast |
| Blur | backdrop-filter: blur(16–20px) | all floating surfaces |
| Hairline border | 1px white @ 8–12% opacity | all floating surfaces |
| Elevation | large-blur / low-spread dark shadow | all floating surfaces |
| Radius | 16px (cards/sheets), full-pill (nav bubble) | all floating surfaces |
| Accent | existing blue | + button and primary actions ONLY |
| Text | high-contrast off-white; secondary ~70% | all text |

Rule: do NOT ship a surface in light theme. The Settings sheet is the
reference look; all other surfaces must match it.

---

## Primary shell — the nav bubble

Navigation is ONE floating component: a 4-button nav bubble.

```
Text | Map | + | Settings
```

It is NOT a bar. It is a single glass bubble that DOCKS by breakpoint:

| Breakpoint | Bubble dock | Bottom bar/strip? |
|---|---|---|
| Mobile | bottom-center | none — the bubble is the bottom element |
| Desktop | left, vertical rail | NONE — no bottom bar, no bottom strip |

| Button | Role | Weight |
|---|---|---|
| Text | Readable feed/list | 35% |
| Map | 3D/spatial view | 35% |
| + | Create/place atom (blue accent) | 15% |
| Settings | Identity, network, app/admin/debug | 15% |

Hard rules:
- Exactly 4 buttons. Nothing else. No extra on-screen nav buttons.
- NO hamburger (☰) anywhere — on any breakpoint.
- Desktop has NO bottom bar/strip; the left bubble is the only nav.

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
- Use ONE badge per card (e.g. "Talk"), not stacked BOARD + TEXT·TALK
- Use ONE primary CTA per card ("Open board", accent); demote "Show on map" to a small secondary/ghost/icon action

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
- Keep the canvas clean: group map controls (locate, 2D/3D, zoom) into ONE glass control cluster in a single corner
- Auto-dismiss the placement coaching toast after the first placement
- Show nothing else floating except: the nav bubble, the one control cluster, and content chips/cards

Map view should NOT:
- Be initialized at boot while the container is hidden
- Replace or re-implement the existing MapLibre engine
- Block the Text view from loading
- Show a separate hamburger or duplicate navigation control

---

## Create flow

**+** opens creation as a dark-glass sheet. Simple first, advanced on request:

1. Write a note (default focus)
2. Confirm location
3. **Place here**

Height/floor/altitude are HIDDEN by default behind a single
**"Adjust height"** expander (progressive disclosure).

Keep the **"Public and permanent — this cannot be deleted"** warning
prominent and bright against the dark surface.

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
- Lock a shared layout system: one edge margin, one corner radius, one blur value, one border, one elevation token — applied to every floating surface (bubble, pill, cards, toast, sheets)
- Dark / glass / modern is mandatory on all surfaces; the live app must never drift back to a light product theme
