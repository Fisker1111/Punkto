# Candidate 5 — The Craigslist (Light 3D)

## Status

**Proposed launch candidate (2026-07-25, human).** Candidate 5 is not a rival world to Candidate 4 — it is the same product under a different doctrine about **who builds the rich world, and when**:

- Candidate 4: the core team builds the rich world; the MVP is a phase to exit.
- Candidate 5: the core team ships the smallest honest world; richness is delegated to the open-source community.

Candidate 5 claims that for a federated, self-hosted, open-source protocol, **the first app must be the one anyone can run, anyone can fork, and any phone can render** — and that beauty is a consequence of adoption, not a prerequisite for it.

## One-sentence concept

> The complete Punkto product — spatial world, beacons, altitude, boards, live atoms — rendered with Craigslist discipline: the lightest honest 3D that preserves the full grammar, instant on any device, cheap to serve from anyone's hardware.

## Product promise

> **Punkto opens fast, shows the public notes around you, and gets out of the way.**

The first five seconds must answer "what is this" with the world itself: a place, glowing points on it, one obvious `+`. No cinematic reveal, no tutorial, no scenery budget. If the app is beautiful, it is because the atoms are, not the chrome.

## Emotional promise

Opening Punkto should feel like checking a community noticeboard that happens to be the world: **instant, calm, obviously useful, obviously yours to use.**

Not a game. Not a film. Not a console. A tool that respects the device, the battery, the bandwidth, and the person standing in the street holding it. The app that wants to be closed: open → understand → act → look up.

## The Craigslist doctrine

Candidate 5 is named for the Craig Newmark reference point already in `PUNKTO_UI_PRINCIPLES.md`: no growth hacking, no engagement machinery, no dark patterns — a fast, honest tool that earns trust by refusing to grab.

Translated into engineering doctrine:

1. **Light client.** Instant load and smooth interaction on 3–5-year-old phones over mediocre connections. No asset downloads, no bespoke 3D scenery, no rendering feature that needs a performance budget meeting.
2. **Light server.** Many people will run the Docker node on their own hardware — a home server, a small VPS, a Raspberry Pi. **The ability to serve a community outweighs heavy graphics.** Serving thousands of atoms to a neighborhood must stay cheap in CPU, memory, and bandwidth. A design that needs tile servers, asset pipelines, or GPU-backed rendering to feel acceptable has failed this doctrine.
3. **Light governance.** The kernel freezes the meaning; everything replaceable stays cheap and replaceable. Themes, map styles, pillar shaders, skins, and richer worlds are explicitly community territory — forks, themes, and PRs on a stable core.

## Governing principles

1. **The full grammar, nothing else.** Every element of meaning from the shared candidates survives: beacon = public message at an exact point, form/color = kind, brightness = freshness, upright form = urgent, stem/floor chip = physical altitude, board = conversation. Everything that is not meaning is expendable.
2. **One build for all devices.** No separate "fallback" tier: the light build IS the product. Reduced-motion and weak-device behavior are the same code path, not an apology.
3. **Cheap to run, cheap to serve.** Client rendering and node serving are one budget. Self-hosting a node for a real community must remain trivially affordable.
4. **The kernel freezes early.** Visual grammar is decided once and protected; skins are negotiable forever, grammar is not. Community richness builds on a stable target or it does not build at all.
5. **Spatial truth is non-negotiable.** Lightness never compromises protocol: exact Punkto addresses, altitude in the spatial component, signed atoms, independent atoms never merged.
6. **The app that wants to be closed.** Success is time-to-look-up, not time-on-screen. No engagement ranking, no popularity machinery, no infinite anything.
7. **Warmth lives in the atoms, not the scenery.** Human tone comes from real messages and honest empty states ("Leave the first note here"), never from fabricated population or decorative environments.

## Candidate 5 must never become

- **A dollhouse:** no handcrafted scenery, simulated citizens, or world decoration that costs more than it communicates — same hard rule as Candidate 4.
- **A feed:** no infinite scroll, trending, synthetic stories, or engagement ranking — same hard rule as all candidates.
- **A showcase:** no visual feature that exists to impress reviewers rather than serve the person standing at the place.
- **A monolith:** no architectural decision that makes the reference PWA the only viable client. If a community member cannot fork the UI in an afternoon, the kernel has failed.
- **A moving target:** no continuous redesign of the shell. The kernel freezes; the world grows around it.

## Relationship to Candidate 4

Candidate 4 — The Living Public World — remains the **north star**: its semantic-zoom architecture, warmth budget, and local-3D ambitions describe what the world may become when a community earns it.

Candidate 5 is the **constitution**: what v1 is, what the kernel freezes, what v1 refuses.

The two are compatible as phases only if the phasing is honest: C5 is not "C4 with features missing" — it is a complete product that considers C4's ambitions optional, delegated, and community-owned. Richness becomes pull requests, not prerequisites.

Concretely, Candidate 5 adopts from Candidates 1–4:

- **From C1:** the invariant light-pillar beacon, ground ring, and selected-board interaction — already proven on test1 (`ui-cloud.js`).
- **From C4:** the nearby-first opening fallback chain (location → last place → region → home place), the flat bottom-sheet board, and the hard "vertical means altitude" rule.
- **From C2:** warmth through copy and clarity only — zero scenery budget.
- **From C3:** simple density clustering when zoomed out — patterns readable without cinematic transitions.

## First five seconds

Punkto opens nearby-first (same fallback chain as C4). The viewer sees:

- a fast, mostly flat map (2D or very light 3D — pitched view allowed if free)
- real beacons already visible, rendered as simple light pillars or glowing points
- one small place/context pill, one recenter action, one `+`
- nothing else competing for attention

Load target: interactive in under two seconds on a mid-2019 Android over 4G. There is no loading screen worth designing.

The empty neighborhood is honest: warm map, no fabricated atoms, one quiet **Leave the first note here** near the contribution control.

A non-technical user should be able to say:

> "These are public notes people left around here, and I can leave one too."

…and a technical user should be able to say:

> "I could run this for my town this weekend."

## Core interaction architecture

```text
Open → Understand → Act → Look up
```

- **Open:** land nearby, fast. Beacons already there.
- **Understand:** beacon = note, glow = fresh, upright = urgent, stem = floor. Learned by looking.
- **Act:** read a board, reply with a note, or place an atom via the staged `+` sheet.
- **Look up:** the app does not compete with the street. Closing it is the success state.

Zoom behavior is deliberately modest:

- **Far:** simple density clusters with counts; no animated transitions to design or tune.
- **Street:** individual beacons separate; cheap extrusion only if it comes free from the map style.
- **Selected:** pillar brightens, ground ring, board opens as a flat bottom sheet. No camera choreography required.

Altitude is always honored: floor chips and stems render on any view, so atoms on the 3rd floor are never confused with the ground.

## Required Candidate 5 states

1. nearby opening — the first five seconds, cold start, on a 2019 Android
2. empty neighborhood with the first-note invitation
3. street view with several beacons, one urgent, one on a floor above ground
4. selected atom with board bottom sheet
5. fast `Flooding here` write flow (under 20 seconds)
6. zoomed-out density clusters over a district
7. one physical node serving a community: resource footprint documented (CPU/RAM/bandwidth per 1,000 atoms)

## Validation questions

1. Does it load before the user loses patience on a weak phone?
2. Do first-time users understand "public notes on places" in five seconds — without any cinematic help?
3. Does the urgent atom read as serious with the cheapest possible rendering?
4. Can one person run a node for their community on home hardware, affordably?
5. Does the light presentation read as *honest* rather than *unfinished* once real atoms exist?
6. Is the grammar stable and documented well enough that a stranger can fork the UI and reskin it in a weekend?

## Known risks (kept honest)

- **Light can read as unfinished.** Craigslist survived ugly because its content was irreplaceable on day one. C5 therefore raises the stakes on honest seeding — the same unresolved density question recorded in the Candidate 4 decision log.
- **"Others will build later" requires a frozen target.** If the shell keeps being redesigned, nobody builds on it. C5 is a promise of early stability, and breaking that promise breaks the candidate.
- **First impression of a new category.** Nobody knows what public atoms in space are yet. The beacon must still *glow* — cheap to render must never mean quiet to notice. The pillar stays.
- **Deferred richness may never arrive.** The community may keep it light forever. C5 accepts this outcome as legitimate: a useful, widely self-hosted tool is a success even if no one ever builds the living world.

## Engineering posture

- Current test1 AtomCloud work (`ui-cloud.js`, dotted stems, ground rings, height ruler) is treated as the kernel baseline — Candidate 5 is largely a decision to **stop adding**, polish, and harden.
- No new rendering dependencies beyond what already ships in `pwa/lib/`.
- Map style: stock or near-stock tiles; no custom tile pipeline required to feel acceptable.
- Node serving: relay remains a plain Docker service; the UI must not assume CDN-hosted assets, GPU clients, or high-bandwidth links.
- All existing hard rules stand: nav bubble exactly `Text | Map | + | Settings` (35/35/15/15), dark/glass floating surfaces, blue accent only on `+`/primary actions, no social chrome, no hamburger.
