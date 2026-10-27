# Deployment Checklist (single-image)

## Required gates

- [ ] Exact Git SHA approved for deployment.
- [ ] `Pilot CI / PWA validation` passed for that SHA.
- [ ] Combined image digest from canonical workflow recorded.
- [ ] `.env` pins `PUNKTO_IMAGE` by digest (not tag).

## Host actions

- [ ] `docker compose pull`
- [ ] `docker compose up -d --force-recreate`
- [ ] `/health` returns 200
- [ ] `/node/info` returns expected build revision
- [ ] `/publication/root.json` is reachable

## Browser checks

- [ ] PWA loads from same origin
- [ ] Read path works from static publication
- [ ] Publish path works through `/submit`
- [ ] No `/pull`, `/sync`, or `/push` browser read calls

## Rollback readiness

- [ ] Previous digest retained
- [ ] Data volume backup exists
- [ ] Rollback command rehearsed
