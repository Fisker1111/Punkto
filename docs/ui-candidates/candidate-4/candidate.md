# Candidate 4 — The Living Public World

## Status

**Leading product direction, shipped under Candidate 5 discipline.** Candidate 4 replaces Candidates 1–3 as the primary design hypothesis while preserving them as source explorations:

- Candidate 1 supplies the near/atom experience.
- Candidate 3 supplies the zoom-out awareness architecture.
- Candidate 2 supplies a tightly bounded warmth and readability budget.

**Merge (2026-07-26):** Candidate 5 — The Craigslist (Light 3D) — is merged into this specification as its phasing and shipping doctrine, per the unanimous COMBINE verdict of the OpenRouter fusion review ([`../candidate-5/reviews/openrouter-candidate-5-fusion.md`](../candidate-5/reviews/openrouter-candidate-5-fusion.md)). One document, one identity: the warm, faintly alive public world is the product; the Craigslist doctrine is how it ships. The merge is conditional on three amendments, all applied in this revision:

1. **Freeze semantics, not surfaces** — see [Kernel contracts](#kernel-contracts).
2. **Cheap warmth ships in v1** as frozen liveness grammar — see [Visual warmth](#visual-warmth-within-realistic-engineering-limits).
3. **Delegation is engineered, not hoped** — see [Shipping doctrine](#shipping-doctrine-candidate-5-merge).

Candidate 4 should ship first as a Candidate 1-shaped local MVP under the shipping doctrine below, and earn its way toward the full semantic-zoom vision through the acceptance gates defined in [Implementation phases](#implementation-phases).

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

## The v1 warmth floor (Candidate 5 merge amendment)

Warmth is not a graphics budget and must never be delegated or postponed. In a system with no likes, counts, or feeds, **liveness cues are the only channel that signals "people were here recently."** v1 therefore ships a first-party warmth floor that costs zero assets and negligible milliseconds:

- one restrained **procedural beacon glow**
- a **recency/urgency pulse** derived deterministically from timestamps (kernel-owned semantics; theme-adjustable intensity)
- **authored empty states** and humane microcopy throughout
- deliberate easing on the few transitions v1 keeps
- the decision, everywhere, not to show a scoreboard

These elements are frozen **liveness grammar**, not styling options: their meaning is kernel-owned (see [Kernel contracts](#kernel-contracts)), while their intensity is theme-adjustable. The target is explicit: the warmest candidate at 60 fps on a 2019 phone — cheap to render must never mean quiet to notice. The beacon still glows.

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

## Weak-device behavior — one build, no fallback tier (Candidate 5 merge amendment)

There is no separate fallback build. **One semantic build** serves all devices; weaker hardware receives bounded *presentational* reduction within the same grammar:

- flat 2D MapLibre rendering
- normal symbol beacons
- no extrusion
- no per-frame animation
- full reading and writing parity

Adaptation may change detail, never meaning: beacon, altitude, urgency, ordering, and board semantics are identical on every device. No second grammar may ever exist — a fallback tier is precisely how one authoritative spatial context forks into two products.

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

# Kernel contracts

*(Candidate 5 merge amendment — freeze semantics, not surfaces.)*

The wire format and protocol semantics freeze hard now. The visual grammar is versioned and labelled **provisional for 6–12 months** while the wire format is not. "A frozen target" means known compatibility, not permanent appearance. The full derivation of every item is in the [Candidate 5 fusion review §5](../candidate-5/reviews/openrouter-candidate-5-fusion.md).

## A. Protocol and atom semantics — hard freeze

1. Canonical `p:<spatial>-<id>` form; precision/length semantics of the spatial component; an explicit privacy/precision rule (a bench and a front door must be expressible at different precisions).
2. Altitude contract: stated datum (WGS84 ellipsoidal vs orthometric/geoid), AGL-vs-AMSL discrimination, units, rounding — plus a **mandatory positional/altitude uncertainty field**. "Exact" must not conceal unreliable phone altitude.
3. Signed-atom identity: immutable id, author key, created-at, place, signature scheme; correction, supersession, retraction and tombstone behaviour.
4. Validity/expiry windows. Without ranking, recency-and-validity is the only legitimate ordering, so it must be kernel, not client.
5. Closed relation vocabulary: **replies-to, confirms, disputes, supersedes/resolves**, plus the derivation rule turning relations into displayed state ("3 confirmations, unresolved, 11 days"). Attestation counts permitted; approval counts structurally impossible — a confirmation is a claim about the world, not engagement with a message.
6. Atom kinds, including an **urgency kind requiring mandatory expiry**, with cross-client rendering semantics and a reserved signalling channel **no theme may mute** (redundant text/icon/shape meaning, never colour alone).
7. Ordering semantics: **chronological and spatial only.** This freezes the no-engagement rule into the protocol, not just the UI.
8. Federation envelope: propagation of atoms, corrections, removals and moderation actions between nodes.

## B. Spatial grammar — frozen semantics, unfrozen rendering

9. One authoritative camera, projection, orientation, scale and selected place. No competing miniature world; no vertical-exaggeration parameter exposed to themes, ever.
10. Vertical axis = physical altitude only. Never age, urgency, popularity, reply depth, category or activity. **Light never licenses flattening to 2.5D.**
11. Zoom-ladder semantics: what becomes meaningful at region / district / street / exact-place scale, continuity rules between them, and deterministic aggregation derived from public atom data so all conformant clients render identical structure.
12. Query contracts: bbox+altitude+time → atoms, with deterministic pagination and dedup; and **bbox+zoom → aggregates** with visible provenance and freshness, shipped even if implemented naively in-process. Aggregates are projections over atoms, never replacements; decorative aggregates must never mask sparse data.
13. Beacon contract: every beacon resolves to an exact anchor; selection, occlusion, clustering and overlapping-altitude behaviour deterministic and accessible; customization may never detach a beacon from its anchor.
14. Board contract: reading happens in a flat screen-space surface bound to the selected place. Thread nesting and status are board semantics, never world geometry. Explicit render-boundary separation between the 3D layer and the HTML overlay; no 3D text for threads.
15. Liveness grammar: recency/urgency cues derived deterministically from timestamps — kernel-owned semantics, theme-adjustable intensity.

## C. Extension and delegation contracts

16. Versioned **theming contract stated as prohibitions first**: themes may change material, colour, typography, motion, detail density; themes may not change axis meaning, aggregation truthfulness, ordering, relation semantics, urgency legibility, or add any engagement affordance.
17. Layered stability model: protocol highly stable; spatial-query and renderer contracts versioned; visual tokens free to evolve.
18. Render-extension boundary: extensions declare cost and capabilities and fail back to the complete baseline; arbitrary executable presentation arriving from federated nodes or atoms sits outside the trust boundary.
19. **Performance-budget contract**: a theme or fork is "grammar-conformant" only if it passes the named reference-device budget. This makes "cheap-to-render must not mean quiet-to-notice" testable rather than aspirational.
20. A published **conformance suite** — the actual frozen artifact. Artifacts hold the line when prose doesn't.
21. Accessibility equivalence: every atom reachable and legible without the 3D world (navigable text representation, screen readers, keyboard, reduced motion, non-colour status cues) without creating a second feed product.
22. Every atom resolvable as a text-first URL plus a server-rendered static preview card.

## D. Operations and governance

23. Basemap contract: provider neutrality, attribution, projection compatibility, privacy, cache behaviour, degraded operation, and exactly what a self-hoster must supply. (Whether Punkto should have a basemap at all remains an [open human question](#remaining-human-product-decision); the contract must be written either way.)
24. Media policy: whether atoms may carry attachments at all, and if so, hard caps, re-encoding limits and remote-cache expiry.
25. Kernel-level moderation tools (delist, precision-blur) plus removal propagation. Abuse cannot be delegated to pull requests.
26. Key backup and rotation; documented node budgets (town size, concurrent readers, query latency, storage growth, backup/restore, degraded behaviour).
27. RFC process and grammar versioning.

---

# Shipping doctrine (Candidate 5 merge)

Candidate 5's three lights survive intact as the phasing chapter of this specification, amended per the fusion review:

## Light client

One build for all devices, instant on 3–5-year-old phones over mediocre connections. No asset downloads, no bespoke 3D scenery, no rendering feature that needs a performance budget meeting — with the explicit correction that **procedural warmth is free**: a glow computed in a shader costs the operator nothing and the client almost nothing, so "light" is a constraint on *assets and dependencies*, not on *warmth*. "No performance budget meeting" means a testable floor (see Kernel contracts §19), not a ban on measurement.

## Light server

Many operators will run the Docker node on their own hardware — a home server, a small VPS, a Raspberry Pi. The defensible doctrine is precise: **no server-side content or asset dependencies** — no tile servers the operator must run, no required media hosting, no GPU-backed rendering assumptions. Atom serving is never the bottleneck; what breaks a home server first is the basemap/media policy, reachability operations, query amplification during urgent-event bursts, and moderation load — all addressed in Kernel contracts §23–26 and the failure modes below.

## Light governance — delegation engineered, not hoped

"Others will build richer graphics later" is a pathway the kernel ships, not a hope the kernel holds. The empirical record is unambiguous: community contributions cluster at the periphery (themes, translations, packaging), and richness in federated ecosystems historically arrives as **hard forks, not merged PRs** — which without contracts defaults to grammar fragmentation, the exact opposite of one authoritative context. Therefore the kernel team itself ships:

- the theming contract stated as prohibitions (Kernel contracts §16)
- **at least one official rich (non-default) reference theme** exercising every hook
- the published **conformance suite** (§20)
- the named **reference-device performance budget** (§19)
- continued first-party ownership of the baseline experience and this specification's direction

The success metric is a hierarchy, not a single number: v1 gates on first-glance comprehension, urgent-post p95 under 20 s on the reference device, and urgency recognition; ongoing health is tracked through time-to-look-up plus one ambient counter-metric — **return visits with no notification of any kind** — and the share of atoms read by someone who does not know the author. Time-on-screen and anything engagement-shaped remain forbidden.

---

# Implementation phases

## MVP — local Candidate 4 shell (v1, under the shipping doctrine)

Ship a Candidate 1-shaped local experience inside Candidate 4's architecture:

- nearby-first MapLibre world
- warm 2D/2.5D styling
- invariant beacon with the **v1 warmth floor** (procedural glow, timestamp-derived recency pulse, authored empty states)
- selected board bottom sheet
- public replies in 2D UI
- fast `+` writing flow — with compose **independent of map/scene load**, local signing, explicit positional uncertainty, offline queue with retry, no login wall
- categories and sober urgent register (urgency kind with mandatory expiry per Kernel contracts §6)
- freshness and lifecycle foundations (validity/expiry per §4)
- basic clustering plus the naive **aggregate bbox+zoom query** (§12)
- one-build weak-device behavior and reduced-motion support

v1 also ships the **delegation scaffolding** as first-party deliverables, not afterthoughts:

- theming contract stated as prohibitions (§16)
- one official rich (non-default) reference theme exercising every hook
- the published visual conformance suite (§20)
- the named reference-device performance budget (§19)

### v1 acceptance gates (replacing "earn the vision through evidence" prose)

Measured on the named reference device — a mid-2019 Android over throttled 4G:

1. **First-glance comprehension:** a cold newcomer can state what Punkto is ("public notes people left around here, and I can leave one too") and does not call it unfinished.
2. **Urgent-post p95 < 20 s** wall clock from app-open to signed urgent atom accepted.
3. **Urgency recognition:** a cold observer notices the flood beacon and reads it as urgent within seconds.
4. **Unprompted return visits** with no notification of any kind.

Pass: proceed to Phase 2. Fail on urgency or comprehension: redesign the cheap-warmth grammar before anything else ships.

## Phase 2

After the v1 gates pass on real usage evidence:

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
- invariant beacon with the v1 warmth floor (procedural glow, timestamp-derived pulse, authored empty states)
- 2D board threads
- fast contribution action with compose independent of map load
- one authoritative map camera/projection
- vertical axis reserved for altitude
- the kernel contracts (freeze semantics, not surfaces)
- the delegation scaffolding (theming prohibitions, reference rich theme, conformance suite, reference-device budget)

## Postpone

- elaborate regional Flow behavior
- rich 3D environments
- precise altitude promises
- global live channel
- advanced district visualizations
- any warmth that costs an asset download

## Reject

- independently synchronized map and 3D cameras
- reply height in the world
- popularity and engagement ranking
- automatic merging of unrelated atoms
- handcrafted miniature cities
- free-roaming game camera
- black cyberpunk void
- fake activity used to disguise empty areas
- a separate fallback build or second grammar for weak devices
- flattening to 2.5D in the name of lightness
- delegating the v1 warmth floor or the baseline experience to future community PRs

## Remaining human product decision

The UI should remain viewer-first, while the launch strategy should probably be author-first.

The unresolved decision is therefore:

> **Which real communities, official sources, campaigns, and local use cases will create enough honest initial density for the viewer-first world to deliver value—without fabricating activity or changing Punkto into an authoring-only tool?**

Two further questions the Candidate 5 fusion panel could not resolve, recorded as explicitly open rather than silently decided:

1. **Should Punkto have a basemap at all?** Positions ranged from "no basemap — procedural, atom-derived ground" (removes the biggest operator dependency and the GIS-console trap) to "legible geography is a requirement" (the bench is meaningless without the canal), with a middle position: budget it via prebuilt vector tiles on Pi-class hardware. Either way, the basemap contract (Kernel contracts §23) must be written.
2. **Does urgency deserve privileged prominence, given self-declared urgency is gameable?** The fused position ships it — but only with mandatory expiry, provenance, kernel-level moderation tools, local scoping, and federation propagation of removals (Kernel contracts §6, §25). The governance proof remains owed.

## Evaluation

The full multi-model fusion that produced this candidate is preserved in [`reviews/openrouter-candidate-4-fusion.md`](reviews/openrouter-candidate-4-fusion.md).

The Candidate 5 merge review (COMBINE, posture b) whose verdict this revision applies is preserved in [`../candidate-5/reviews/openrouter-candidate-5-fusion.md`](../candidate-5/reviews/openrouter-candidate-5-fusion.md).