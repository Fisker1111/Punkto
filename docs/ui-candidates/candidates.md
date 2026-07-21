# Punkto PWA — UI Design Candidates

## Purpose

This folder is the shared design room for humans and AI reviewers evaluating the next high-level Punkto PWA interface.

The work focuses on:

- visual identity
- spatial interaction
- social acceptance
- navigation and button hierarchy
- message and thread presentation
- mobile usability
- engineering feasibility

## Core product definition

> **Punkto is a living geospatial world made from public messages anchored in real space.**

The message is the primary social object. The author is secondary. Punkto does not initially depend on private messaging, followers, profile popularity, or social-status metrics.

## Shared design principles

1. **Message-first** — places and messages lead; profiles do not.
2. **Spatial truth** — every atom remains anchored to its real location and altitude.
3. **Warm and social** — inviting and slightly game-like, not cold cyberpunk infrastructure.
4. **Calm** — activity feels alive without becoming noisy or addictive.
5. **Public-board model** — replies are public notes attached to a root atom.
6. **No silent merging** — independent atoms remain independent.
7. **Progressive complexity** — advanced identity, node, altitude, and technical controls stay out of first use.
8. **Mobile-first feasibility** — the design must remain plausible on ordinary mobile hardware and in a PWA.
9. **Vertical means altitude** — reply order never uses geographic height.
10. **No engagement ranking** — proximity, recency, urgency, chosen categories, and official sources may guide visibility; popularity machinery may not.

---

# Leading direction

## [Candidate 4 — The Living Public World](candidate-4/candidate.md)

> **Punkto opens by helping someone understand the world; contribution remains one obvious action away.**

Candidate 4 is now the leading product direction. It is not a loose visual blend; it has one coherent architecture:

- **Candidate 3** supplies semantic zoom from region to atom.
- **Candidate 1** supplies the invariant beacon and selected-board interaction.
- **Candidate 2** supplies a tightly bounded warmth and environmental-readability budget.

### Core Candidate 4 decisions

- nearby-first opening
- viewer-first interface, likely author-first launch strategy
- one authoritative map camera and projection
- local 3D rendered inside the same spatial context
- true 3D mainly at street scale
- replies in flat bottom-sheet board UI
- vertical world axis reserved for physical altitude
- independent atoms remain independent at every scale
- no synthetic stories or engagement-ranked Flow feed
- Candidate 1-shaped local MVP before full regional Flow behavior

### Signature

**A warm public world where zoom reveals patterns, concentrations, individual beacons, and finally one exact public conversation.**

The full multi-model fusion is preserved in [`candidate-4/reviews/openrouter-candidate-4-fusion.md`](candidate-4/reviews/openrouter-candidate-4-fusion.md).

---

# Source candidates

The original candidates remain important as source explorations and fallback references.

## [Candidate 1 — Calm Spatial Board](candidate-1/candidate.md)

A calm spatial world where each message appears as a precise light-pillar beacon. Selecting a beacon opens a compact public board while preserving geographic context.

**Retained contribution:** exact atom, beacon language, board interaction, feasible local MVP.

**Rejected as full direction:** cold/abstract world and vertical reply stacks.

## [Candidate 2 — The Living Miniature](candidate-2/candidate.md)

A warm, game-like miniature of the real world. Simplified buildings, streets, trees, and water make the neighborhood understandable and invite exploration.

**Retained contribution:** warmth, environmental readability, light game-like curiosity.

**Rejected as full direction:** handcrafted global miniature world, excessive scenery, high rendering and asset cost.

## [Candidate 3 — Flow World](candidate-3/candidate.md)

A viewer-first live world channel using semantic zoom: broad patterns become city concentrations, local beacons, and finally exact atoms and threads.

**Retained contribution:** region-to-atom semantic architecture and ambient awareness.

**Rejected as full direction:** engagement-ranked television framing, synthetic events, and world-first opening.

---

# Current comparison

| Dimension | Candidate 1 | Candidate 2 | Candidate 3 | Candidate 4 |
|---|---:|---:|---:|---:|
| Distinctive Punkto identity | Strong | Medium | Very strong | **Very strong** |
| Immediate comprehension | Medium | Very strong | Strong | **Strong** |
| Social warmth | Medium | Very strong | Strong | **Strong** |
| Large-scale usefulness | Weak | Medium | Very strong | **Very strong** |
| Mobile feasibility | Strong | Weak–medium | Medium | **Strong if phased** |
| Engineering risk | Low | High | Medium–high | **Medium** |
| Long-term potential | Strong | Strong | Very strong | **Very strong** |
| Current status | Source/MVP facet | Styling source | Architecture source | **Leading direction** |

These are still hypotheses to validate through prototype testing.

---

# Shared real-world scenarios

Every specification and prototype should demonstrate:

## Everyday social

> Bench by the canal has sun until 7 pm.

## Infrastructure thread

> Fire hydrant not working.
>
> I confirm, it has not been working for a week.
>
> County has been informed.

## Urgent local information

> Flooding here — road blocked.

---

# Required Candidate 4 states

The next connected design iteration should show:

1. nearby opening—the first five seconds
2. sparse or completely empty neighborhood
3. street view containing several beacons
4. selected atom and threaded board
5. fast `Flooding here` writing flow
6. region → district → street → atom semantic-zoom storyboard
7. weak-device flat 2D fallback

---

# Validation process

## Immediate prototype

Build one seeded real-neighborhood prototype with approximately 30 atoms, including:

- everyday canal/bench note
- broken hydrant thread
- urgent flooding atom(s)
- one altitude/floor example
- one dense concentration
- one empty area

Test on ordinary 2–3-year-old Android and iPhone devices.

Measure:

1. Can users explain Punkto after five seconds?
2. Do they understand that a beacon is a public message attached to a place?
3. Can they distinguish the root, replies, and physical altitude?
4. Does urgent content read as serious?
5. How quickly can they post `Flooding here`?
6. Is map interaction smooth and battery behavior acceptable?
7. Does an empty area feel inviting rather than broken?

## Engineering proof

Before committing to the full redesign, prove:

- one authoritative MapLibre camera/projection
- custom-layer beacon rendering
- close-scale extrusion and beacon performance
- smooth semantic transitions
- weak-device fallback
- reduced-motion behavior

---

# Decision log

## 2026-07 — Candidate 4 promoted

The OpenRouter multi-model evaluation concluded that a disciplined synthesis is stronger than any pure candidate:

> **Candidate 3 architecture, Candidate 1 atom interaction, and a restrained amount of Candidate 2 warmth.**

Candidate 4 — The Living Public World — is now the leading design specification.

Candidates 1–3 remain documented as source directions and fallback references rather than active competing winners.

## Remaining human product decision

The UI remains viewer-first. The launch strategy should likely be author-first.

The unresolved decision is:

> **Which real communities, official sources, campaigns, and local use cases will create enough honest initial density for the viewer-first world to deliver value without fake activity?**