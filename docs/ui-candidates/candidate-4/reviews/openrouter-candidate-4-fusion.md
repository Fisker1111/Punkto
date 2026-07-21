# OpenRouter Model Fusion — Candidate 4

## Executive verdict

Candidate 4 is coherent, but only if two structural commitments are locked:

1. **One authoritative camera and projection.** Punkto's 3D beacons and local extrusion should render in MapLibre's spatial context, such as through a custom layer using MapLibre's projection matrix. Avoid a separately controlled Three.js camera synchronized to the map.
2. **The vertical world axis means physical altitude only.** Replies always live in flat 2D board UI.

With these commitments, Candidate 4 has one spine—semantic zoom from patterns to situations to messages to conversation—one invariant object—the beacon—and one emotional register—a calm, warm public world.

The central product statement is:

> **Punkto opens by helping someone understand the world; contribution remains one obvious action away.**

Viewing and writing should not be separate destinations. The user understands by looking at the world and contributes by acting on that same world.

The principal risk is the viewer-first cold-start paradox: a viewer-first experience needs real content, while most launch neighborhoods will be sparse. The recommended resolution is to keep the interface viewer-first but use an author-first launch strategy with deliberate communities, campaigns, and official data sources.

Candidate 4 should replace Candidates 1–3 as the leading direction while absorbing them as facets:

- Candidate 1: near/atom and board interaction
- Candidate 3: semantic-zoom awareness architecture
- Candidate 2: tightly bounded warmth and environmental readability

It should ship first as a Candidate 1-shaped local MVP and expand upward only after evidence.

---

## Candidate definition

**Name:** The Living Public World

**Concept:** Punkto is a calm, warm public world you zoom into—from regional activity patterns to a single public message pinned at one real place—where reading the world and leaving a message happen on the same continuous surface.

### Governing principles

1. The message is the object; the world is its context.
2. One continuous world, one semantic zoom axis.
3. See first, contribute instantly.
4. Vertical space means physical height only.
5. Every beacon represents a real independent atom.
6. No popularity or engagement-ranking system.

### Must never become

- a feed
- a GIS or operator console
- a handcrafted dollhouse world

---

## First five seconds

Punkto opens nearby-first at a gently pitched district/street threshold:

- warm 2D or restrained 2.5D map
- nearest real beacons visible
- readable roads, water, parks, and footprints
- one place/context pill
- one recenter action
- one persistent `+`

Without location permission, use last viewed place, coarse region, or user-selected home area. Do not show a hard permission wall.

In an empty area, show honest geography and a quiet invitation:

> Leave the first note here.

A non-technical user should say:

> “These are public notes people left around here, and I can leave one too.”

---

## Core interaction

```text
Open → Understand → Explore → Select → Read → Contribute → Return
```

- **Open:** nearby, warm, pitched map
- **Understand:** beacon means message here; glyph means kind; brightness means freshness
- **Explore:** pinch out to concentrations and regional patterns; pinch in to individual atoms
- **Select:** tap a beacon; keep its exact anchor visible; raise board from below
- **Read:** root and replies in sequential 2D UI
- **Contribute:** tap `+`, place a provisional beacon, type, publish, return
- **Return:** dismiss sheet or recenter; no separate home screen required

---

## Semantic zoom

### Region

Show soft activity pulses. A pulse means more recent independent messages exist in the area. It does not mean popular, trending, or one synthetic event.

### District

Show honest concentrations or counts where individual atoms overlap. Selecting a concentration zooms in rather than opening a fabricated combined story.

### Street

Buildings may begin to rise. Individual beacons separate. Physical altitude becomes meaningful.

### Atom

The selected beacon brightens while the exact spatial anchor stays visible. A bottom-sheet board shows the root and replies.

---

## Invariant beacon

The beacon is the one object that means:

> A public message exists here.

Recommended properties:

- compact luminous seed/droplet
- thin stem to exact ground or building anchor
- category communicated by shape/glyph plus color
- freshness through brightness and one gentle ripple
- urgency through a sober upright form and steady pulse
- thread presence through a compact reply count
- altitude through stem length and explicit floor/elevation chip
- selection through brightening, anchor ring, and softened neighbors

At distance it simplifies from beacon to dot, concentration, and regional pulse.

---

## Thread and altitude

Replies belong in an expandable bottom-sheet board:

- root pinned and visually dominant
- replies indented beneath
- long threads scroll in the sheet
- ten or more replies never change map geometry
- new replies trigger one subtle beacon ripple

The world Z-axis is reserved exclusively for physical altitude.

---

## Writing flow

Fast path:

1. Tap `+`.
2. Show provisional beacon at current anchor.
3. Open compose sheet with keyboard ready.
4. Type the message.
5. Optionally choose Note, Infrastructure, or Warning.
6. Publish.
7. Return to same spatial state.

Advanced controls remain under **Adjust place & height**.

Public notice:

> Public and signed. Anyone can read this.

Signing is automatic; author identity stays secondary.

---

## Scenarios

### Everyday

**Bench by the canal has sun until 7 pm.**

- warm everyday beacon
- small selected board
- optional expiry or retirement after relevance ends

### Infrastructure thread

**Fire hydrant not working.**

- infrastructure beacon with reply count
- root plus sequential replies in the board
- persists until resolved or updated

### Urgent report

**Flooding here — road blocked.**

- sober warning form visible farther out
- precise street anchor
- selected board with timestamps and updates
- freshness/confirmation rules prevent stale warnings

Independent reports remain independent unless they are actual replies to the same root.

---

## Content selection

Permitted:

- proximity
- recency
- selected categories
- explicit urgency
- active replies as freshness
- official/source presence
- saved places

Forbidden:

- click optimization
- outrage
- dwell-time maximization
- follower popularity
- reaction totals as ranking
- opaque engagement scoring

The product should be able to explain:

> Shown because it is near you and recent.

---

## Engineering assessment

Recommended architecture:

- MapLibre remains authoritative for camera and projection
- broad scales stay 2D/data-driven
- district uses clustering/concentrations
- true 3D begins mainly at street scale
- beacons use instancing or cheap repeated primitives
- board and replies remain HTML/CSS
- weak-device fallback is fully functional 2D
- reduced-motion mode is static
- cached tiles/atoms and queued signed writes support unreliable networks

Main technical risks:

1. smooth semantic zoom on ordinary Android phones
2. custom-layer performance and battery use
3. variable global building data
4. honest altitude/floor placement
5. collision-safe atom display at density

---

## MVP recommendation

Ship a Candidate 1-shaped local MVP inside Candidate 4's architecture:

- nearby-first warm MapLibre world
- invariant beacon
- selected board bottom sheet
- 2D public replies
- fast `+` writing
- category and sober urgent register
- freshness/lifecycle foundations
- basic clustering
- weak-device fallback
- reduced motion

Postpone regional pulses, district blooms, rich 3D environments, precise altitude promises, and a global live channel until performance and usage evidence justify them.

---

## Failure modes

1. Empty-world cold start
2. Writing becomes secondary
3. Concentrations are misread as trending
4. Performance or battery failure
5. Warm styling trivializes urgency
6. Exact-location abuse and moderation failure
7. Uneven map quality across regions

---

## Decisive recommendation

Build Candidate 4 as the single leading direction, with:

- nearby-first opening
- one invariant beacon
- flat board threads
- one authoritative spatial context
- altitude-only vertical axis
- one obvious contribution action

Reject:

- second synchronized camera
- vertical reply stacks
- engagement ranking
- synthetic event merging
- handcrafted miniature cities
- free-roaming game camera
- black cyberpunk void
- fake activity

### Remaining human decision

> Which real communities, official sources, campaigns, and local use cases will create enough honest initial density for the viewer-first world to deliver value—without fabricating activity or changing Punkto into an authoring-only tool?

The interface should remain viewer-first. The launch strategy should likely be author-first.