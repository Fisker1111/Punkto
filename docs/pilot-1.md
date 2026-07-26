# Pilot 1 — Implementation Plan

> First execution plan against the merged specification: [`ui-candidates/candidate-4/candidate.md`](ui-candidates/candidate-4/candidate.md) (Candidate 4 + Candidate 5 shipping doctrine), diffed against the shipping baseline [`ui-candidates/candidate-0/candidate.md`](ui-candidates/candidate-0/candidate.md).
>
> **Pilot 1 thesis:** one operator, one town, honest atoms, weak phone — prove the four v1 gates with real humans before building anything beyond them.

---

# 1. Human decisions (defaults recommended — confirm or amend)

These five decisions unblock all work. Each has a recommended default; changing any of them re-scopes the work packages below.

| # | Decision | Recommended default | Status |
|---|---|---|---|
| D1 | **One-camera architecture** (Candidate 0 gap #6 — the big fork) | **Adapt, not rebuild.** Port the AtomCloud beacon rendering (dotted stems, ground rings, height ruler, category colors) into a MapLibre **custom layer** — Three.js may render, but with MapLibre's projection matrix, no independently controlled second camera. The test1 `ui-cloud.js` work survives as grammar; the independent scene does not. Evaluation task (WP-6a) decides final shape before any visual build. | ✅ confirmed 2026-07-26 |
| D2 | **Basemap** | **Yes, with a provider-neutral contract.** Keep current tiles at launch; write the basemap contract (attribution, privacy/viewport leakage, caching, degraded mode, self-host path) without building self-hosted tiles now. "The bench is meaningless without the canal." | ✅ confirmed 2026-07-26 |
| D3 | **Urgency governance** | **Ship per the fused position.** Urgency kind with mandatory expiry + provenance + kernel-level moderation tools (delist, precision-blur) with removal propagation. Expiry is the v1 abuse resistance; governance proof remains owed and is explicitly tracked. | ✅ confirmed 2026-07-26 |
| D4 | **Reference device** | **One physical mid-2019 Android** (Moto G7 / Galaxy A50 class or older), named and owned by the human, used for every gate measurement. No emulator substitutes. `[HUMAN: name the actual unit]` | ✅ confirmed 2026-07-26 |
| D5 | **Pilot town & seeding** | **The human's own local area.** Human writes the honest everyday atoms; AZ script-seeds the scenario set (hydrant thread, flooding report, floor atom, cluster) via the relay. Target ~30 atoms per the MVP validation brief. `[HUMAN: name the town]` | ✅ confirmed 2026-07-26 |

---

# 2. Pilot definition

- **Where:** the pilot town (D5), served by one self-hosted node on home-class hardware or a small VPS, federated with the seed nodes.
- **Who:** the human product owner + 5–10 cold users (people who have never seen Punkto).
- **Content:** ~30 honest atoms — everyday notes (bench/canal class), one infrastructure thread with confirmations, one urgent report, one altitude/floor example, one dense cluster, one deliberately empty area. No fabricated activity: every atom is either true, or clearly a scenario atom placed for the test and removable after.
- **Device:** the named reference device (D4), throttled 4G profile for gate 2.
- **Success:** the four v1 gates (§5) pass. Failure on gate 2 or 3 redesigns the cheap-warmth grammar before anything else ships.

---

# 3. Work packages (dependency order)

Owners per `AGENTS.md`: **ChatGPT** = specs/review text · **Codex** = code/tests/PRs · **AZ** = deploy/Docker/verify/ops · **Human** = decisions and manual testing. Every Codex package is a PR using `CODEX_TASK_TEMPLATE.md`.

## Phase P — Protocol (Candidate 0 gaps 1–4; do first — retrofitting protocol is the painful path)

| WP | Scope | Spec basis | Acceptance |
|---|---|---|---|
| **P-1** Atom validity/expiry field | Add optional `exp` (expiry timestamp) to atom schema, canonicalization, relay validation (reject expired from feeds, keep in log), PWA display of remaining validity | Kernel §4 | Relay tests extended; expired atom excluded from `/feed` & sync; 56+ tests green |
| **P-2** Urgency kind + mandatory expiry | `kind: "urgent"` requires `exp`; sober register semantics documented; non-suppressible signal rules written (render follows in R-1) | Kernel §6, D3 | Relay rejects urgent atoms without `exp`; protocol doc updated |
| **P-3** Relation vocabulary | `rel: replies-to | confirms | disputes | supersedes` on atoms; derivation rule producing displayed state ("3 confirmations, unresolved, 11 days"); relay validation | Kernel §5, docs/punkti.replies.md | Hydrant scenario expressible end-to-end at protocol level; tests for each relation + derivation |
| **P-4** Positional/altitude uncertainty | `acc` field (meters) recorded at create from device accuracy; shown as soft radius in compose confirmation | Kernel §2 | New atoms carry `acc`; older atoms tolerated (absent = unknown) |

**ChatGPT deliverable for Phase P:** one protocol delta spec (single doc, fields + validation + federation behavior) before Codex starts P-1. This is the freeze document for Kernel §A.

## Phase C — Client architecture (gaps 5–6)

| WP | Scope | Spec basis | Acceptance |
|---|---|---|---|
| **C-1** Compose independent of map/scene load | `+` opens compose instantly from any app state; GPS fix, key access, and map loading never block typing; sign locally; **offline queue with retry** (IndexedDB outbox, publish on reconnect) | v1 gate 2; merged spec writing flow | On reference device: app-open → signed urgent atom accepted p95 < 20 s over throttled 4G (measured, not asserted); compose works fully offline and publishes on return of connectivity |
| **C-2** One-camera evaluation → decision | **6a:** spike — port one beacon + stem + ground ring into a MapLibre custom layer with MapLibre's projection matrix; measure on reference device. **6b:** decision record — adopt custom-layer path (retire independent `ui-cloud.js` scene) or documented alternative approved by human | D1; Kernel §9 | Decision record committed; if custom layer: AtomCloud grammar (stems, rings, height ruler, category colors) renders inside MapLibre's camera with no visible handoff |

## Phase R — Render & query (gaps 7–8; after C-2)

| WP | Scope | Spec basis | Acceptance |
|---|---|---|---|
| **R-1** v1 warmth floor | Procedural beacon glow; recency pulse derived deterministically from timestamps (kernel-owned semantics, theme-adjustable intensity); authored empty states incl. "Leave the first note here"; urgent register per P-2 (sober upright form, slow pulse, visible farther out) | Merged spec §Visual warmth; Kernel §15 | Gate 3 passes with cold observers; zero new asset downloads; 60 fps on reference device |
| **R-2** Aggregate bbox+zoom endpoint | Relay: naive in-process aggregate (`bbox+zoom → counts/centroids` with provenance/freshness); PWA: simple district clustering consuming it | Kernel §12 | Zoomed-out district shows honest counts; aggregates never mask sparse data; relay tests green |
| **R-3** Board derived-state display | Boards show relation-derived state from P-3 ("3 confirmations, unresolved, 11 days"); author + time only, no counts-as-approval anywhere | Kernel §5, board contract §14 | Hydrant thread readable end-to-end in UI; zero approval-shaped UI |

## Phase G — Governance artifacts (gaps 9–14; parallel with R, mostly documents + one theme)

| WP | Scope | Owner | Acceptance |
|---|---|---|---|
| **G-1** Theming contract (prohibitions-first) + theme token inventory | ChatGPT draft, Codex implements tokens | Kernel §16–17 | Contract published; CSS tokens extracted so a fork can reskin in an afternoon |
| **G-2** Reference rich theme (non-default) | Codex; exercises every hook | Kernel §16, §20 | Second theme ships behind a debug/settings flag; default remains the light build |
| **G-3** Reference-device performance budget doc + minimal conformance checklist | ChatGPT + AZ | Kernel §19–20 | Budget named (device, fps, load time, memory); checklist runnable against a build |
| **G-4** Static atom preview card | Codex (relay serves server-rendered card at `/p/<id>` for non-app fetches) | Kernel §22 | curl of an atom URL returns a readable static card; app deep-link behavior unchanged |
| **G-5** Basemap contract + media policy + moderation doc + node budget doc | ChatGPT drafts; human approves | Kernel §23–26, D2 | Four short docs published; moderation tooling ticket created (delist/precision-blur — implementation may follow pilot) |

## Phase V — Validation (gap 15; the pilot itself)

| WP | Scope | Owner | Acceptance |
|---|---|---|---|
| **V-1** Pilot node deployment | One self-hosted node on home-class hardware, federated with seed nodes | AZ | Node-doctor green; backup/restore rehearsed; footprint measured (CPU/RAM/bandwidth per 1k atoms) feeding G-5 numbers |
| **V-2** Seeding | ~30 atoms per pilot definition | Human + AZ | Seed set present; honest; removable scenario atoms flagged |
| **V-3** Gate measurement | Four gates with 5–10 cold users | Human | Results recorded in this document's §6; pass/fail decided per gate |

---

# 4. Sequencing and dependencies

```text
D1–D5 confirmed
   │
   ├─ ChatGPT: protocol delta spec (freeze §A) ──────────┐
   │                                                      ▼
   │   P-1 expiry → P-2 urgency → P-3 relations → P-4 uncertainty   (Codex, sequential PRs)
   │                                                      │
   ├─ C-1 compose/offline queue (Codex, parallel with P)  │
   ├─ C-2 one-camera spike → decision (Codex + human) ────┤
   │                                                      ▼
   │   R-1 warmth floor · R-2 aggregates · R-3 board state
   │                                                      │
   ├─ G-1…G-5 (mostly parallel; G-2 after C-2)            │
   │                                                      ▼
   │   V-1 pilot node → V-2 seeding → V-3 gates
   ▼
Pilot review: gates recorded, Phase-2 scope decided by evidence
```

Hard sequencing rules:

- **No visual work before C-2 decides the camera.** Everything else can move; pixels cannot.
- **No Phase-2 (semantic zoom richness, saved places, Explore view) before the gates pass.** The gates gate them.
- **Protocol PRs never bundle UI changes** beyond the minimum to keep the app working (per AGENTS.md: small focused PRs, no silent scope expansion).

---

# 5. The four v1 gates (measurement method)

| Gate | Method | Pass |
|---|---|---|
| 1. First-glance comprehension | Cold user opens the app unbriefed; asked after ~5 s "what is this?" | States "public notes people left around here, and I can leave one too" in their own words; does not call it unfinished |
| 2. Urgent-post p95 < 20 s | Reference device, throttled 4G, timed app-open → signed urgent atom accepted; ≥10 runs across pilot week | p95 < 20 s |
| 3. Urgency recognition | Cold observer shown the street view containing the flooding beacon; asked "what do you notice?" | Notices and reads it as urgent within seconds, without prompting |
| 4. Unprompted return visits | Pilot users told nothing about metrics; no notifications exist | Measurable return visits within the pilot window; share of atoms read by non-authors recorded |

Forbidden measurements: time-on-screen, session length, anything engagement-shaped.

---

# 6. Results log (filled during the pilot)

| Gate | Result | Evidence | Verdict |
|---|---|---|---|
| 1. Comprehension | — | — | ⬜ |
| 2. Urgent-post p95 | — | — | ⬜ |
| 3. Urgency recognition | — | — | ⬜ |
| 4. Return visits | — | — | ⬜ |

Pilot verdict: ⬜ proceed to Phase 2 · ⬜ redesign cheap-warmth grammar · ⬜ revisit the merge (per the fusion's named falsification condition)

---

# 7. Explicitly out of scope for Pilot 1

- Semantic zoom beyond the naive aggregate endpoint (region/district choreography is Phase 2)
- Self-hosted tiles (contract only, G-5)
- Conformance suite as automated tooling (checklist only, G-3)
- Moderation tooling implementation (documented + ticketed in G-5; required before public launch, not before a trusted-town pilot)
- Any notification system (deliberately never — gate 4 depends on its absence)
- Announcement/marketing of any kind before the gates are recorded

---

# 8. Branch and merge strategy

- All work on `codex/*` feature branches off `main`, one PR per work package, `CODEX_TASK_TEMPLATE.md` receipt in each PR.
- This document lives on `agent/ui-design-candidates` until that branch merges to `main` (PR with ChatGPT review), then travels with it.
- AZ deploys merged work to the canary first, verifies (node-doctor, hard marker, smoke tests), then both seed nodes, per `DEPLOYMENT_CHECKLIST.md`.

---

*Pilot 1 defined 2026-07-26, per human direction following the Candidate 5 merge. **D1–D5 confirmed by the human 2026-07-26** (D4 device unit and D5 town name still to be named by the human when ready). Work may start.*
