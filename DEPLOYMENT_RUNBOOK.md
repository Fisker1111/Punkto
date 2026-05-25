# Deployment Runbook

> Step-by-step procedure for deploying a new Punkto release to `server1` and `app2`.

---

## Pre-Deploy Checklist

- [ ] PR merged to `main`
- [ ] GitHub Actions `docker.yml` workflow completed successfully (check Actions tab)
- [ ] Docker images pushed to `ghcr.io/fisker1111/punkto-web:<tag>` and `ghcr.io/fisker1111/punkto-relay:<tag>`
- [ ] Hard marker noted from PR description (e.g., `v86-hard-marker-2026-05-25-1`)
- [ ] No active manual testing in progress on either node (announce in chat if uncertain)

---

## Deploy: server1 (app1.punkto.xyz)

```bash
# SSH to server1
ssh root@web1.punkti.net
cd /path/to/punkto/deploy/server1

# Pull latest images
docker compose pull

# Recreate containers with fresh images (do NOT use only `caddy reload`)
docker compose up -d --force-recreate

# Tail logs for 30 seconds to confirm no crash loop
docker compose logs -f --tail=200 web relay
# Ctrl+C once stable

# Run smoke tests locally on node (or from AZ)
bash /path/to/punkto/deploy/verify.sh app1.punkto.xyz "<HARD_MARKER>"
```

Expected: all 6 smoke tests green.

---

## Deploy: app2 (app2.punkto.xyz)

```bash
# SSH to app2
ssh root@web1.punkti.net -p <port_if_different>
cd /path/to/punkto/deploy/app2

docker compose pull
docker compose up -d --force-recreate
docker compose logs -f --tail=200 web relay

bash /path/to/punkto/deploy/verify.sh app2.punkto.xyz "<HARD_MARKER>"
```

Expected: all 6 smoke tests green.

---

## Post-Deploy Verification (from AZ)

```bash
# Run from Agent Zero (or any internet-connected machine)
for NODE in app1.punkto.xyz app2.punkto.xyz; do
  echo "=== $NODE ==="
  bash /a0/usr/projects/punkto/deploy/verify.sh "$NODE" "<HARD_MARKER>"
  echo
done
```

Both nodes must report identical hard markers and green status.

---

## Rollback Procedure

### When to Rollback

- Smoke tests fail after 2 remediation attempts
- Runtime error visible in console (`TypeError`, `ReferenceError`, missing imports)
- Relay `/health` returns 5xx for > 60 seconds

### How to Rollback

```bash
NODE=app1   # or app2
cd /path/to/punkto/deploy/$NODE

# Pin previous known-good tag
export RELAY_TAG=v85-hard-marker-2026-05-22-1
export WEB_TAG=v85-hard-marker-2026-05-22-1

# Override compose to use pinned images
docker compose down
docker pull ghcr.io/fisker1111/punkto-web:$WEB_TAG
docker pull ghcr.io/fisker1111/punkto-relay:$RELAY_TAG

# Temporarily tag pinned images as latest (or edit compose file)
docker tag ghcr.io/fisker1111/punkto-web:$WEB_TAG ghcr.io/fisker1111/punkto-web:latest
docker tag ghcr.io/fisker1111/punkto-relay:$RELAY_TAG ghcr.io/fisker1111/punkto-relay:latest

docker compose up -d --force-recreate
```

After rollback, rerun smoke tests with the previous marker.

### Notify

- Announce rollback in team chat with: marker rolled back from, marker rolled back to, failure symptom.
- Do not re-deploy failed version until Root Cause Analysis (RCA) is added to `DEPLOYMENT_TROUBLESHOOTING.md`.

---

## Emergency: Full Node Reset

Use only if node state is corrupted (e.g., broken Atom data, relay unresponsive after restart).

```bash
cd /path/to/punkto/deploy/$NODE
docker compose down
docker system prune -f    # removes dangling images only; data volume intact
docker compose pull
docker compose up -d --force-recreate
```

**Warning:** `docker compose down -v` would delete relay data. Never use `-v` without explicit Human approval.
