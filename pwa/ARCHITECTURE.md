# Punkto PWA Architecture

## 1) Overview

The Punkto frontend is organized into explicit layers so changes can stay local and behavior stays predictable.

Current architecture:

- **UI layer**
  - `pwa/ui-shell.js`
  - `pwa/ui-text.js`
  - `pwa/ui-map.js`
- **Core/helper layer**
  - `pwa/core/location.js`
  - `pwa/core/display.js`
  - `pwa/core/atoms.js`
- **Storage layer**
  - `pwa/storage/db.js`
  - `pwa/storage/atom-store.js`
  - `pwa/storage/node-store.js`
- **Sync/network layer**
  - `pwa/sync/node-registry.js`
  - `pwa/sync/network-client.js`
- **App coordinator**
  - `pwa/app.js`
- **Protocol/identity pieces**
  - `pwa/geohash3d.js`
  - `pwa/key-management.js`
- **Service worker/cache behavior**
  - `pwa/sw.js`

`pwa/app.js` is intentionally still the coordinator. It wires modules together, owns app state, and decides when UI updates, storage writes, and sync operations happen.

---

## 2) High-level data flow

Primary runtime flow:

```text
relay/network
  ↓
sync/network client
  ↓
storage/IndexedDB
  ↓
core helpers / display models
  ↓
app coordinator
  ↓
UI modules
```

Interpretation:

1. **Relay/network** is the external source of atoms and node info.
2. **Sync/network client** fetches and posts protocol payloads and handles request timeouts/failover attempts.
3. **Storage/IndexedDB** persists atoms and node cursor metadata.
4. **Core helpers** provide pure decode/format/filter behavior used to prepare display-ready values.
5. **App coordinator (`app.js`)** orchestrates read/write/sync/UI timing and owns page-level state.
6. **UI modules** render Text/Map shell surfaces and user interactions.

---

## 3) Layer responsibilities and boundaries

### UI layer

### `pwa/ui-shell.js`
Owns shell concerns only:
- page switching between `text` and `map`
- bottom nav wiring (`Text | Map | + | Settings`)
- settings panel open/close/toggle state
- active nav classes and body page classes
- small count labels via `setCounts()`

It does **not** own storage, network, map engine internals, or atom business logic.

### `pwa/ui-text.js`
Owns Text view rendering:
- feed card markup
- empty/location-denied states
- click delegation for **Show on map** and **Leave note here** callbacks

It expects already-sorted atom data from `app.js` and stays DOM-focused.

### `pwa/ui-map.js`
Owns lightweight map view wrapper behavior:
- lazy map initialization boundary
- resize-on-show behavior
- focus wrapper that delegates actual focus logic back to `app.js`

It does **not** replace MapLibre/deck.gl engine logic.

---

### Core/helper layer

Core modules are pure or near-pure helpers with no app-shell ownership.

### `pwa/core/location.js`
- geohash3d encode/decode wrappers
- current map center → encoded location
- haversine distance
- floor-height constant

### `pwa/core/display.js`
- relative/absolute time formatting
- distance/altitude/coordinate labels
- title/category derivation
- safe text rendering helpers

### `pwa/core/atoms.js`
- atom classification helpers
- hidden-author filtering predicate
- verified-atom predicate

Boundary rule: core helpers should remain reusable and not depend on DOM lifecycle/sync scheduling.

---

### Storage layer

### `pwa/storage/db.js`
Defines the Dexie database and schema versions:
- `atoms` table
- `meta` table
- `nodes` table (for per-node sync state)

### `pwa/storage/atom-store.js`
Encapsulates atom persistence behavior:
- upsert/insert logic
- read APIs for all atoms / newest-first
- location decode at write-time for lat/lon/alt columns

### `pwa/storage/node-store.js`
Encapsulates node persistence behavior:
- get stored nodes
- ensure node row exists
- read/write per-node cursor rows

Boundary rule: storage modules should expose persistence APIs, while orchestration stays in `app.js`.

---

### Sync/network layer

### `pwa/sync/node-registry.js`
Maintains in-memory node health and write balancing:
- health states (`ok`, `failing`, `unavailable`, `recovering`)
- candidate selection
- failure/success accounting
- write-rotation index

### `pwa/sync/network-client.js`
Owns network I/O primitives:
- timeout fetch wrapper
- post atom with multi-node fallback
- fetch node cursor
- fetch node info

Boundary rule: sync modules should not mutate DOM directly; they return data/errors for coordinator decisions.

---

### App coordinator

### `pwa/app.js`
`app.js` remains the integration point that:
- imports and wires all layers
- owns global runtime state (current page, map instance, sync timers, deep-link handling)
- sequences sync → storage → refresh UI
- coordinates create flow and settings/network info updates
- delegates rendering to UI modules

This is currently the intentional place where cross-layer coordination lives.

---

### Protocol/identity pieces

### `pwa/geohash3d.js`
Protocol-adjacent spatial encoding/decoding primitive used by core location helpers.

### `pwa/key-management.js`
Identity/key lifecycle logic (generation/import/export/storage) used by settings/identity flows.

Boundary rule: protocol/identity internals may be surfaced in Settings/debug contexts, not as primary Text/Map UI language.

---

### Service worker/cache behavior

### `pwa/sw.js`
Current behavior is intentionally conservative:
- service worker activates
- clears all caches
- unregisters itself

Result: app runs as a plain web app without persistent SW caching.

---

## 4) Practical change guidance

When editing, keep these constraints:

- **UI work**: prefer `ui-shell.js`, `ui-text.js`, `ui-map.js`; keep Text and Map as two views of the same atoms.
- **Display/format logic**: prefer `core/display.js` and `core/atoms.js` before adding more logic in `app.js`.
- **Location math/encoding**: prefer `core/location.js`.
- **IndexedDB behavior**: prefer `storage/*`.
- **Network transport/failover behavior**: prefer `sync/*`.
- **Cross-layer orchestration**: keep in `app.js`.
- **Do not redesign by default**: preserve existing protocol, sync behavior, DB schema intent, and UI shell behavior unless explicitly requested.

This keeps PRs small, auditable, and aligned with current Punkto ownership boundaries.
