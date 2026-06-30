# Deployment Smoke Tests

> Automated checks to run immediately after every deploy to both `node1` (node1) and `node2` nodes.

## When to Run

- After every `docker compose pull && up -d --force-recreate` on either node
- After every PR merge that touches `pwa/` or `relay/`
- From GitHub Actions (via `deploy/verify.sh`)

---

## Manual Quick Checks

```bash
NODE=node1.punkto.xyz   # or node2.punkto.xyz
EXPECTED_MARKER="v86-hard-marker-2026-05-25-1"   # fill in from PR

# 1. Hard marker present in deployed JS
echo "--- Hard marker in app.js ---"
curl -s -H 'Cache-Control: no-cache' "https://${NODE}/app.js" | grep -F "$EXPECTED_MARKER" | head -3

# 2. JS served with no-cache
echo "--- Cache-Control header on app.js ---"
curl -sI "https://${NODE}/app.js" | grep -iE 'cache-control|pragma|expires'

# 3. PWA icons reachable (not 404)
echo "--- PWA icons ---"
for size in 192 512; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://${NODE}/logo-${size}.png")
  echo "logo-${size}.png -> $code"
done

# 4. Relay /health green
echo "--- Relay health ---"
curl -s "https://${NODE}/health" | head -c 200
echo

# 5. Feed endpoint reachable
echo "--- Relay /feed (first 3 atoms) ---"
curl -s "https://${NODE}/feed?limit=3" | head -c 400
echo

# 6. HTML loads
echo "--- index.html title ---"
curl -s "https://${NODE}/" | grep -o '<title>[^<]*</title>'
```

---

## Pass / Fail Criteria

| Check | Pass | Fail |
|---|---|---|
| Hard marker present | grep returns exact marker string | empty / old marker → stale image |
| Cache-Control | `no-cache, no-store, must-revalidate` present | default or permissive caching |
| PWA icons | HTTP 200 for both sizes | 404 → missing assets |
| Relay /health | `{"status":"ok"...}` or HTTP 200 | 5xx / timeout → relay down |
| /feed | Valid JSON, HTTP 200 | 5xx → relay misconfigured |
| index.html | `<title>` present | 5xx / empty → Caddy misconfigured |

---

## Expected Post-Deploy Output (Green Deploy)

```
--- Hard marker in app.js ---
const APP_VERSION = "v86-hard-marker-2026-05-25-1";
--- Cache-Control header on app.js ---
cache-control: no-cache, no-store, must-revalidate
pragma: no-cache
expires: 0
--- PWA icons ---
logo-192.png -> 200
logo-512.png -> 200
--- Relay health ---
{"status":"ok","node":"punkto-relay","version":"0.5"}
--- Relay /feed (first 3 atoms) ---
[{"punkto":"p:...","t":...,"sig":"..."},...]
--- index.html title ---
<title>Punkto</title>
```

Any deviation triggers the **Troubleshooting Runbook** → `DEPLOYMENT_TROUBLESHOOTING.md`.
