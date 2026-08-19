# Candidate 2 — The Living Miniature

## One-sentence concept

> A warm, game-like miniature of the real world where simplified neighborhoods contain glowing public messages and threads.

## Status

**Active exploration candidate.** Strongest in immediate warmth and social accessibility.

## Core experience

The viewer looks down into a simplified, angled 3D neighborhood. Roads, buildings, parks, water, and paths are immediately recognizable. Punkti appear as warm lights attached to real locations.

The useful inspiration from games such as *The Sims* is not characters or simulation. It is the instant readability and curiosity of a lived-in miniature world.

## Emotional character

- warm
- welcoming
- playful
- calm
- curious
- socially approachable
- mature rather than cartoonish

The user should feel:

> “Let me look around and see what is happening here.”

## Opening screen

The app opens on a compact neighborhood scene near the viewer.

The viewer immediately sees:

- recognizable streets and building volumes
- warm windows and soft ambient light
- a few glowing Punkti
- restrained navigation
- a clear sense that places contain stories

The scene should feel inhabited without requiring animated people.

## Visual world

The environment uses simplified geographic forms:

- extruded or low-poly buildings
- softened roads and paths
- simple trees and street elements
- readable water and terrain
- warm ambient lighting
- reusable assets rather than bespoke city models

The geography supplies structure. Punkto supplies the visual identity.

Buildings should remain muted enough that the messages are the hero.

## World and zoom behaviour

### City view

Detailed buildings simplify into readable districts and pools of activity.

### Neighborhood view

The miniature world becomes the main exploration surface. Separate locations and building relationships are easy to understand.

### Close view

The viewer sees exact atom placement on a street, roof, façade, courtyard, or floor.

### Selected atom

The camera gently rotates or moves toward the location. The selected stack expands and a compact public board appears while the miniature world remains visible.

## Atom and thread behaviour

- one message is one warm anchored light
- a thread is a short vertical stack from the same root atom
- nearby independent atoms stay separate
- fresh messages gently brighten or release a small upward spark
- active threads may become warmer, not aggressively larger
- altitude can be understood relative to visible buildings

## Interaction model

- drag to move through the neighborhood
- rotate and tilt within safe, understandable limits
- tap a Punkti to focus it
- tap a building or empty area to inspect nearby messages or begin placement
- zoom out to simplify the world rather than retaining all detail

## Writing flow

1. Navigate to the place.
2. Tap `+`.
3. Write the message.
4. Confirm the anchor.
5. Optionally adjust floor, altitude, or category.
6. Place the Punkti and see it become part of the miniature.

The flow should feel like placing something in a world, not completing a GIS form.

## Navigation

Current shared baseline:

**Text · Map · + · Settings**

The world itself should carry most of the interaction. Permanent UI chrome should stay restrained.

## Strengths

- easiest candidate for ordinary users to understand
- strongest warmth and game-like curiosity
- makes buildings, floors, courtyards, and streets legible
- gives users an emotional reason to explore
- can make sparse early activity feel like part of a designed world

## Risks

- highest asset and world-generation burden
- could become too cute, generic, or toy-like
- realistic worldwide consistency is difficult
- environment can overshadow the messages
- detailed scenes may harm performance and battery life
- mockups can promise a fidelity that a mobile PWA cannot deliver

## Engineering boundaries

Candidate 2 is **not a simulated city**.

Initial versions should exclude:

- animated citizens
- traffic simulation
- interiors and furniture
- complex physics
- photorealistic shadows
- unique assets for every building
- heavy weather systems

Plausible techniques include:

- simplified building extrusion from map data
- reusable instanced trees and street objects
- limited lighting and baked-looking materials
- aggressive level-of-detail
- HTML/CSS board overlays
- local geometry only within the active neighborhood

## Engineering feasibility

**Relative risk: medium to high.**

This can remain a PWA only if Punkto designs the illusion of a living world rather than attempting a complete simulated city.

## Open questions

1. How abstract can buildings be while remaining recognizable?
2. Can the world feel warm without requiring expensive assets?
3. What is the reduced-detail fallback on weaker devices?
4. Does the miniature remain mature enough for warnings and infrastructure reports?
5. Should this be a full product architecture or primarily a visual influence on another candidate?

## Review plate

- [`candidate-2-01-mobile.svg`](candidate-2-01-mobile.svg) — warm miniature neighborhood concept

This SVG plate is a lightweight, editable repository version intended for shared review. A high-resolution raster mockup can be added alongside it later.

## Evaluation

Use [`../evaluation-prompt.md`](../evaluation-prompt.md). Save independent reviews in [`reviews/`](reviews/).
