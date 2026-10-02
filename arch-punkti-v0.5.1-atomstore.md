# Punkto 1.1 — Punkti v0.5.1 atom store, sync and World data path

## Source of truth
Notion task "Punkto 1.1 — real two-node atom store, sync and World data path"
(3ed8117d-813e-81a7-95bc-d9a87dfef943). Follow it exactly. Do not expand scope.

## Terminology a reviewer must know
- **Punkti atom (canonical v0.5.1, frozen)**: immutable object with exactly the
  fields `t, h, x, fp, sig`.
    - signing input = UTF8(`t_decimal + "|" + h + "|" + x + "|" + fp`)
    - `mid = lowercase_hex(SHA256(signing_input))`
    - `sig` is intentionally NOT part of the MID.
- **Legacy relay** (`relay/relay.py`, `punkto-web`/`punkto-relay` images): the
  pre-existing Punkto relay. It is Functioning today only as a small legacy feed
  (2 atoms, old `punkto`/`atom_id=SHA256(canonicalJSON)` model) and backs the
  preserved **Explorer** deployment plus legacy `/atom /latest /feed` paths.
  It does NOT support the v0.5.1 atom semantics. Per the task we must NOT
  silently replace a functioning backend and must NOT disturb Explorer.

## Decision: additive, separate atom store (not a rewrite of the legacy relay)
A new self-contained service **`punkto-atoms`** on each node implements the
canonical v0.5.1 atom store + API + peer sync. It runs alongside the legacy
`punkto-relay`. Rationale:
- Legacy relay's retention/serving policies (prune by time+count, accept-recent
  24h window, rate limits) are incompatible with "durable immutable atom store".
  Reusing it would clobber the store's durability and dedup guarantees.
- Additive deployment preserves the Explorer/legacy client untouched and keeps
  rollback trivial (remove the added service/proxy lines).

## Storage choice: SQLite (stdlib `sqlite3`), WAL
- Single file, ACID, survives restart/reboot by construction.
- `UNIQUE` index on `mid` enforces dedup at the storage layer.
- Indexed `t` column + stored lat/lon/alt columns serve spatial+time queries for
  World efficiently. Atom bytes stored verbatim (canonical fields + sig), never
  rewritten.
- No distributed SQL / consensus / Kafka / extra infra — consistent with the
  task's "smallest suitable persistence" and "no heavy platforms" constraints.
- Node2 has 961MB RAM; SQLite is minimal-footprint.

## Canonical atom semantics (implement exactly)
- Atom object has fields `t, h, x, fp, sig`.
- `t` = Unix time in milliseconds (decimal integer).
- `h` = canonical 3D spatial geohash, 12 base32 chars, from
  `core/geohash3d.encode(lat, lon, alt)` (existing repo primitive).
  `geohash3d.decode(h)` gives center lat/lon/alt (+errors).
- `x` = message / human content (UTF-8 string).
- `fp` = author fingerprint / identity string (World's `identity`).
- `sig` = Ed25519 signature over the signing input (see above); base64 string.
- signing input = f"{int(t)}|{h}|{x}|{fp}" encoded UTF-8.
- `mid` = `hashlib.sha256(signing_input).hexdigest()` (already lowercase hex).
- Validation on submit: MID is recomputed from canonical signing input and MUST
  match; `t` integer within range; `h` valid geohash; `x`/`fp` present and
  bounded; `sig` present. Reject malformed records. Never trust a client-supplied
  MID. Dedup: an already-known `mid` returns duplicate, stored once.

## Public HTTP API (served by the `punkto-atoms` service, proxied by Caddy)
- `GET /atoms/v1/mid/{mid}`            -> single atom or 404.
- `GET /atoms/v1/feed`                 -> spatial bounds + time/range query for
  World. Query params: min_lat, max_lat, min_lon, max_lon, min_t, max_t, limit.
  Response items include decoded lat/lon/alt, t, message(=x), identity(=fp), mid.
- `POST /atoms/v1`                     -> submit a signed atom {t,h,x,fp,sig};
  201 accepted (return mid), 200 duplicate, 4xx validation error.
- `GET /atoms/v1/info`                 -> replication/sync info: count, head
  sequence, peer url, last sync status/at, peers list.
- `GET /atoms/v1/sync?since=<seq>`     -> incremental inventory for peer
  convergence (atoms with stored seq > since). Head seq via /info or /sync?since=0.
- `GET /atoms/v1/health`               -> ok.

## Peer sync (node1 <-> node2), simple pull with sequence cursor
- Each node has `PUNKTO_ATOMS_PEERS` (other node's base URL).
- Background loop every ~20s: GET `{peer}/atoms/v1/info`, read peer head seq;
  if peer head > local seq, GET `{peer}/atoms/v1/sync?since=<local seq>` and
  append each atom through the SAME validate+dedup path as local submits.
- Idempotent by construction (UNIQUE mid). Duplicates never create extra rows.
- Temporary outage: failures logged, cursor not advanced on failure, retried next
  cycle -> no data loss, converges after reconnect.
- No central-primary requirement: both nodes pull from each other independently.

## Proof (automated integration tests — required, results recorded in Notion)
Test harness (local, two in-process stores or two ephemeral servers) must prove:
1. submit A to node1 -> A reaches node2
2. submit B to node2 -> B reaches node1
3. resend same atom -> stored once (dedup)
4. stop/disconnect node2
5. submit more atoms to node1
6. restore node2
7. node2 catches up
8. repeat direction node2 -> node1
9. restart service -> stores retain identical expected mid set
10. compare full mid sets on both stores -> identical.

## World wiring (keep rendering/UI unchanged)
- `world/src/atomsAdapter.ts` keeps the `AtomAdapter` interface +
  `getAtoms(bounds, time)`. Replace the fixture-backed default with a real
  adapter that calls the atom store `/atoms/v1/feed` (same-origin on punkto.xyz /
  test1, or configured base URL), mapping each API item to the existing
  `WorldAtom { id, x(lon), y(lat), altitudeM, t, message, identity, color }`.
  Empty-world state when the store returns no matching atoms. Fixture mode
  retained only as a dev flag.

## Deployment (both nodes)
- New container `punkto-atoms` (Python, sqlite) in `deploy/docker-compose.yml` on
  node1 and node2; data on a named volume; service NOT host-port-exposed.
- Caddy: add proxy for `/atoms/v1/*` (and `/atoms/v1`) to `atoms:8020` in the
  `punkto_relay` snippet of both nodes' `~/punkto/Caddyfile`.
- `PUNKTO_ATOMS_PEERS` node1 -> https://node2.punkto.xyz ; node2 -> https://node1.punkto.xyz.
- Punkto World v1.tar built from the updated world/ branch; deploy static build
  to /var/www/punkto-v1 on both nodes so punkto.xyz (and test1 staging when
  ready) read the real atom source.
- Do NOT touch explorer.punkto.xyz, legacy relay, or unrelated services.

## Security
- No DB ports exposed publicly. Only proxied API endpoints public.
- Validate input sizes/types on every endpoint. Max body ~64KB.
- No secrets/SSH keys/tokens in repo or client code.
- Preserve TLS (Caddy auto-HTTPS) and existing reverse-proxy layout.

## Branch / rollback
- Dedicated branch: `feat/punkti-v0.5.1-atomstore` branched from
  `world/v1.0-cutover` (c080aba) — the current live production base.
- Do NOT merge to main. Preserve rollback: keep a Caddyfile + docker-compose
  backup on each node before editing; test1 staging proves the path before prod.
