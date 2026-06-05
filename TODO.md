# Punkto TODO — Public Readiness

Punkto is the reference app built on Punkti. Punkto.xyz is the first public reference deployment. Before broader public launch, the focus is boring reliability: durable storage, deployability, sync safety, public node status, and clear docs.

## Current baseline

- v100 live on node1/node2
- ROOT/REPLY public threads live
- Public /status page live
- Public /node/info JSON live
- /feed and data flow visible
- node1/node2 hostnames working
- PWA is reference UI
- Docker node is public workhorse

## Phase 8 — Public Node Hardening

- [ ] 8.0 Define public-readiness checklist
- [~] 8.1 Design durable storage model — in progress; see `docs/sync-fast-forward.md`
- [~] 8.2 Implement append-only atom log — durable log live; rate/size limits remain follow-up
- [x] 8.3 Add node doctor script (`scripts/node-doctor.py`)
- [~] 8.4 Add live-forward acceptance/serving policy — implemented config policy; rate/size limits remain follow-up
- [x] 8.5 Define cache / Cloudflare policy
- [x] 8.6 Document public API
- [x] 8.7 Add backup and restore scripts
- [x] 8.8 Fresh install guide from clean VM
- [x] 8.9 Launch candidate checklist

## Storage direction

```
/data/atoms.log.jsonl = append-only truth
/data/punkto.db = SQLite index/cache
```

Notes:
- Atom log is durable truth
- SQLite can be rebuilt
- Dedupe by atom_id
- Feed survives restart
- Live-forward serving is policy-limited while the atom log remains durable truth
- Fast-forward/cursor design is being documented in `docs/sync-fast-forward.md`
- Backup/restore must be tested

Next implementation tasks:
- Node doctor script
- Rate limits and size limits
- Node-seen/log sequence envelope or sidecar metadata
- Static feed snapshots

## Node roles

- **Public sharing node:** DNS/IP reachable, serves /status, /feed, /node/info
- **Browser/PWA node:** local/offline/push-pull only
- **Future phone node:** stronger local node with secure keys and background sync

## Public-only rule

- Punkto is a public BBS for reality
- No private chat in core
- Signed atoms provide authorship, not privacy
- Admin/config changes remain SSH/server-side

## Go Public checklist

- [ ] Durable atom storage live
- [ ] Restart persistence tested
- [ ] Backup/restore tested
- [ ] Node doctor passes node1/node2
- [x] Rate limits active — per-IP POST /atom rate limit (default 30/60s, configurable)
- [ ] Cache policy active
- [ ] API docs complete
- [ ] Fresh install works
- [ ] No secrets exposed in /status or /node/info
- [ ] node1/node2 healthy
- [ ] Public launch note drafted

## IP-first bootstrap follow-ups

- Keep DNS/HTTPS as convenience layers, not protocol requirements.
- Add future structured `network.seed_nodes` entries with `url` plus `node_id` once config parsing supports them.
- Add future `/data/known-peers.json` learned peer cache for peer memory.
- Consider future `/peers`, signed node records, QR/imported peer records, manual peer add, peer capabilities, `last_seen`, and trust levels.
- Move backfill trust toward node identity/fingerprint rather than DNS-only endpoint strings.
