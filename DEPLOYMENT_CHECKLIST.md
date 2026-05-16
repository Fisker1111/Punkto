# Punkto Deployment Checklist

## Golden rule

> Do not assume a commit is deployed just because GitHub Actions built an image.
> The running Docker container must be pulled and recreated explicitly.

---

## Standard deploy — after GitHub Actions build completes

Run on **each node** (server1 and app2):

```bash
docker compose pull
docker compose up -d --force-recreate
docker compose ps
```

All services must show `Up` or `running` in `docker compose ps`.

> ⚠️ `caddy reload` alone is NOT enough after a code change. Always pull + force-recreate.

---

## Node inventory

| Node | Host | Directory |
|---|---|---|
| server1 | `punkto.xyz` | `~/punkto` |
| app2 | `app2.punkto.xyz` | `~/punkto` |

Both nodes must be deployed on every release. Never leave one node on an older image.

---

## Verification after deploy

### 1. Hard marker check

```bash
curl -s https://punkto.xyz/ | grep 'hard-marker'
curl -s https://app2.punkto.xyz/ | grep 'hard-marker'
```

Expected: the hard marker string from the current `pwa/app.js` (e.g. `v53-hard-marker-2026-05-16-2`)

### 2. Container health

```bash
docker compose ps
```

Expected: `web` and `relay` show `Up` or `running`.

### 3. Cache-control headers

```bash
curl -I https://punkto.xyz/app.js | grep -i cache
curl -I https://punkto.xyz/ui-shell.js | grep -i cache
```

Expected:
```
cache-control: no-cache, no-store, must-revalidate
```

### 4. New module files reachable

```bash
curl -o /dev/null -sw '%{http_code}' https://punkto.xyz/ui-shell.js
curl -o /dev/null -sw '%{http_code}' https://punkto.xyz/ui-text.js
curl -o /dev/null -sw '%{http_code}' https://punkto.xyz/ui-map.js
```

Expected: `200` for each.

---

## Browser test after deploy

1. Open a fresh **InPrivate / Incognito** window  
   OR visit `https://punkto.xyz/reset.html`
2. Open `https://punkto.xyz/`
3. Open DevTools console — confirm the hard marker matches the deployed commit
4. Confirm bottom nav shows: **Text | Map | + | Settings**
5. Confirm Settings panel is **closed** on first load
6. Tap **Map** → tiles load, location dot visible
7. Tap **Text** → feed or empty state
8. Tap **+** → create modal opens
9. Tap **Settings** → panel slides up, Settings button highlights

---

## Caddyfile changes

Caddyfile is NOT inside the Docker image. It lives on the host at:

```
~/punkto/Caddyfile   (server1)
~/punkto/Caddyfile   (app2)
```

After editing Caddyfile on the host:

```bash
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

No container restart needed for Caddy-only changes. But if in doubt, force-recreate anyway.

---

## GitHub Actions

- Workflow: `.github/workflows/docker.yml`
- Triggers on push to `main`
- Builds and pushes image to `ghcr.io/fisker1111/punkto-web:latest`
- Build takes ~1 minute
- **Check Actions tab before deploying to confirm the build succeeded**
- A failed build means the registry still has the old image — do not pull until fixed

---

## Rollback

```bash
# Pin to a specific image digest or tag if needed
docker compose down
docker pull ghcr.io/fisker1111/punkto-web:<previous-sha>
# Edit docker-compose.yml to pin the image, then:
docker compose up -d
```

Or revert the Git commit, let Actions rebuild, then redeploy.

---

## Hard marker convention

Every release must bump the hard marker in `pwa/app.js`:

```js
const HARD_MARKER = 'v<N>-hard-marker-<YYYY-MM-DD>-<seq>';
```

Examples:
```
v53-hard-marker-2026-05-16-2
v54-hard-marker-2026-05-17-1
```

The hard marker is logged to the browser console on boot and must appear in the page source. Use it to confirm which exact build is running.

---

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser shows old version after deploy | `docker compose up` without `--force-recreate` | Force-recreate containers |
| Phone/Edge still shows old version after force-recreate | Browser disk cache | InPrivate + Ctrl+Shift+R |
| `ui-shell.js` returns 404 | Container has old image (pre-v52) | `docker compose pull` then force-recreate |
| Map is black on first load | MapLibre initialized while container hidden | Bug in ui-map.js lazy init — do not call initMap at boot |
| Settings panel open on first load | `#settings-menu` has `.open` class in HTML | Remove `.open` from the HTML source |
| One node serves different version than the other | Deploy not run on second node | Deploy and verify both nodes after every release |
