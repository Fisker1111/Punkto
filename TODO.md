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
- [ ] 8.2 Implement append-only atom log
- [ ] 8.3 Add node doctor script
- [ ] 8.4 Add rate limits and size limits
- [ ] 8.5 Define cache / Cloudflare policy
- [ ] 8.6 Document public API
- [ ] 8.7 Add backup and restore scripts
- [ ] 8.8 Fresh install guide from clean VM
- [ ] 8.9 Launch candidate checklist

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
- Fast-forward/cursor design is being documented in `docs/sync-fast-forward.md`
- Backup/restore must be tested

Next implementation tasks:
- Append-only atom log
- Feed cursor
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
- [ ] Rate limits active
- [ ] Cache policy active
- [ ] API docs complete
- [ ] Fresh install works
- [ ] No secrets exposed in /status or /node/info
- [ ] node1/node2 healthy
- [ ] Public launch note drafted
