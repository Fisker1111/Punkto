# punkto.xyz — single-image cutover record

CEO-OS Issue #16. Production state after the cutover on 2026-10-22 (UTC).

## Deployed artifact

| Item | Value |
| --- | --- |
| Image | `ghcr.io/fisker1111/punkto:0.7.0-draft.2` |
| Digest | `sha256:8d8ecc2420c05aa039411f679ba5d88f0b52130d5b01baa12d91b71303ee298a` |
| Revision label | `ac3684658506c8f6d5b5ecacc16adaa5edf25e1f` |
| Platforms | `linux/amd64`, `linux/arm64` |
| CI | https://github.com/Fisker1111/Punkto/actions/runs/39790738985 |
| Source branch | `feat/punkto-single-image` (PR #114) |

Candidate predecessor `0.7.0-draft.1`
(`sha256:435e2fd356a3cfc6e40f9df6c5f33acdcacc8ba79dfeaf3767c280e2d323dc6e`,
CI run 39789447743) passed acceptance first; `0.7.0-draft.2` adds only the
`/p/`-scoped SPA fallback fix and carries the same acceptance evidence.

## Host layout (node1)

- `/opt/punkto/app/docker-compose.yml` — one service, loopback publish `127.0.0.1:18080:8000`,
  networks `punkto_punkto_internal`, bind mounts `config.yml` (ro) and `data/`.
- `/opt/punkto/app/config.yml` — one operator file: node name `punkto.xyz`,
  `public_url: https://punkto.xyz`, peers `[]`, global subscription, `/data`, branding.
- `/opt/punkto/app/.env` — image pinned by digest.
- `/opt/punkto/app/data/` — clean store created at cutover (empty; one deliberate atom).
- Caddy (`punkto-web-1`, host `~/punkto/Caddyfile`) terminates TLS for
  `punkto.xyz` and reverse-proxies the whole origin to `punkto-app-1:8000`.
  Backup of the previous config: `~/punkto/Caddyfile.rollback-20261022`.

No operator-specific code, build, environment variable or file name exists in the
image: the same digest runs unchanged for any domain.

## Route layout (same origin, one port)

| Path | Serves |
| --- | --- |
| `/`, `/*.js`, `/*.json`, assets | bundled PWA |
| `/p/<id>` | PWA (client route, SPA fallback) |
| `/api/hello`, `/api/pull`, `/api/push`, `/api/sync` | node protocol aliases |
| `/api/health`, `/api/ready`, `/api/node/info` | operational aliases |
| `/hello`, `/pull`, `/push`, `/sync`, `/health`, `/ready`, `/node/info` | native peer/ops surface |

Legacy relay routes (`/atom`, `/feed`, `/info`, `/latest`, `/atoms/v1/*`) return
404 on `punkto.xyz`; they are no longer served there.

## Acceptance evidence

Container acceptance ran on node1 against two differently named instances of the
same digest (`punkto-accept-a`, `punkto-accept-b`), then was repeated on the
production container.

| Proof | Result |
| --- | --- |
| 1. Fresh store (`/api/node/info` `store.valid == 0`) | pass (both instances) |
| 2. PWA served from the same container | pass (`/` 200 HTML, same origin) |
| 3. Create/read through the API path | pass (`/api/push` admitted, `/api/pull` returned it) |
| 4. Restart/recreate preserves data | pass (same epoch `78b75972…`, record survived) |
| 5. Second, differently named instance from the same image | pass (`accept-b`, distinct epoch) |
| 6. Layer-3 sync between the two instances | pass (atom pushed to A appeared on B) |
| 7. Unknown Layer-4 payload preservation | pass (`x` byte-identical, nested unknown keys intact) |
| 8. One instance without `punkto.xyz` | pass (instance B advertises its own URL only) |
| 9. Health/readiness/version | pass (`/api/health` 200, `/api/ready` ready, version from build) |
| 10. No `punkto.xyz` special code in the image | pass (`grep -ril punkto.xyz /app /srv` → no matches) |

Additional: PID 1 runs as uid/gid `10001`; duplicate `/api/push` returns
`duplicate`; tampered envelopes are rejected; `/p/<id>` serves the PWA while
unknown API-looking paths 404.

### Production store after cutover

- epoch `78b75972ca8641ff9fd4020974d0335b`, `valid: 1`, `candidates: 0`,
  `corrupt_lines: 0`, `duplicate_lines: 0`.
- First (deliberate, human-readable) atom:
  `punkti/0.6:79c297fece1e921624e70e8ce919188cb8acec38f99436a2f07dc0bcd79e8e88`
  — author `hermes`, `p:u07qskym6vu8`, text
  “Punkto 1.0 — first deliberate atom on the clean Punkti 0.6 store at punkto.xyz.”
- Zero legacy atoms were migrated or reinterpreted.

Public checks (from outside the host):

- `https://punkto.xyz/` 200 `text/html` (bundled PWA), `Cache-Control: no-store`.
- `https://punkto.xyz/api/health` → `{"service":"punkti-node","status":"ok","version":"0.7.0-draft.2"}`.
- Certificate: `CN=punkto.xyz`, Let's Encrypt, valid.
- `https://punkto.xyz/p/79c297fe` → PWA (200).

## Rollback

Legacy containers (`punkto-web-1`, `punkto-relay-1`, `punkto-atoms-1`) and the
previous static bundle `/srv-punkto-v1` were left running/on disk during cutover.
They no longer serve `punkto.xyz`, but remain the tested rollback path:

```sh
# 1. Restore the previous routing (legacy static bundle + relay/atoms).
ssh root@node1.punkto.xyz
cat ~/punkto/Caddyfile.rollback-20261022 > ~/punkto/Caddyfile
docker exec punkto-web-1 caddy reload --config /etc/caddy/Caddyfile

# 2. Optionally stop the new container (the volume stays for later inspection).
cd /opt/punkto/app && docker compose up -d --force-recreate   # or scale/stop
```

To roll back the image only, pin the previous digest in
`/opt/punkto/app/.env` (`sha256:435e2fd3…` for `0.7.0-draft.1`) and
`docker compose up -d`. The store is unchanged by image rollback; only delete
`/opt/punkto/app/data` if a fresh store is intended.

## Notes for the Founder review

- `punkto.xyz` now serves the bundled PWA. The Punkto World v1 experience that
  previously occupied the root is retained on disk (`/srv-punkto-v1`) and keeps
  running at `https://test1.punkto.xyz`; it is not bundled in this image and can
  be re-exposed at any path or host once a decision is made.
- `node1.punkto.xyz`, `explorer.punkto.xyz` and `test1.punkto.xyz` still use the
  legacy stack; removing that stack is a follow-up once this deployment is
  accepted.
- Production has `network.peers: []`. Joining a mesh is a config change to
  `network.peers` plus a recreate; no rebuild.
- No Punkti protocol freeze is implied: the node package is unchanged apart from
  operational route aliasing and static hosting.
