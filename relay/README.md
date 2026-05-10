# punkto-relay v0.1

A standalone, single-file Python server implementing the **relay** role of the [Punkto Flow TV architecture](../punkto.relay.md). Relays carry the live network: they accept new atoms from clients, forward them to peers, and serve a small rolling window of recent atoms via `/latest`. They do **not** maintain a queryable historical archive — that's the [archive role](../punkto.relay.md#5-the-archive-role-optional-possibly-paid).

> The protocol stores forever. Relays carry the now. Clients keep what they witnessed. Archives serve those who ask.

## Quick start

```sh
pip install -r requirements.txt
python3 relay.py
```

Server listens on `127.0.0.1:8000` by default. Verify it's up:

```sh
curl http://127.0.0.1:8000/health
# {"status":"ok","node":"relay-<host>","buffer_size":0}
```

Post an atom:

```sh
curl -X POST http://127.0.0.1:8000/atom \
  -H 'Content-Type: application/json' \
  -d '{"punkto":"p:u07qsuustfsh","t":1745598371000,"f":"alice","x":"hello"}'
```

Read the live flow:

```sh
curl http://127.0.0.1:8000/latest
```

## Configuration

All config is via environment variables. See `.env.example` for a complete file you can copy.

| Var | Default | Purpose |
|---|---|---|
| `PUNKTO_HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` behind a reverse proxy. |
| `PUNKTO_PORT` | `8000` | Listen port. |
| `PUNKTO_DATA_DIR` | `./data/` | Where `atoms.ndjson` and `sync_state.json` live. |
| `PUNKTO_NODE_NAME` | `relay-${hostname}` | Identifier returned in `/info` and `/latest`. |
| `PUNKTO_PEERS` | *(empty)* | Comma-separated peer URLs to pull from, e.g. `https://app2.example.com,https://app3.example.com`. |
| `PUNKTO_BUFFER_ATOMS` | `10000` | Hard cap on buffered atom count. |
| `PUNKTO_BUFFER_HOURS` | `168` (7 days) | Atoms older than this are pruned. |
| `PUNKTO_LATEST_LIMIT` | `100` | Max atoms returned by `GET /latest`. |
| `PUNKTO_SYNC_INTERVAL` | `30` | Seconds between peer-pull cycles. |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/atom` | Submit an atom. Returns `201 {status:accepted, atom_id, punkto}` or `200 {status:duplicate, …}`. |
| `GET` | `/latest` | Up to `PUNKTO_LATEST_LIMIT` atoms, newest first. |
| `GET` | `/feed?since=<cursor>` | Backward-compat byte-offset feed. After any prune, returns `buffer_underflow:true` so clients reset. |
| `GET` | `/health` | Liveness — `{status:ok, node, buffer_size}`. |
| `GET` | `/info` | Node metadata, peers, buffer config and current size. |
| `GET` | `/p/<atom_id>` | Server-rendered HTML with OpenGraph + Twitter card meta for share previews. Falls back to a generic page if the atom has aged out. |
| `OPTIONS` | `/*` | CORS preflight. |

Atom validation rules:
- `punkto` (required): string matching `p:[0-9a-z]{12}(-[a-zA-Z0-9]+)?`
- `t` (required): integer Unix milliseconds, between 2020-01-01 and now+1day
- `f`, `x`, `sig`, and any other fields: optional, passed through unchanged
- `atom_id` is computed as `SHA-256(canonical_json_without_sig)` — never trusted from input

## Operator notes

**Disk:** With defaults (10K atoms, 7d window, ~200 bytes/atom), expect <5 MB of `atoms.ndjson`. Pruning rewrites the file atomically via `rename(2)`.

**Memory:** The buffer holds every atom in RAM plus a hash-set of atom_ids. ~80 MB is a comfortable upper bound at 10K atoms. Deduplication is O(1).

**Threading:** `ThreadingHTTPServer` handles each request in its own thread. All buffer mutations are guarded by a single `threading.Lock`. The peer-sync background thread is a daemon and uses the same lock.

**Cursor compatibility:** `/feed?since=<offset>` works as before until the first prune. After that, every old cursor returns `buffer_underflow:true` once and the client should reset to `since=0`. New clients should prefer `/latest`.

**Reverse proxy:** Run behind nginx/Caddy with TLS termination. Bind to `127.0.0.1` (default). Forward `/` to `http://127.0.0.1:8000` and let the proxy handle compression and HTTPS.

**Scaling:** A single relay handles thousands of writes/sec on commodity hardware. Run multiple relays in a peer mesh for redundancy; clients can write to any of them.

## Files

- `relay.py` — the server (single file, stdlib + `requests`)
- `requirements.txt` — `requests>=2.28.0`
- `.env.example` — annotated env template
- `systemd/punkto-relay.service` — Debian/Ubuntu unit file
- `test_relay.py` — smoke tests

## Running tests

```sh
python3 test_relay.py
```

Tests start a relay on `127.0.0.1:18000`, exercise every endpoint, and verify buffer rotation. They do not require pytest but will use it if available.

## Spec

Authoritative spec: [`../punkto.relay.md`](../punkto.relay.md). Atom format: [`../punkto.md`](../punkto.md). Sync model: [`../punkto.sync.md`](../punkto.sync.md).

## Verifying a production deployment

After deploying, run these from the host to confirm the relay is healthy and TLS is auto-renewing:

```bash
# 1. TLS certificate state and renewal
sudo certbot certificates                 # cert age + auto-renew configured
sudo systemctl list-timers | grep certbot # renewal timer is active

# 2. Relay service
sudo systemctl status punkto-relay         # active and enabled
sudo journalctl -u punkto-relay -n 50      # recent log lines

# 3. Public endpoints
curl -sI https://YOUR-DOMAIN/health        # 200 OK from public
curl -s  https://YOUR-DOMAIN/info | jq .   # buffer size, version, capabilities
curl -s  https://YOUR-DOMAIN/latest | head # recent atoms (NDJSON)

# 4. Peer sync state (if PUNKTO_PEERS is configured)
curl -s  https://YOUR-DOMAIN/info | jq '.peers'
```

If any of these fail or report unexpected values, check `sudo journalctl -u punkto-relay -n 200` for clues, and consult [`../punkto.relay.md`](../punkto.relay.md) for the expected behaviour.
