# Candidate 3 — Flow World

## One-sentence concept

> A viewer-first live world channel where semantic zoom moves continuously from global activity to city situations, local 3D beacons, and exact public atoms and threads.

## Status

**Strong long-term architecture candidate.** Broadest product vision and strongest large-scale usefulness.

## Core experience

Punkto opens as a calm live view of what the public world is saying now. The viewer does not begin with a conventional feed or a complex 3D city. They begin with a familiar geographic overview that reveals more human detail as they approach.

The product combines:

- the shared attention and ease of old flow television
- live, user-generated public messages
- exact geographic anchoring
- direct access to every original atom and thread

The viewer may lean back and watch, or interrupt the flow and explore at any moment.

## Product statement

> **Punkto is a live window into the public world: zoom from global activity to the exact message left at a real place.**

## Viewer-first behaviour

The interface is optimized for the person trying to understand what is happening.

Example:

A taxi driver in Nairobi posts:

> **INFO — Flooding here**

A nearby viewer sees a clear live spatial signal on the affected road. The message is not silently merged with unrelated atoms. Independent reports remain independent unless they are actual replies to the same root atom.

A threaded infrastructure example:

> **INFO — Fire hydrant not working**
>
> “I confirm, it has not been working for a week.”
>
> “County has been informed.”

The replies form one public board at the original atom's exact location.

## Semantic zoom

### 1. World view — 2D

The viewer sees:

- a calm global or regional map
- soft activity pulses around cities and areas
- category and freshness signals
- selected live headlines
- no individual atom clutter

Individual atoms are represented as aggregates appropriate to the scale.

### 2. Country and city view — 2.5D

As the viewer zooms closer:

- roads and city structure appear
- terrain gains slight depth
- activity separates into districts
- clusters become situations and local signals
- the camera begins to tilt naturally

### 3. Neighborhood view — 3D

At local scale:

- simplified buildings rise
- individual atoms become anchored light-pillar beacons
- altitude and floors become meaningful
- independent atoms separate
- root atoms with replies become compact vertical stacks

### 4. Atom view — spatial board

Selecting an atom pauses the flow:

- the exact beacon remains visible
- the board opens
- the root and replies are readable
- the viewer can contribute, follow the place, or return to Flow

Guiding hierarchy:

> **Far away: patterns. Closer: situations. Nearby: messages. Selected: conversation.**

## Old and new flow

### Old flow qualities

- one understandable item at a time
- shared live attention
- clear geographic headlines
- a calm “now playing” rhythm
- limited choice when the viewer wants to lean back

### New flow qualities

- public messages from people actually present
- free geographic exploration
- zooming from world to atom
- user-selected categories and areas
- direct inspection of the original signed records
- public contribution from the scene

## Visual character

- full-screen geographic world
- dark but warm atmosphere
- broadcast-style typography
- minimal permanent chrome
- calm camera transitions
- geographic pulses and regions at distance
- light-pillar atoms when close
- information cards placed low like captions rather than covering the world

## Atom and thread behaviour

- independent atoms always remain logically independent
- density and clustering may simplify distant display but never change underlying meaning
- one root atom owns its replies
- a thread appears as a narrow protected stack
- fresh replies increase warmth and visibility
- selected threads expand; unselected threads remain cheap and compact

## Interaction model

Possible primary gestures:

- tap to pause and inspect
- swipe for the next live item
- pinch or zoom to reveal larger or smaller geographic context
- zoom in to transition from 2D to local 3D
- select a beacon to open the board
- tap `+` to contribute at the current location

The exact navigation is still open. Candidate 3 may justify a larger redesign than the shared Text · Map · + · Settings baseline.

## Writing flow

Although the candidate is viewer-first, contributing must remain simple:

1. Tap `+` or Contribute.
2. Write the message.
3. Confirm the current spatial anchor.
4. Optionally add category, floor, or altitude.
5. Publish and return immediately to the live world.

A reporter should not need to construct a synthetic event or headline.

## Engineering architecture

Different scales use different representations of the same underlying atoms:

| Scale | Viewer sees | Likely rendering model |
|---|---|---|
| World | regional activity | aggregated 2D map layer |
| Country | cities and corridors | clusters and simplified lines |
| City | district signals | batched or instanced signals |
| Street | buildings and beacons | local 3D geometry |
| Atom | root message and replies | expanded selected object + HTML UI |

This follows the useful rendering discipline demonstrated by large Three.js geospatial systems: batch similar objects, use instancing, avoid rebuilding geometry, and change visual state through buffers, materials, visibility, and level-of-detail.

Likely stack:

- MapLibre for world and regional geography
- Three.js for local spatial rendering
- viewport-appropriate server or client aggregation
- instanced beacons and batched flow lines
- HTML/CSS message and board layers
- geometry loaded only around the active local view

## Strengths

- strongest world-to-atom product architecture
- greatest usefulness for live local awareness
- viewer-first rather than posting-first
- can absorb Candidate 1's atom interaction naturally
- supports both passive discovery and active exploration
- technically scalable through semantic zoom and level-of-detail
- highly distinctive long-term Punkto identity

## Risks

- highest interaction-design complexity
- scale transitions may feel confusing or technically fragile
- can become noisy or alarmist if ranking is poor
- “Flow” can accidentally resemble algorithmic social media
- automated selection must not imply synthetic certainty or silently merge records
- more difficult to communicate in one static mockup

## Engineering feasibility

**Relative risk: medium.**

It is ambitious but plausible because the entire planet is not rendered in detailed 3D. The challenge is orchestration between representations, not raw full-world geometry.

## Open questions

1. Does Punkto open nearby, at the last location, or on a broader world channel?
2. What determines which atom becomes “now playing” without creating an opaque engagement algorithm?
3. At which zoom ranges do 2D, 2.5D, and 3D transitions occur?
4. What is the simplest navigation that supports both lean-back viewing and free exploration?
5. How should sparse regions be presented without appearing dead?
6. How does the system distinguish urgent, useful, and ordinary social content without editorial overreach?

## Review plates

- [`candidate-3-01-overview.svg`](candidate-3-01-overview.svg) — wide architecture and semantic-zoom concept
- [`candidate-3-02-mobile.svg`](candidate-3-02-mobile.svg) — mobile live-world concept

These SVG plates are lightweight, editable repository versions intended for shared review. High-resolution raster mockups can be added alongside them later.

## Evaluation

Use [`../evaluation-prompt.md`](../evaluation-prompt.md). Save independent reviews in [`reviews/`](reviews/).
