# Changelog

All notable changes to Punkto are documented in this file.

This project follows a loose semantic-versioning convention: `vMAJOR.MINOR` for protocol changes, with patches reserved for fixes that don't change wire format. Until v1.0, breaking changes may occur between minor versions if the protocol benefits clearly from them.

---

## [v0.5] — 2026-05-16 — UI shell refactor + Docker stabilisation

Major structural refactor of the PWA. UI ownership moved out of `app.js` into dedicated modules. Service worker removed. Caching fixed for all assets. Two-view shell (Text / Map) becomes the canonical UI.

### Added
- **`pwa/ui-shell.js`** — owns page switching (Text ↔ Map), bottom nav wiring, settings panel open/close, body state classes, `setCounts()`; exports `initShell`, `showPage`, `openSettings`, `closeSettings`
- **`pwa/ui-text.js`** — owns text feed rendering, card markup, empty states, location-denied state, Show-on-map and Leave-note callbacks; exports `initTextView`, `renderTextFeed`, `clearTextFeed`
- **`pwa/ui-map.js`** — lazy map init wrapper, map resize on show, `focusOnMap` delegate; exports `initMapView`, `showMapView`, `focusOnMap`
- **`pwa/logo-192.png`** and **`pwa/logo-512.png`** — teal circle PWA icons (were 404)
- **Settings button active state** — `#nav-settings` gains `active` class while settings panel is open

### Changed
- **Bottom nav** — consolidated to exactly 4 buttons: **Text (35%) | Map (35%) | + (15%) | ⚙ (15%)**; Network and Me moved inside ⚙ settings panel
- **Service worker** — `sw.js` now immediately unregisters all service workers; app runs as a plain web app (no offline cache, no cache-bust pain)
- **Lazy map init** — map is only initialised on the first time the user switches to Map view; fixes black map when `#map` container is hidden at boot
- **Caddyfile (both nodes)** — `@app` matcher broadened from `path /app.js /index.html /reset.html` to `not path /lib/* && path *.html *.js`; all JS modules now get `no-cache, no-store, must-revalidate` + `Pragma` + `Expires` headers
- **`app.js`** — imports ui-shell, ui-text, ui-map; no longer contains inline nav wiring or card HTML generation; −106 / +59 lines vs v46
- **Deployment workflow** — after each GitHub Actions image build, both nodes must be updated with `docker compose pull && docker compose up -d --force-recreate` (not just `caddy reload`)

### Fixed
- `ReferenceError: elNavAdd is not defined` — stale duplicate variable removed from `wireEvents`
- App.js line 1221 mangled (43 877-char single line) — 1 219 literal `\n` occurrences restored as real newlines; regex patterns protected
- Duplicate event listeners on key-management buttons removed
- `setupKeyManagement()` now called unconditionally from `wireEvents()` on boot (was only called after atom click)
- Settings panel was leaking through at very small viewport heights due to missing bottom offset — fixed in CSS
- Stale Docker image issue — force-recreate now always pulls fresh image from registry

### Versions (app.js hard marker)
| Marker | Change |
|---|---|
| `v47-hard-marker-2026-05-15-6` | 4-button nav, SW removed, Network+Me into settings |
| `v48-hard-marker-2026-05-15-7` | Fixed mangled app.js line, duplicate listeners, `elNavAdd` crash |
| `v49-hard-marker-2026-05-15-8` | Redesigned UI shell attempt |
| `v50-hard-marker-2026-05-15-9` | Lazy map init fix — map no longer black on first load |
| `v51-hard-marker-2026-05-16-0` | Logo 404 fix, `elNavAdd` crash fix |
| `v52-hard-marker-2026-05-16-1` | Modular refactor — ui-shell.js, ui-text.js, ui-map.js extracted |
| `v53-hard-marker-2026-05-16-2` | Settings button highlights when panel is open |

---

## [v0.4+] — 2026-05-15 — Post-launch UX + Docker infrastructure

Iterative improvements applied after the v0.4 public launch. PWA is now at v46.

### Added
- **Docker deployment** — full containerised stack (Caddy + Python relay) for all reference nodes
  - `pwa/Dockerfile` — Caddy serving static PWA files
  - `relay/Dockerfile` — Python relay service
  - `deploy/docker-compose.yml` — single compose file for all nodes
  - `deploy/server1/Caddyfile` — auto-TLS for `punkto.xyz`, `app1.punkto.xyz`, `www`
  - `deploy/app2/Caddyfile` — auto-TLS for `app2.punkto.xyz`
  - GitHub Actions workflow (`.github/workflows/docker.yml`) — build + push to `ghcr.io/fisker1111/` on push/tag
- **Four-page UI shell** — app now has four distinct top-level views navigated by bottom bar
  - **Text** (default) — text-first atom feed, nearby atoms, proximity sort
  - **Map** — existing MapLibre + deck.gl 3D map, placement preview, altitude controls
  - **Network** — read-only node, peer, sync, and health status
  - **Me** — in-browser key generation, import, save/load, identity display
- **In-browser key management** — generate, import, save to LocalStorage, and load Ed25519 identities without CLI tools
- **Proximity-first atom list** — atoms sorted by distance from user; distance, category pill, and verified badge shown on each card
- **Placement preview + altitude controls** — 3D preview in Add-Atom modal; free-altitude and floor-picker input
- **Mnemonic modal** — replaces `window.alert()` for key generation; works in standalone PWA mode on mobile
- **ARIA and accessibility pass** — semantic HTML (`<header>`, `<main>`), ARIA roles/labels on all interactive elements, focus-visible CSS, `prefers-reduced-motion` media query
- **PWA_REVIEW.md** — documents review findings and improvement checklist

### Changed
- **Navigation labels**: Atoms → Text, Space → Map (v46)
- **Feed copy**: "Around you" → "Text view", "No notes here yet" → "No text here yet", "Nearby notes" → "Nearby text", "Show in 3D" → "Show on map" (v46)
- **Default landing**: app now boots into Text feed instead of the 3D map
- **Deployment**: bare-metal nginx + systemd replaced by Docker on all reference nodes; Caddy handles TLS via Let's Encrypt
- **Service Worker**: network-first for `.js` and `.html` during development; cache version bumped each release (currently `punkto-v46`)
- **Settings menu**: stripped to version + reset; Network and Me content moved to dedicated pages

### Removed
- `deploy.sh` — replaced by `docker compose pull && docker compose up -d`
- `pwa/node.py` — bare-metal runner, superseded by Docker
- `relay/systemd/punkto-relay.service` — superseded by Docker
- Bare-metal nginx configs and certbot cron on all reference nodes

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
