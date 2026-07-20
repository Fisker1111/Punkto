# Punkto PWA — UI Design Candidates

## Purpose

This folder is the shared design room for humans and AI reviewers evaluating the next high-level Punkto PWA interface.

The work is intentionally focused on product design rather than implementation details:

- visual identity
- spatial interaction
- social acceptance
- navigation and button hierarchy
- message and thread presentation
- mobile usability
- engineering feasibility

The candidates are explorations, not approved implementation specifications.

## Core product definition

> **Punkto is a living geospatial world made from public messages anchored in real space.**

The message is the primary social object. The author is secondary. Punkto does not initially depend on private messaging, followers, profile popularity, or social-status metrics.

## Shared design principles

1. **Message-first** — places and messages lead; profiles do not.
2. **Spatial truth** — every atom remains anchored to its real location and altitude.
3. **Warm and social** — inviting and slightly game-like, not cold cyberpunk infrastructure.
4. **Calm** — activity feels alive without becoming noisy or addictive.
5. **Public-board model** — replies are public notes attached to a root atom.
6. **No silent merging** — independent atoms remain independent; replies stack only when they belong to the same root.
7. **Progressive complexity** — advanced identity, node, altitude, and technical controls stay out of the first-use experience.
8. **Mobile-first feasibility** — the design must remain plausible on ordinary mobile hardware and in a PWA.

## Candidates

### [Candidate 1 — Calm Spatial Board](candidate-1/candidate.md)

A dark, calm spatial world where each message appears as a precise light-pillar beacon. Selecting a beacon opens a compact public board while preserving geographic context.

**Signature:** exact anchor, vertical beacon, floating board.

### [Candidate 2 — The Living Miniature](candidate-2/candidate.md)

A warm, game-like miniature of the real world. Simplified buildings, streets, trees, and water make the neighborhood immediately understandable and invite exploration.

**Signature:** a lived-in miniature world containing glowing public stories.

### [Candidate 3 — Flow World](candidate-3/candidate.md)

A viewer-first live world channel using semantic zoom: 2D global patterns become city situations, local 3D beacons, and finally exact atoms and threads.

**Signature:** continuous movement from global awareness to one real message.

## Current comparison hypothesis

| Dimension | Candidate 1 | Candidate 2 | Candidate 3 |
|---|---:|---:|---:|
| Distinctive Punkto identity | Strong | Medium | Very strong |
| Immediate comprehension | Medium | Very strong | Strong |
| Social warmth | Medium | Very strong | Strong |
| Large-scale usefulness | Weak | Medium | Very strong |
| Mobile feasibility | Strong | Medium | Medium |
| Engineering risk | Low | High | Medium |
| Long-term potential | Strong | Strong | Very strong |

These are hypotheses to test, not final scores.

## Real-world evaluation scenarios

Every candidate should eventually demonstrate the same three scenarios:

### Everyday social

> Bench by the canal has sun until 7 pm.

### Useful infrastructure thread

> Fire hydrant not working.
>
> I confirm, it has not been working for a week. County is informed.

### Urgent local information

> Flooding here — road blocked.

## Required views for each candidate

Before selection, each candidate should show:

1. first five seconds after opening Punkto
2. world or city overview
3. neighborhood exploration
4. selected atom and thread
5. writing and placing a Punkti
6. weak-device or reduced-detail fallback

## Evaluation process

1. Strengthen each candidate without blending them prematurely.
2. Ask independent human and AI reviewers to use [`evaluation-prompt.md`](evaluation-prompt.md).
3. Test the same scenarios and scales across all candidates.
4. Review engineering feasibility and mobile performance.
5. Select separately:
   - primary product architecture
   - visual language
   - atom/thread interaction model
6. Record the final decision and rejected alternatives here.

## Current working hypothesis

A possible final direction may combine:

- **Candidate 3** for world-to-street architecture
- **Candidate 1** for precise atom and board interaction
- selected warmth and readability from **Candidate 2**

This combination is not yet approved. The candidates must first be evaluated independently.

## Decision log

_No final decision yet._
