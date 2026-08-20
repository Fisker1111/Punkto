# AZ Current Task

Status: **ACTIVE — Pilot_1 Slice 3.5: test1 joins the public Punkto network**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Goal

Turn `test1` from a static-only staging site into a **normal independent Punkto node**, using the same public-node model that an operator anywhere in the world would use.

The intended architecture is:

```text
test1 PWA
   ↓ same origin
test1 local relay + local persistent atom store
   ↓ normal Punkto peer/API sync
node1 + node2
```

This is **not** a special staging shortcut.

## Core rule

**Do not connect test1 directly to node1/node2 databases or filesystems.**

Use the existing Punkto public relay/peer mechanism only. `test1` must have its **own relay, its own persistent data volume, and its own node identity**, with node1/node2 configured as ordinary peers/seeds using the same mechanism documented for a fresh Punkto installation.

Reference files already in the repo:

- `deploy/README.md`
- `deploy/docker-compose.yml`
- `deploy/node1/Caddyfile` (reference same-origin relay proxy pattern)

The repo's documented model is `web + relay`, with `PUNKTO_PEERS` for comma-separated peer relay URLs and a persistent relay data volume.

## Starting application version

Keep the currently approved/deployed Pilot_1 Slice 3 PWA exactly at:

`7f9b22b40173d3c0da0779458e8f72671cbeb003`

Expected marker:

`pilot1-slice3-board-2026-08-20-1`

This task is operations/integration only. **Do not edit Punkto product/application code.**

## Required approach

1. **Inspect before changing anything.**
   - document the current test1 Caddy/static deployment and Docker topology;
   - determine whether any existing container/config/volume is shared with node1/node2 or other production services;
   - if a change would risk shared production infrastructure, stop and report before making it.

2. Give test1 an **isolated local relay**.
   - separate container/service identity from production;
   - separate persistent atom-store volume/data directory;
   - separate node name/identity, e.g. `test1` / `punkto-test1`;
   - do not reuse node1/node2 relay data volumes.

3. Configure test1's relay peers using the normal public configuration mechanism:
   - node1 public relay/API URL;
   - node2 public relay/API URL;
   - use `PUNKTO_PEERS` or the equivalent existing supported node config;
   - do not add a bespoke test-only fetch path.

4. Make the test1 PWA talk to **its own relay on the same origin**, like a normal Punkto installation.
   - proxy the existing relay endpoints from `https://test1...` to the local test1 relay using the established Caddy pattern;
   - preserve the Slice 3 static PWA tree and no-cache app-shell behavior;
   - do not point browser JavaScript directly at node1/node2.

5. Start the isolated test1 relay and allow normal peer synchronization.

6. **Do not create automated test/public atoms.**
   - the node may be capable of normal writes because it is a real Punkto node;
   - for Slice 3.5 verification, use existing public atoms only;
   - if there are no synced real atoms available, report that honestly rather than fabricating activity.

## Acceptance checks

All of the following should be verified and reported:

1. `test1` still serves Slice 3 marker `pilot1-slice3-board-2026-08-20-1`.
2. `test1/health` returns successfully from the **local test1 relay**.
3. `test1/info` or the equivalent node-info endpoint identifies test1's own node/relay, not node1/node2.
4. Peer-sync logs show successful normal synchronization with node1 and/or node2.
5. test1's local relay store contains real atoms learned through normal peer sync when such atoms are available.
6. `test1/feed`, `test1/latest`, or equivalent supported public endpoints return the locally synchronized data.
7. In a fresh browser, the PWA loads without runtime/module errors and reads from test1 same-origin API.
8. Find one **existing real synchronized atom** if available and verify on test1:
   - beacon/atom is reachable in the Pilot UI;
   - selecting/focusing it opens the Slice 3 board sheet;
   - root message remains primary;
   - replies, if present, render as flat 2D content;
   - closing the sheet returns to the same map context.
9. No direct DB/filesystem connection from test1 to node1/node2 exists.
10. node1 and node2 application versions/config/data remain untouched.
11. No Slice 4 work is started.

## Safety / isolation requirements

- **No direct database access.**
- **No shared relay volume with node1/node2.**
- **No production node restart/config change unless absolutely unavoidable; if unavoidable, STOP and ask first.**
- Prefer an isolated Docker Compose project/service/volume namespace for test1.
- Back up the current test1 deployment/config before conversion.
- Preserve a straightforward rollback to the current static-only Slice 3 test1 state.
- Do not delete the existing Slice 2/3 backups.

## What success means

Slice 3.5 is successful when test1 behaves like an independently operated Punkto installation that discovers/synchronizes public atoms through the ordinary peer/API mechanism, while still serving the Pilot_1 Slice 3 client.

This is also a small real-world federation/self-hosting test: **if an operator in another country configured a new Punkto node against the same public peers, the topology should be materially the same.**

## Completion report

Return a concise report containing:

- test1 topology before/after;
- test1 relay/container + persistent volume identity;
- peer configuration (URLs may be redacted if needed, but identify node1/node2 logically);
- sync result and atom count;
- `/health` + `/info` result;
- exact PWA SHA/version marker still served;
- real-atom board-sheet browser verification result;
- node1/node2 untouched verification;
- rollback location/method;
- any limitation or blocker.

Do **not** deploy to node1/node2. Do **not** start Slice 4. Stop after Slice 3.5 verification.