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

> **Next styling-only PR** (no behavior/protocol/backend changes) must follow `PUNKTO_UI_PRINCIPLES.md`:
> dark/glass unification · one nav bubble (docks bottom on mobile, left on desktop) · no hamburger · map control clustering · staged Create sheet.

---

## Team roles

| Role | Owns |
|---|---|
| **ChatGPT** | Product direction, architecture specs, PR specs, review text |
| **Codex** | Code implementation, tests, commits, PRs |
| **AZ (Agent Zero)** | Deploy, Docker, Caddy, live-node verification, logs, OPS, security — **not product scope** |
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
- **Do not silently expand scope.**
  - If a task is implementation, do not redesign.
  - If a task is deployment, do not refactor app code.
  - If a task is review, do not apply unrelated fixes.

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

---

## Cursor Cloud specific instructions

Two runnable services; no build step, no Docker needed for local dev. Python deps (`requests`, `PyYAML`, `cryptography`) are installed by the startup update script.

### Relay (Python, `relay/relay.py`)
- Standard run/test commands are in `relay/README.md`. The default bind is `127.0.0.1:8000`; tests run via `python3 test_relay.py` (no pytest required).
- Non-obvious: besides the documented `PUNKTO_DATA_DIR`, the relay also defaults `PUNKTO_NODE_KEY` to `/data/node-key.json` and `PUNKTO_ATOM_LOG_PATH` to `/data/atoms.log.jsonl` (absolute `/data`, writable only inside the Docker image). For local dev these must be redirected to a writable dir, e.g.:
  ```bash
  PUNKTO_DATA_DIR=/tmp/punkto-data \
  PUNKTO_NODE_KEY=/tmp/punkto-data/node-key.json \
  PUNKTO_ATOM_LOG_PATH=/tmp/punkto-data/atoms.log.jsonl \
  python3 relay.py
  ```
  The `node config missing at /config/punkto-node.yml; using safe defaults` log line is expected locally and harmless.
- Acceptance window: `POST /atom` rejects timestamps older than 24h (`atom_too_old`). Use a current-millis `t` when posting test atoms.

### PWA (vanilla JS static files, `pwa/`)
- No bundler/npm; dependencies are vendored in `pwa/lib/` and `pwa/nacl.min.js`. Serve the directory statically (e.g. `python3 -m http.server 8080` from `pwa/`). Map tiles and the no-relay fallback (`node1/node2.punkto.xyz`) require internet.
- Non-obvious: the PWA targets its relay at `window.location.origin` (`NODE_URL` in `app.js`), and **create-atom posts to the relay first and only stores locally on success** (`submitAtomFromModal`). A plain static server on `:8080` has no `/atom` endpoint, so the create flow silently falls back to the production seed nodes. To exercise create end-to-end against a *local* relay, serve the PWA behind a front that also reverse-proxies the relay API paths (`/atom`, `/latest`, `/feed`, `/info`, `/node`, `/health`, `/status`) to the relay on `:8000`, so they share one origin (this is what production Caddy does).

### Quick checks
- PWA JS syntax: the `node --check` list under "Required checks" above.
- Relay: `python3 relay/test_relay.py` (56 tests).
- Core lib/CLI: `python3 -m core.cli make <lat> <lon> <alt>` / `decode <p:...>`.
