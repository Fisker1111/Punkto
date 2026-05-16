# Punkto Agent Instructions

## Project summary

Punkto is a PWA/protocol for attaching small signed atoms/punkti to exact real-world 3D points.

Core product model:
- Text = readable/list representation of atoms
- Map = spatial/3D representation of the same atoms
- \+ = create/place an atom
- Settings = identity, network, app/admin/debug

Current accepted bottom navigation:

```
Text | Map | + | Settings
```

Approximate nav weighting:
- Text: 35%
- Map: 35%
- +: 15%
- Settings: 15%

---

## Team roles

| Role | Owns |
|---|---|
| **ChatGPT** | Product direction, architecture specs, PR specs, review text |
| **Codex** | Code implementation, tests, commits, PRs |
| **AZ (Agent Zero)** | Deploy, Docker, Caddy, live-node verification, logs, OPS, security |
| **Human** | Final decisions, direction overrides, manual testing |

---

## Agent rules

- Be conservative.
- Inspect before editing.
- Prefer small, focused PRs.
- Do not redesign while fixing bugs.
- Do not change protocol/sync/storage/backend unless explicitly requested.
- Do not replace MapLibre/deck.gl unless explicitly requested.
- Do not add social features unless explicitly requested.
- Do not expose protocol/internal language in primary user UI.
- Keep Text and Map as two views of the same atoms.
- Keep Settings as the place for identity/network/debug/admin.
- Always report files changed, tests run, and manual verification.

---

## Current UI module ownership

| File | Owns |
|---|---|
| `pwa/ui-shell.js` | Shell/nav/page switching/settings visibility/counts |
| `pwa/ui-text.js` | Text feed/cards/empty/location/actions |
| `pwa/ui-map.js` | Map wrapper/focus/resize/lazy map boundary |
| `pwa/app.js` | Lifecycle, sync, IndexedDB, protocol/network, atom creation, coordination |
| `pwa/index.html` | Mostly static containers |
| `pwa/key-management.js` | Key/identity logic |
| `pwa/sw.js` | Service worker (currently unregisters itself — plain web app) |

---

## Required checks

Before final response, run when relevant:

```bash
node --check pwa/app.js
node --check pwa/ui-shell.js
node --check pwa/ui-text.js
node --check pwa/ui-map.js
node --check pwa/key-management.js
node --check pwa/sw.js
```

All must exit 0 before committing.

---

## Manual browser checklist

- Fresh InPrivate or `reset.html`
- Confirm console hard marker matches commit
- Confirm Text page opens by default
- Confirm nav: `Text | Map | + | Settings`
- Confirm settings panel closed on first load
- Tap **Map** → map tiles load, location dot visible
- Tap **Text** → text feed or empty state
- Tap **+** → create atom modal opens
- Tap **Settings** → settings panel slides up, button highlights
- Tap Settings again → panel closes, button unhighlights
- Tap **Show on map** on a Text card → switches to Map, focuses atom
- Test `/p/<id>` deep link → opens Map, focuses atom
- Test create with altitude if practical

---

## Deployment (AZ role)

See `DEPLOYMENT_CHECKLIST.md` for full deploy procedure.

Quick reference:

```bash
# After GitHub Actions build completes
docker compose pull && docker compose up -d --force-recreate
```

Run on **both** nodes. Always verify with hard marker and `docker compose ps`.
