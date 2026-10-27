# Deployment Runbook (single-image, digest-pinned)

## Preconditions

- `Pilot CI / PWA validation` is green on the exact approved SHA.
- Published image digest is recorded from `punkto-image.yml` job summary.
- Target host has Docker and compose plugin.

## Configure

1. Set `PUNKTO_IMAGE` in `.env` to the exact digest:

```bash
PUNKTO_IMAGE=ghcr.io/fisker1111/punkto@sha256:<approved_digest>
```

2. Ensure `deploy/docker-compose.yml` and `config.yml` are present.

## Deploy

```bash
cd /opt/punkto/app
docker compose pull
docker compose up -d --force-recreate
```

## Verify

```bash
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18080/node/info
curl -fsS http://127.0.0.1:18080/publication/root.json
```

- Confirm browser reads from static publication and publishes via `/submit`.
- Confirm no deployment uses floating tags (`latest`, branch tags).

## Rollback

1. Restore previous digest in `.env`.
2. Recreate containers:

```bash
docker compose pull
docker compose up -d --force-recreate
```

3. Re-run verification commands.
