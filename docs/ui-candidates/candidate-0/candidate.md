# Candidate 0 — The Baseline (What Ships Today)

## Status

**Baseline reality, not a design candidate.** Candidate 0 documents the Punkto product as it actually exists and runs today — the reference implementation deployed on `node1` and `node2` — measured against the merged specification ([Candidate 4 — The Living Public World, with the Candidate 5 shipping doctrine](../candidate-4/candidate.md)).

Purpose: implementation planning diffs the merged spec against *reality*, not against other visions. This document is the reality. Where a claim is uncertain, it is marked **[verify]** — planning must confirm against code, not against this summary.

## What exists today

### The product

A plain web app (service worker currently unregisters itself), served statically from each relay node. Vanilla JS, no build step, vendored libraries in `pwa/lib/` (MapLibre, Three.js, Dexie, nacl). Live at both seed nodes.

### Shell and navigation

- Nav bubble exactly **`Text | Map | + | Settings`** (35/35/15/15), dark/glass, no hamburger — already conformant with `PUNKTO_UI_PRINCIPLES.md`.
- **Text view**: readable feed of atoms — cards with safe link rendering, category badges, author/reply UI, "Show on map" action, empty state, boot default is Text **[verify current default]**.
- **Map view**: MapLibre map with atom markers, lazy boundary, focus/deep-link support (`/p/<id>` opens Map focused on an atom).
- **AtomCloud** (test1 branch, `ui-cloud.js`): Three.js 3D world — light-pillar-style atoms with dotted stems, ground rings, height ruler, world context floor, category colors. **Architecturally separate scene/camera from MapLibre** — the merged spec's one-authoritative-camera rule makes this the biggest open engineering question.
- **Settings**: identity (keys), network (nodes), app/admin/debug — progressive disclosure already in place.

### Protocol and data

- Punkto addresses `p:<spatial>-<id>` with altitude inside the 12-char spatial component (`core/geohash3d.py`, `pwa/geohash3d.js`).
- Atoms: canonical JSON, sorted keys, Ed25519 signed in the PWA (`key-management.js`, wired into create and reply flows); `atom_id = SHA-256(canonical atom without sig)`, computed locally.
- Relay protocol drafts: root/reply, queries with `after` cursor and `before` floor, fast-forward sync, dev-mode `fed: true`.
- Replies exist end-to-end (spec `docs/punkti.replies.md`, relay support, PWA UI).
- Categories/labels with badge UI exist.
- Altitude: protocol-complete; UI has floor/height input in the create flow **[verify]**.

### Storage and sync

- IndexedDB via Dexie (`storage/db.js`, `atom-store.js`, `node-store.js`).
- Sync engine with node registry and network client (timeouts/failover), fallback to production seed nodes.
- Create flow: **posts to relay first, stores locally on success** — no offline queue.

### Operations

- Relay: Python, single Docker service per node; node config YAML; backup/restore scripts; node-doctor; canary verification; launch-candidate checklist completed (2026-07-22); 56 relay tests passing.
- Federation: two seed nodes syncing; dev-mode federation flag; multi-relay client groundwork **[verify]**.
- Precedent for honest density: DMI operator import (real official data as atoms).

## What Candidate 0 already gets right (per the merged spec)

1. **The nav and shell are the spec.** Bubble, weights, dark/glass tokens, language rules — done before any candidate was drawn.
2. **Text and Map as two views of the same atoms** — the spec's accessibility-equivalence requirement (§21) has a running head start.
3. **The beacon instinct exists** — AtomCloud's pillar-with-stem is the invariant beacon in embryo; the grammar was found in code before it was found in documents.
4. **Altitude is real** — encoded in the address, displayed with floors, never a side channel.
5. **No engagement machinery anywhere** — ordering is chronological/spatial by construction; nothing to remove.
6. **Self-hosting works today** — one Docker service, Caddy, backup/restore, fresh-install runbook. The Craigslist server doctrine is partially lived, not just written.
7. **Deep links** — `/p/<id>` is the text-first URL seed of kernel contract §22 (server-rendered preview card still missing).

## The gap table (merged spec → current reality)

| # | Merged spec requirement | Candidate 0 reality | Gap class |
|---|---|---|---|
| 1 | Urgency kind with mandatory expiry + non-suppressible signalling (§6) | Categories exist; no urgency kind, no expiry, no protected channel | **Protocol** |
| 2 | Closed relation vocabulary: reply/confirms/disputes/supersedes + derivation rule (§5) | Replies only; no typed relations, no derived state ("3 confirmations, unresolved") | **Protocol** |
| 3 | Validity/expiry windows as the legitimate ordering (§4) | Atoms are permanent; no expiry field | **Protocol** |
| 4 | Mandatory positional/altitude uncertainty field (§2) | Not recorded at create time **[verify]** | **Protocol** |
| 5 | Compose independent of map/scene load; offline queue with retry (v1 gate: p95 < 20 s) | Create posts to relay first; fails without network; map loads before compose | **Client architecture** |
| 6 | One authoritative camera/projection (§9) | Two scenes: MapLibre map + separate Three.js AtomCloud camera | **Client architecture — the big one** |
| 7 | v1 warmth floor: procedural glow, timestamp-derived recency pulse, authored empty states | Visual language exists (dark/glass); no liveness grammar or freshness pulse; empty states plain | **Render** |
| 8 | Aggregate bbox+zoom query, naive implementation acceptable (§12) | Not present; sync fetches by cursor, map shows loaded atoms only | **Protocol + client** |
| 9 | Theming contract (prohibitions-first), one reference rich theme, conformance suite, reference-device budget (§16–20) | None exist; CSS is monolithic **[verify]** | **Governance artifacts** |
| 10 | Server-rendered static preview card for every atom URL (§22) | Deep link opens the app; no static/preview rendering | **Server + protocol** |
| 11 | Basemap contract — provider neutrality, attribution, privacy, caching, degraded mode (§23) | MapLibre style/tiles dependency undocumented as a contract **[verify]** | **Operations** |
| 12 | Media policy (§24) | Atoms are text-only today **[verify]** — policy trivially "no attachments", must be written | **Operations** |
| 13 | Kernel-level moderation tools + removal propagation (§25) | None; relay accepts validly signed atoms within policy | **Protocol + operations** |
| 14 | Documented node budgets (§26) | Backup/restore exists; no published CPU/RAM/bandwidth budgets per atom volume | **Operations** |
| 15 | v1 acceptance gates on a named reference device | Never measured; no reference device named | **Validation** |

## What Candidate 0 must never pretend

- **That the AtomCloud 3D scene is the spec's world.** It is a promising prototype of the beacon grammar under the wrong camera architecture. The spec is explicit: one spatial truth, no visible handoff. Gap #6 is an architecture decision, not a styling task.
- **That replies are the board.** The hydrant scenario needs typed relations and derived state; a reply chain cannot express "3 confirmations, unresolved, 11 days" without them.
- **That launch-checklist-complete means spec-complete.** The launch candidate checklist proved the v0 relay/PWA is deployable and honest. It said nothing about urgency, expiry, relations, aggregates, liveness, or conformance — those are the v1 delta.
- **That sparse deployment is a failure state.** Two seed nodes with honest atoms is exactly the condition the shipping doctrine is designed for. Candidate 0 is not behind schedule; it is the foundation the schedule stands on.

## Relationship to the merged specification

Candidate 0 is the **kernel before the contracts**. The merged spec now defines what must freeze; this document records what exists to be frozen. The implementation plan is, in order:

1. **Protocol gaps first** (rows 1–4): urgency kind + expiry, relation vocabulary, validity windows, uncertainty field — because retrofitting protocol into a deployed signed-event system is the painful path.
2. **Client architecture** (rows 5–6): compose independent of map load + offline queue; the one-camera decision (adapt AtomCloud into a MapLibre custom layer vs. rebuild).
3. **Render and query** (rows 7–8): liveness grammar; naive aggregate endpoint.
4. **Governance artifacts** (rows 9–14): theming contract + reference theme + budget; preview cards; basemap/media/moderation/budget documents.
5. **Validation** (row 15): name the reference device, run the four v1 gates in a pilot.

The detailed planning for these steps is the next activity after this document is accepted.

## Required reviews of this document

This baseline should be **verified against the code** during planning — every **[verify]** marker resolved to a fact — and corrected in place. It is a working document, not a vision.
