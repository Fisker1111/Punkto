# Candidate 4 — The Living Public World

## Status

**Leading product direction.** Candidate 4 replaces Candidates 1–3 as the primary design hypothesis while preserving them as source explorations:

- Candidate 1 supplies the near/atom experience.
- Candidate 3 supplies the zoom-out awareness architecture.
- Candidate 2 supplies a tightly bounded warmth and readability budget.

Candidate 4 should ship first as a Candidate 1-shaped local MVP and earn its way toward the full semantic-zoom vision through usage and performance evidence.

## One-sentence concept

> Punkto is a calm, warm public world you zoom into—from the shape of activity across a region down to a single message pinned at one exact place—where understanding the world and leaving a message happen in the same continuous place.

## Product promise

> **Punkto opens by helping someone understand the world; contribution remains one obvious action away.**

This does not mean writing is unimportant. It means the user immediately receives value before posting, while writing never requires entering a separate creator destination.

The interface remains viewer-first. The launch strategy may be author-first: communities, campaigns, official imports, and deliberate local use cases seed the world without changing the product's personality.

## Emotional promise

Opening Punkto should feel like stepping to a window and quietly seeing the public world around you as it is now—not a feed shouting for attention, not a map bristling with technical data, and not a simulated game world.

The world feels warm, calm, legible, and faintly alive. Messages glow where they belong. Leaving a message should feel as natural as pointing at a place and saying, “Look.”

## Governing principles

1. **The message is the object; geography is its context.** Scenery, extrusion, and motion remain visually subordinate to the atom.
2. **Zoom reveals meaning, not merely magnification.** Region shows patterns, district shows concentrations, street shows messages, and selection shows conversation.
3. **See first, contribute instantly.** Punkto provides value on opening, while one unmistakable action always lets the user add a message.
4. **One authoritative spatial world.** Map, camera, projection, beacons, and local 3D must share one spatial truth without a visible renderer handoff.
5. **The vertical axis means physical altitude only.** Replies never use world height.
6. **Every beacon represents a real independent atom.** Distant aggregation changes presentation, never meaning.
7. **No engagement machinery.** No ranking by outrage, dwell time, follower popularity, likes, or addictive interaction.

## Candidate 4 must never become

- **A feed:** no infinite-scroll default, trending page, synthetic stories, or engagement-ranked channel.
- **A GIS or operator console:** no cold void, persistent technical toolbars, or exposed node and key machinery in the primary experience.
- **A dollhouse:** no handcrafted miniature world, global bespoke assets, simulated citizens, or scenery more important than messages.

---

# First five seconds

## Default opening

Punkto opens **nearby-first** using this fallback chain:

1. current location, when permitted
2. last viewed place
3. coarse regional location
4. a user-selected home place

The world opens around the street/district threshold:

- gently pitched, around 35–45 degrees
- warm 2D or restrained 2.5D map context
- nearby real beacons already visible
- building footprints readable, with extrusion only beginning at close scale
- one small place/context pill
- one recenter action
- one persistent `+` contribution action

Technical status, profile machinery, keys, and settings stay out of the first impression.

A non-technical user should be able to say:

> “These are public notes people left around here, and I can leave one too.”

If the first reaction is only “It is a map” or “It is a game,” the opening has failed.

## Location permission

Location is requested contextually:

> “Allow location to show what people have left around you.”

There is no hard permission wall. Without permission, Punkto opens at the last viewed or chosen place.

## Empty opening

An empty neighborhood is shown honestly:

- warm map context
- no fabricated atoms
- optional directional hint toward the nearest real activity
- one quiet invitation near the contribution control: **Leave the first note here**

No counters, confetti, fake population, or needy onboarding.

---

# Core interaction architecture

```text
Open → Understand → Explore → Select → Read → Contribute → Return
```

## Open

Land nearby at a warm, gently pitched map scale. Real beacons are already visible when present.

## Understand

The visual grammar should be learned by looking:

- beacon = a public message exists here
- glyph/form = message kind
- brightness = freshness
- sober upright form = urgent attention
- stem and floor chip = physical height

## Explore

Zoom is the primary semantic navigation axis:

- zoom out: beacons become district concentrations and then regional activity
- zoom in: concentrations resolve into individual atoms and local spatial context

There is no required hard switch between Map, 3D, and Flow.

## Select

Tap a beacon:

- selected beacon brightens
- its exact anchor remains visible
- nearby context softens
- a readable board rises from the bottom

## Read

The root message and replies remain in flat 2D UI. Replies do not occupy geographic height.

## Contribute

Tap `+`:

- a provisional beacon appears at the current anchor
- the compose sheet opens with the text field focused
- the user writes and publishes
- the sheet collapses back into the same world

Writing and viewing are two gestures on one continuous surface, not separate products.

## Return

Dismiss the board or writing sheet to return to the same camera position. Recenter is a camera move, not a navigation reset.

---

# Semantic zoom contract

## Region — patterns

Approximate range: broad regional and country scales.

Visible:

- warm base geography
- soft activity pulses
- broad corridors or concentrations of recent atoms
- sober urgent signals that remain noticeable farther out

Hidden:

- individual messages
- buildings
- atom text
- thread details

A pulse means:

> More recent independent public messages exist in this area.

It does **not** mean popular, important, trending, or one automatically generated event.

## District — concentrations

Approximate range: city and district scales.

Visible:

- roads and district structure
- flat building footprints
- honest concentration markers with counts
- category hints where useful

Independent atoms may be summarized visually because they overlap, but they are never silently merged into a synthetic story.

Selecting a concentration zooms toward it; it does not open a fabricated combined post.

## Street — messages

Approximate range: local neighborhood and street scales.

Visible:

- individual beacons
- muted building extrusion
- parks, water, roads, and physical context
- real altitude stems and floor/elevation labels when available

True 3D begins mainly here. Buildings rise gently from footprints as the user approaches.

## Atom — conversation

Selecting one beacon:

- pauses ambient movement
- preserves the exact ground or building anchor
- opens the root board in a draggable bottom sheet
- shows replies, author, time, source, and physical placement as secondary context
- provides reply, follow-place, and contribution actions where appropriate

## Transition behavior

- eased cross-fades and scale transitions
- no hard 2D/3D button required
- no inter-level loading-screen feeling
- buildings rise from footprints rather than popping in
- different data representations may be used internally, but the camera and projection remain authoritative and continuous

---

# The invariant atom beacon

The beacon is the one visual object that always means:

> **A public message exists here.**

## Base form

A compact luminous seed or droplet attached by a thin stem to its exact physical anchor.

The beacon should remain recognizable as it simplifies:

```text
selected beacon → local beacon → small dot → district contribution → regional pulse
```

## Category

Category uses both **shape/glyph and color**, never color alone.

Possible examples:

- everyday note: soft rounded seed
- infrastructure/info: structured glyph
- warning: sober upright chevron or banner
- event/community: distinct but restrained glyph

## Freshness

Freshness is communicated primarily through:

- brightness
- warmth
- one gentle ripple when created or updated

Old atoms settle into calm, readable markers rather than disappearing solely because they are old.

## Urgency

Urgent content uses a sober visual register:

- upright form
- steady slow pulse
- clear warning glyph
- persistent visibility across broader zoom levels
- muted serious color rather than playful neon or screaming red

## Thread presence

A root with replies shows only a compact count or notch on the map. Thread content never expands into the 3D world.

## Altitude

Physical height is represented through:

- the stem from real anchor to message point
- explicit chip such as `5th floor` or `≈18 m`
- uncertainty where altitude is estimated

The vertical axis has no other meaning.

## Selection

On selection:

- beacon brightens and subtly lifts visually
- anchor ring appears at the exact point
- neighbors soften
- board opens while the spatial relationship remains visible

---

# Thread and board model

## Final thread representation

Replies appear in a **draggable bottom-sheet board** with sequential 2D cards.

- root atom remains pinned and visually dominant
- replies are indented or visually subordinate
- long threads scroll within the board
- ten or more replies never alter map geometry
- a new reply triggers one soft beacon ripple and a subtle card entrance

This avoids confusing reply order with altitude and preserves narrow-screen readability.

## Board levels

- collapsed preview: root message and brief metadata
- medium sheet: root plus recent replies
- expanded sheet: full board and composition controls

The board should not permanently obscure the world or remove geographic context.

---

# Viewer-first navigation

## Permanent controls

The primary spatial view should expose as little permanent chrome as possible:

- current place/context pill
- recenter / Here
- unmistakable `+`
- optional entry to Text/accessible list view

Technical settings live behind a secondary menu or identity area, not as equal-weight primary navigation.

## Nearby and world

Nearby is the default. World/region awareness is reached through:

- natural pinch zoom
- tapping the place/context pill
- an Explore option if a direct shortcut proves useful

The world does not require its own engagement-ranked “Live” feed.

## Text view

A text/list representation remains valuable for:

- accessibility
- low-power devices
- weak network conditions
- fast scanning

It should represent the same spatial atoms, not become a separate algorithmic social feed.

---

# Writing flow

## Fast path

A taxi driver should be able to publish **Flooding here** quickly:

1. Tap `+`.
2. Provisional beacon appears at the current location.
3. Compose sheet opens with keyboard and text field ready.
4. Choose category only when needed; everyday note is the default.
5. Publish.
6. Receive subtle visual/haptic confirmation.
7. Return immediately to the same viewer state.

## Location confirmation

The map remains visible behind the sheet so the user sees the proposed anchor.

A soft uncertainty radius may communicate GPS precision without turning the flow into surveying software.

## Progressive disclosure

Advanced controls are hidden under **Adjust place & height**:

- drag/nudge anchor
- choose floor
- enter approximate height
- use device altitude when useful

## Public notice

Use a clear but compact message:

> Public and signed. Anyone can read this.

A stronger first-use explanation may appear once, but repeated posting should not require a modal warning.

## Identity

Signing happens automatically with the current device identity. Author information is visible but secondary.

---

# Shared scenario behavior

## Everyday

> Bench by the canal has sun until 7 pm.

- region: no individual presentation
- district: contributes faintly to activity
- street: warm everyday beacon near the canal
- selected: small board with time relevance
- lifecycle: may expire or retire after relevance ends

## Infrastructure thread

> Fire hydrant not working.
>
> I confirm. It has not been working for a week.
>
> County has been informed.

- district: infrastructure concentration only when density justifies it
- street: infrastructure beacon with reply count
- selected: root plus sequential replies
- lifecycle: persistent until resolved or explicitly updated
- official/source marking: clear but visually restrained

## Urgent report

> Flooding here — road blocked.

- region/district: sober urgent signal remains visible farther out
- street: warning beacon anchored to the affected road location
- selected: root, confirmations, updates, and timestamps
- lifecycle: requires freshness/confirmation rules so stale warnings do not mislead
- independent reports remain independent unless they are actual replies to the same root

---

# Sparse and dense regions

## Completely empty

- honest warm geography
- invitation to leave the first note
- optional direction toward nearest real activity
- no fake atoms

## One atom

The world should be composed intentionally around the single beacon so it feels meaningful rather than broken.

## Three unrelated atoms

Each remains visually separate and category-readable. No artificial grouping beyond collision-safe distant presentation.

## Highly active neighborhood

- collision-safe clustering at district scale
- individual atoms separate only when spatially legible
- selected atom remains dominant
- text/list view offers another readable route

---

# Transparent content selection

Permitted signals:

- geographic proximity
- recency
- explicit urgency category
- user-selected categories
- active replies as freshness, not popularity
- official/source presence
- saved or followed places

Forbidden signals:

- click optimization
- outrage or controversy
- dwell-time maximization
- follower popularity
- reaction totals as ranking
- opaque engagement scoring

When Punkto surfaces an atom, it should be able to explain plainly:

> Shown because it is near you and recent.

---

# Visual warmth within realistic engineering limits

Warmth should come from inexpensive, scalable choices:

- warm neutral daytime map palette
- deep blue and warm-window evening palette after dark
- humanist typography
- generous spacing
- calm easing
- subtle ambient lighting
- muted building extrusion from vector data
- readable water and park styling
- restrained haptics
- humane message language

Punkto should support day and evening appearances, but never become a black void or neon cyberpunk world.

Environmental fidelity remains intentionally below the beacon's visual importance.

---

# Engineering architecture

## One authoritative camera and projection

MapLibre should remain the authoritative map camera and projection.

Local 3D objects should render inside the same spatial context, for example through a MapLibre custom layer. Three.js may be used internally with MapLibre's projection matrix, but there should not be an independently controlled second scene and camera.

The requirement is **one spatial truth with no visible handoff**.

## Rendering by scale

- region: MapLibre data-driven activity layers
- district: MapLibre clusters/concentrations and flat footprints
- street: restrained extrusion and instanced beacons
- selected atom: local highlight plus HTML/CSS board

## Level of detail

- render only viewport-relevant individual atoms
- aggregate distant atoms per tile or spatial cell
- use instanced sprites/quads for repeated beacons
- load richer local geometry only at close zoom
- keep replies entirely out of 3D geometry

## Weak-device fallback

- flat 2D MapLibre
- normal symbol beacons
- no extrusion
- no per-frame animation
- full reading and writing parity

Depth is optional; the product is not.

## Reduced motion

- static beacons
- instant or short transitions
- no ripples or pulses

## Offline and unreliable networks

- cache last viewed tiles and atoms
- show honest last-updated state
- queue signed writes locally when appropriate
- publish when connectivity returns

## Main technical risks

1. smooth semantic zoom on ordinary Android hardware
2. consistent custom-layer performance and battery behavior
3. variable global building/map data quality
4. honest and usable altitude/floor placement
5. collision-safe atom presentation at real density

These should be proven before committing to full Flow World behavior.

---

# Implementation phases

## MVP — local Candidate 4 shell

Ship a Candidate 1-shaped local experience inside Candidate 4's architecture:

- nearby-first MapLibre world
- warm 2D/2.5D styling
- invariant beacon
- selected board bottom sheet
- public replies in 2D UI
- fast `+` writing flow
- categories and sober urgent register
- freshness and lifecycle foundations
- basic clustering
- weak-device 2D fallback
- reduced-motion support

## Phase 2

After performance and usage evidence:

- district concentration blooms
- regional activity pulses
- richer custom-layer beacons
- saved/followed places
- direct Explore/world view
- improved official-source language
- refined day/evening ambient appearance

## Long-term

- fully continuous region-to-atom semantic flow
- mature ambient public awareness
- reliable altitude/floor representation
- cross-region patterns without synthetic event creation

---

# Failure modes

1. **Cold-start death spiral:** viewer-first world has too little real content.
2. **Writing becomes secondary:** users look but do not contribute, worsening sparsity.
3. **Semantic zoom resembles trending:** concentrations are misunderstood as ranked importance.
4. **Performance failure:** local depth, transitions, or animations drain battery or stutter.
5. **Warmth trivializes urgency:** serious reports fail to cut through.
6. **Exact-location abuse:** harassment, spam, and geo-doxxing lack adequate governance.
7. **Map quality inequality:** some places look rich while others degrade badly.

---

# MVP validation brief

Before full implementation, build one seeded real-neighborhood prototype containing approximately 30 atoms, including:

- everyday canal/bench message
- broken hydrant thread
- urgent flooding reports
- one real altitude/floor example
- one dense cluster
- one empty nearby area

Test on ordinary 2–3-year-old Android and iPhone devices.

Measure:

1. Can users explain Punkto after five seconds?
2. Do they understand that a beacon is a public message at a place?
3. Can they distinguish root atom, replies, and physical altitude?
4. Does urgent information read as serious?
5. How quickly can they post **Flooding here**?
6. Is map interaction smooth and battery behavior acceptable?
7. Does an empty area feel inviting rather than broken?

---

# Decisive recommendation

## Build

- Candidate 4 shell
- nearby-first spatial opening
- invariant beacon
- 2D board threads
- fast contribution action
- one authoritative map camera/projection
- vertical axis reserved for altitude

## Postpone

- elaborate regional Flow behavior
- rich 3D environments
- precise altitude promises
- global live channel
- advanced district visualizations

## Reject

- independently synchronized map and 3D cameras
- reply height in the world
- popularity and engagement ranking
- automatic merging of unrelated atoms
- handcrafted miniature cities
- free-roaming game camera
- black cyberpunk void
- fake activity used to disguise empty areas

## Remaining human product decision

The UI should remain viewer-first, while the launch strategy should probably be author-first.

The unresolved decision is therefore:

> **Which real communities, official sources, campaigns, and local use cases will create enough honest initial density for the viewer-first world to deliver value—without fabricating activity or changing Punkto into an authoring-only tool?**

## Evaluation

The full multi-model fusion that produced this candidate is preserved in [`reviews/openrouter-candidate-4-fusion.md`](reviews/openrouter-candidate-4-fusion.md).