# Changelog

All notable changes to Punkto are documented in this file.

This project follows a loose semantic-versioning convention: `vMAJOR.MINOR` for protocol changes, with patches reserved for fixes that don't change wire format. Until v1.0, breaking changes may occur between minor versions if the protocol benefits clearly from them.

---

## [v0.4] — 2026-05-10 — Public launch

First public release. Repository goes from private to MIT-licensed open source.

### Added
- `LICENSE` (MIT, Copyright 2026 Fisker)
- `CONTRIBUTING.md` — guide for newcomers, file structure tour, run-locally instructions
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1
- `SECURITY.md` — vulnerability disclosure policy (fisker@protonmail.ch)
- `CHANGELOG.md` — this file
- `punkto.identity.md` v0.1 — formal Ed25519 + BIP39 identity spec
- `punkto.relay.md` v0.1 — formal relay-role spec (rolling buffer, /latest, three-role architecture)
- `relay/` directory — standalone reference relay implementation (Python stdlib + `requests`, ~830 lines)
  - `relay.py` — single-file relay server
  - `relay/README.md`, `relay/.env.example`, `relay/test_relay.py`, `relay/systemd/punkto-relay.service`
- `tools/punkto-key.py` — full identity toolkit (new / import / sign / verify)
- `tools/punkto-keygen-v0.1.py` — small standalone key-generation script
- README polish: Roadmap, Known issues, Philosophy, License sections

### Changed
- Live reference deployment (`app1.punkto.xyz`, `app2.punkto.xyz`) migrated from `pwa/node.py` to `relay/relay.py`
- nginx configuration on both reference nodes proxies `/latest`, `/stream`, `/llms.txt` (in addition to `/atom`, `/feed`, `/health`, `/info`)
- Default relay buffer policy: 10 000 atoms or 7 days, whichever fills first (Flow TV semantics)

### Notes
- Relay v0.1 stores `sig` and `pubkey` if present but does not verify signatures yet. Verification is planned for relay v0.2.
- The pre-existing seed atoms (April–early May 2026) will age out of the relay buffer naturally as new atoms arrive.

---

## [v0.3] — 2026-05-08 — PWA UX iteration

Three iterations of UI/UX work delivering deep linking, onboarding, and 3D altitude features.

### Added
- A1: `/p/<id>` deep-link routing in the PWA — shareable URLs now focus the map on a specific atom
- A2: Reset action in settings with confirmation modal
- A3: Cache-first rendering for instant cold-start
- A4: 44×44 minimum touch targets across the UI
- B1: Hidden-atoms filter in settings
- B3: Drop-atom warning before posting
- B4: Peer-sync improvements (better error handling, cursor recovery)
- Onboarding tagline, first-visit hint, branding polish
- Altitude input on atom creation; building-aware floor picker (v22)
- Box-query height detection for buildings (v24) — handles cases where the map center isn't exactly on a building footprint
- Live crosshair height readout (v26)
- Lollipop-style 3D leader lines from atoms to their bubbles (v23)
- Bubble UI rendering with DOM bubbles, per-author tint, +N badge for stacks, new-atom pulse
- Server-rendered `/p/<id>` with OpenGraph, Twitter Card, and JSON-LD metadata for sharing
- AI-discovery surfaces: `robots.txt`, `llms.txt`, `openapi.json`, `sitemap.xml`
- Privacy and reset HTML pages (`privacy.html`, `reset.html`)
- HTTPS via Let's Encrypt on both reference nodes with auto-renew

### Changed
- Boot view focused on Copenhagen with fit-to-atoms behavior
- TextLayer auto for Nordic character support
- Removed ground grid over Copenhagen for cleaner map

### Fixed
- PPTX hallucination fix in atom rendering
- nginx now correctly serves `/latest` and similar new endpoints

---

## [v0.2] — 2026-05-04 — Consolidation

63 files changed. Repository structure consolidated to a single PWA-centric source after dropping the native Android exploration.

### Removed
- `App/Web/` — duplicated PWA copy (consolidated into `pwa/`)
- `App/Android/` — early Kotlin Android app (paused on `android-native-paused` branch)
- Root-level `*.js`, `*.html`, `*.py`, `*.json` PWA copies
- `punkto.ai.v0.1.md`, `punkto.v0.1.md` — archived early spec versions

### Changed
- README points to `pwa/` as the single source of truth
- Spec atom format aligned: `t` (timestamp ms), `sig` (Ed25519 signature), canonical form `p:<spatial>-<id>` with `<spatial>` as a 12-char 3D geohash
- `atom_id` defined as full SHA-256 of canonical bytes excluding `sig`
- Decision: PWA is the canonical client for v1.0; native Android development paused until after v1.0 launch

### Notes
- Tag: `v0.2-consolidated`

---

## [v0.1] — Initial protocol drafts

The original Punkti protocol prototype and the first round of `punkto.*.md` specifications.

### Added
- `punkto.md` v0.1 — initial atom format and 3D geohash addressing scheme
- `punkto.sync.md` v0.1 — first sync model (byte-offset cursors, NDJSON append-only logs)
- `punkto.node.md` v0.1 — first node API definition
- `punkto.manifest.md` v0.1 — atom data model
- `punkto.ui.md` v0.1 — UX guidelines
- `punkto.ai.md` v0.1 — first AI discovery / onboarding spec (later refactored)
- `core/` — pure-Python reference library
- `pwa/` — first PWA prototype with MapLibre + deck.gl
- Two synced reference nodes deployed and validated

---

## Versioning rules

- **Spec changes** (atom format, canonical bytes, sync semantics) bump the minor version
- **Reference implementation fixes** (without spec change) live as patches between minor versions
- **Pre-v1.0**: breaking spec changes are allowed when the new design is clearly better
- **Post-v1.0**: breaking spec changes require a major bump and a migration plan
