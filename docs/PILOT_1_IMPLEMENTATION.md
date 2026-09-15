# Punkto Pilot_1 — Implementation Contract

## Purpose

Pilot_1 is the first field-ready implementation of the final Candidate 4 direction, shipped under Candidate 5's lightweight discipline.

Pilot_1 is not a full world/semantic-zoom release. It exists to prove one product claim with real people:

> **People understand and use public messages attached to real places.**

The primary product statement is:

> **Punkto opens by helping someone understand the world; contribution remains one obvious action away.**

## Scope lock

Pilot_1 must remain narrow. Do not add unrelated protocol, sync, moderation, media, profile, social, or native-app work.

### In scope

1. nearby-first Map opening
2. lightweight recognizable geography
3. invariant spatial beacon for real atoms
4. physical altitude represented vertically
5. selected atom opens a flat board/bottom sheet
6. replies remain 2D UI, never world height
7. one obvious `+` create action
8. create flow fast enough for a real urgent report
9. honest empty state
10. simple sparse/dense behavior and basic clustering
11. Text view remains available as an equivalent representation
12. reduced-motion / weak-device behavior preserves meaning
13. existing signing, sync, relay, and deep-link behavior remains intact

### Explicitly out of scope

- world Flow / cinematic semantic zoom
- handcrafted or asset-heavy 3D environments
- follower/like/popularity features
- automatic merging of independent atoms
- new media/attachment system
- protocol redesign for confirmations/disputes/resolution
- self-hosted global basemap project
- native mobile rewrite

## Product invariants

These are acceptance rules, not styling suggestions.

1. **Message-first.** Message and place dominate author/profile information.
2. **Nearby-first.** Normal open should lead with the local world, not a feed or global channel.
3. **Beacon means atom.** Every visible beacon resolves to one real atom.
4. **Vertical means altitude.** Never reply order, popularity, urgency, age, or activity.
5. **Replies are flat UI.** Threads appear in a board/sheet, not 3D stacks.
6. **Independent atoms stay independent.** Clustering is a view only.
7. **One obvious contribution action.** `+` must remain immediately discoverable.
8. **No engagement ranking.** Existing chronological/spatial logic stays intact.
9. **One spatial truth.** Do not introduce a second independent map/3D camera.
10. **Light but alive.** Procedural glow, humane copy, and calm motion are allowed; heavy assets are not required.

## Required mobile states

### 1. Nearby opening

- Map is the primary first-use Pilot_1 surface.
- Current location is requested contextually, not behind a hard onboarding wall.
- If location is unavailable, fall back to the existing/last map context without blocking use.
- Nearby real atoms are visible when present.
- `+` is visible without opening another menu.
- Text remains one tap away.

Five-second comprehension target:

> “These are public notes people left around here, and I can leave one too.”

### 2. Empty neighborhood

Show honest geography and a quiet invitation such as:

> **Leave the first note here.**

No fake atoms, fake counts, or fabricated activity.

### 3. Street view with beacons

- beacon is visually stronger than the map scenery
- category may influence form/color but cannot rely on color alone for urgent content
- selected atom has a clear exact anchor
- altitude stem remains legible where altitude exists

### 4. Selected atom / board

- selected beacon remains visible behind/above the board where practical
- root message is primary
- replies are sequential 2D content
- author/time/source metadata is secondary
- long threads scroll in the board rather than creating world geometry

### 5. Create flow

Fast path:

`Tap + → type → publish → return to world`

Requirements:

- text field should become ready quickly
- map rendering must not be a conceptual prerequisite for composing
- current anchor is visible/understandable
- advanced altitude/place adjustment remains progressive disclosure
- first-use public-data acknowledgement remains clear
- successful publish returns to the same spatial context

Target for Pilot_1 field test:

- urgent-post p95 under 20 seconds from app open to accepted signed atom on the named reference device/network

### 6. Urgent atom

Existing warning/emergency categories may be used for Pilot_1 without introducing a new protocol kind.

Urgency must be readable with redundant visual cues (shape/icon/text and color), remain sober, and never resemble an engagement/trending signal.

### 7. Altitude example

At least one seeded/test atom must demonstrate physical altitude clearly. The board and map must not imply that replies are at different heights.

### 8. Text equivalent

Text remains an accessible/list representation of the same atoms. It must not become a separate ranked feed product.

## Rendering direction

Pilot_1 should reuse the current MapLibre/deck.gl stack unless a specific blocker is proven.

- MapLibre remains authoritative for the map/camera.
- Keep 3D lightweight.
- Reuse current atom/stem/ground-ring work where it helps.
- Prefer simple beacons, CSS/HTML board UI, and cheap map styling.
- Avoid a separate synchronized Three.js camera for the production Pilot_1 path.

The existing `test1-atomcloud` work in PR #108 is a source of useful experiments, not automatically the implementation branch.

## Performance discipline

Reference target: a real mid-range/older Android on ordinary 4G.

Pilot_1 must not depend on:

- large art downloads
- bespoke city assets
- high-end GPU features
- long animation sequences

Reduced-motion or weak hardware may remove motion/extrusion/detail, but must preserve:

- atom identity
- location
- altitude meaning
- urgency meaning
- board/read/write capability

## Implementation sequence

### Slice 1 — Pilot shell

- open nearby-first on Map for Pilot_1
- preserve Text/Map/+ /Settings functionality
- make empty-map state humane and explicit
- verify deep links still work

### Slice 2 — Beacon + selection

- refine current marker/stem into Pilot_1 invariant beacon
- keep physical altitude semantics
- selected atom visibly owns its board

### Slice 3 — Board

- selected root opens bottom-sheet/board treatment
- replies remain flat and readable
- preserve reply behavior and imported-source rendering

### Slice 4 — Fast create

- reduce friction in current staged create sheet
- preserve signing/public warning/category/altitude behavior
- ensure normal simple post path is obvious

### Slice 5 — Field hardening

- reduced motion
- older-phone check
- QR/deep-link destination check
- network failure behavior
- seeded Pilot_1 content
- hard-marker/deployment verification

## Required checks before merge/deploy

At minimum run:

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

Manual checks:

- fresh browser / reset
- nearby Map opening behaves as intended
- Text remains accessible
- Map loads and location works
- `+` create works
- public-data acknowledgement works
- Settings still opens/closes
- Text card → Show on map works
- `/p/<id>` deep link works
- root/reply board works
- imported source atom works
- altitude example works
- empty state works
- urgent category is distinguishable
- successful post appears through normal sync path

## Deployment ownership

### Git / implementation

All Pilot_1 implementation work goes through branch:

`pilot-1`

and its dedicated PR.

Small commits and reviewable slices are preferred.

### AZ / webservers

Agent Zero owns deployment/ops only:

1. deploy only a reviewed Pilot_1 commit/PR head
2. use the repository's `DEPLOYMENT_CHECKLIST.md`
3. deploy to the designated test/pilot node first
4. verify container state, hard marker, relay health, map load, create, sync, and deep links
5. record exact deployed commit SHA and hostname in the Pilot_1 PR
6. do not redesign/refactor product code during deployment
7. production/main rollout occurs only after human field verification

## Pilot_1 field acceptance gates

Pilot_1 is successful enough to continue when real tests show:

1. a cold newcomer can explain the product after a glance
2. a cold user recognizes that a beacon is a public message at a place
3. an urgent report can be posted in under the target time
4. urgent content is recognized as serious
5. root/reply/altitude are not confused
6. sparse geography feels intentional, not broken
7. the app performs reliably on the reference phone/network
8. at least some people read atoms from authors they do not know

Failure on comprehension or urgent posting should trigger simplification before adding richer world features.

## Decision rule

For every implementation request during Pilot_1 ask:

> **Does Pilot_1 need this to prove that public messages attached to places are useful and understandable?**

If not, backlog it.