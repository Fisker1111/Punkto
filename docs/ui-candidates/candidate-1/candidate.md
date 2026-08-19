# Candidate 1 — Calm Spatial Board

## One-sentence concept

> A calm, dark spatial world where every public message is a precise glowing beacon and every thread opens as a compact board at its real location.

## Status

**Strong benchmark candidate.** The revised mockup is the current reference for precise atom interaction.

## Core experience

The user enters a quiet 3D field of glowing messages anchored in real space. The world is abstract enough to feel distinctly Punkto, but grounded by streets, simplified structures, a ground plane, and exact light-pillar anchors.

The world is primary. Cards appear only when the user selects a message.

## Emotional character

- calm
- precise
- slightly mysterious
- mature
- social without social pressure
- game-like through movement and discovery rather than scores

It should avoid feeling like a developer console, cyberpunk dashboard, or conventional pin map.

## Opening screen

The app opens close to the viewer's current area or last position.

The viewer immediately sees:

- a small number of glowing atom beacons
- a clear spatial ground or structure
- restrained navigation
- no technical node, peer, key, or fingerprint information

A new user should understand that the lights represent messages attached to places.

## World and zoom behaviour

### Far view

Atoms compress into quiet points or density signals. The scene should remain intentional even when sparse.

### Mid view

Individual anchors separate. Threads remain compact and do not overlap neighboring atoms.

### Close view

The exact ground ring, pillar, altitude, and relationship between message and place become visible.

### Selected atom

The atom brightens and its public board appears beside it. The beacon remains fully visible so the board never loses its spatial context.

## Atom and thread behaviour

- one root atom owns one protected spatial volume
- one atom appears as one anchored light
- replies rise in a narrow vertical stack from that root
- inactive stacks remain compact
- selecting the atom expands the thread
- a new reply can appear as a gentle upward light movement
- activity is communicated through warmth, freshness, and motion rather than raw stack height

Guiding rule:

> **At rest: simple. In motion: alive. On touch: revealing.**

## Board interaction

The selected board contains:

- category and location
- distance and altitude where useful
- root message
- author and time as secondary metadata
- public notes or replies
- a clear **Open board** action
- an optional location/focus action only when logically necessary

Avoid hearts, follower counts, avatar piles, popularity indicators, or private-message affordances.

## Writing flow

1. Move or focus the world on a location.
2. Tap the small blue `+` action.
3. Write the message.
4. Confirm the location.
5. Optionally adjust category, floor, or altitude.
6. Place the Punkti.

Advanced spatial controls should be hidden until requested.

## Navigation

Current benchmark navigation:

**Text · Map · + · Settings**

- exactly four actions
- `Map` active in the spatial view
- `+` is a small but unmistakable blue accent
- no oversized social-media compose button

## Strengths

- strongest exact atom and board interaction
- distinctive Punkto beacon language
- relatively feasible in Three.js on mobile
- works with simplified geometry
- naturally preserves atom uniqueness
- avoids conventional social-media aesthetics

## Risks

- can feel abstract or empty when activity is sparse
- may be less immediately friendly to mainstream users
- floating board can dominate the world if oversized
- weak at communicating city or global activity by itself
- dark visual language could drift toward technical or cyberpunk

## Engineering feasibility

**Relative risk: low.**

Suitable techniques include:

- GPU-instanced atom beacons
- simple ground and building geometry
- point-cloud or low-poly structures
- level-of-detail by zoom
- HTML/CSS board cards above the 3D scene
- expanded geometry only for the selected atom

This candidate is a strong fit for the current PWA and Three.js direction.

## Open questions

1. How should the scene remain warm and intentional with only one nearby atom?
2. How much real-world geography is needed beneath the abstract world?
3. Should the secondary card action be Focus, Center here, or omitted?
4. How does this visual language extend to world and city scale?
5. What does the Text view counterpart look like?

## Review plates

- [`candidate-1-01-concept.svg`](candidate-1-01-concept.svg) — initial warm spatial concept
- [`candidate-1-02-revision.svg`](candidate-1-02-revision.svg) — spec-aligned benchmark revision

These SVG plates are lightweight, editable repository versions intended for shared review. High-resolution raster mockups can be added alongside them later.

## Evaluation

Use [`../evaluation-prompt.md`](../evaluation-prompt.md). Save independent reviews in [`reviews/`](reviews/).
