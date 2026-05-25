# Deployment Troubleshooting

> Decision tree when a post-deploy smoke test fails.

---

## Flowchart: Where to Start

```
Deploy completed, smoke tests run
          │
          ▼
┌────────────────────────────┐
│ Hard marker missing / old  │──▶ Stale Docker image (see §1)
└────────────────────────────┘
          │ no
          ▼
┌────────────────────────────┐
│ JS 200 but wrong headers?  │──▶ Caddy matcher too narrow (see §2)
└────────────────────────────┘
          │ no
          ▼
┌────────────────────────────┐
│ PWA icons 404?             │──▶ Missing static assets (see §3)
└────────────────────────────┘
          │ no
          ▼
┌────────────────────────────┐
│ Relay /health 5xx?         │──▶ Relay crashed (see §4)
└────────────────────────────┘
          │ no
          ▼
┌────────────────────────────┐
│ Browser black map / crash? │──▶ Lazy-init bug (see §5)
└────────────────────────────┘
          │ no
          ▼
        UNKNOWN — open issue, attach logs.
```

---

## §1. Stale Docker Image

**Symptom:** `curl` on `app.js` returns an older hard marker, or the file is identical to pre-deploy.

**Diagnosis:**
```bash
# On the node
docker compose images | grep punkto
# Compare digest vs ghcr.io tag digest
```

**Fix:**
```bash
docker compose pull --ignore-pull-failures
docker compose up -d --force-recreate
# Clear any reverse-proxy or browser cache, re-test
```

**Prevention:** always use `--force-recreate`, never trust in-place restarts.

---

## §2. Wrong Cache-Control Headers

**Symptom:** Browser caches old JS; users see stale UI.

**Diagnosis:**
```bash
curl -sI "https://app1.punkto.xyz/app.js" | grep -i cache-control
```

Expected: `no-cache, no-store, must-revalidate`.

**Fix:** Caddyfile `@app` matcher must cover all JS modules:
```caddyfile
@app not path /lib/* && path *.html *.js
header @app {
    Cache-Control "no-cache, no-store, must-revalidate"
    Pragma "no-cache"
    Expires "0"
}
```

After editing: `docker exec <caddy_container> caddy reload --config /etc/caddy/Caddyfile` + `docker compose up -d --force-recreate` if changes require rebuild.

---

## §3. PWA Icons 404

**Symptom:** `logo-192.png` or `logo-512.png` returns 404.

**Diagnosis:**
```bash
docker exec <web_container> ls /srv/pwa/logo-*.png
```

**Fix:** Rebuild web image (icons are baked in at `docker build` time).

---

## §4. Relay Crashed

**Symptom:** `/api/health` returns 5xx or times out.

**Diagnosis:**
```bash
docker compose logs --tail=100 relay
docker compose ps   # exit code >0?
```

Common causes:
- Missing `.env` or `data/` directory mounted
- Port conflict with existing process
- Python dependency version drift (pin `requirements.txt`)

**Fix:** Check `.env`, rebuild if needed:
```bash
docker compose build relay
docker compose up -d --force-recreate
```

---

## §5. Map Black / Lazy-Init Bug

**Symptom:** Map stays black on first visit, works after switching tabs.

**Root Cause (historic — PR #50):** `ui-map.js` initialized map before `#map` container was visible.

**Fix verified in app.js / ui-map.js:**
```js
// ui-map.js
export function initMapView({ getMap, initMap }) {
  if (!state.initialized) {
    initMap();
    state.initialized = true;
  } else {
    getMap()?.resize();
  }
}
```

If regression: revert to previous PR marker, file issue, attach console trace.

---

## §6. Browser Console Errors (Common)

| Error | Likely cause |
|---|---|
| `ReferenceError: X is not defined` | Stale cached JS — hard refresh + clear cache |
| `TypeError: Cannot read property 'x' of undefined` | Atom format mismatch — check relay `/feed` payload |
| `Uncaught SyntaxError: Unexpected token` | Mangled JS bundle — re-pull image (§1) |
| CORS errors on `/api/*` | Caddy missing `Access-Control-Allow-Origin` header |

---

## Escalation

1. **Auto-resolvable** (§1–§4): fix, rerun smoke tests, log fix in CHANGELOG.
2. **Regressive** (§5, §6): rollback immediately (see Runbook), notify team, file issue.
3. **Unknown:** preserve logs (`docker compose logs > logs-<node>-<timestamp>.txt`), notify Human, do not redeploy.
