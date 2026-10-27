# Punkti 0.6 Mesh reference experiment

Self-contained Python implementation of the candidate L3 reset and generic spatial
peer replication. No imports from Punkto, relay, PWA, identity or application code.
This is an in-memory loopback reference, not production networking or a frozen
interoperability claim. See [the wire specification](../../docs/proposals/PUNKTI_0_6_MESH.md).

Requires Python 3.10+ and `cryptography` (see requirements-test.txt).

```sh
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests -v
python3 experimental/punkti-v0.6-mesh/tests/measure.py
```

Run from repository root on a host permitting loopback TCP. The tests must create
three actual HTTP servers. They intentionally fail rather than skip or mock the
wire when sockets are prohibited. Current verified status: **all 37 tests pass**
(including all 12 acceptance cases over real loopback HTTP), and the historical convergence
measurement (not rerun for XY_Z) converged in one round at 12/96/384 atoms. See
[docs/measurement.md](docs/measurement.md) for the measured reconciliation verdict.

## Modules

- `src/carrier.py`: strict JSON import, canonical C/S/MID/R framing, real Ed25519
  verification and validation states. JSON import does not offer byte-exact export;
  network storage preserves raw R. Unsupported carrier versions require an explicit
  opaque wrapper rather than guessing a malformed envelope's version.
- `src/spatial.py`: standard 2D geohash encode/decode, canonical exact decimal Z,
  immutable XY/Z subscriptions using lower-edge keys padded to 12 characters.
- `src/mesh.py`: independent stores, separate bounded unverified candidates,
  configured-peer discovery hints, real HTTP PUSH and Range PULL, scoped sequence
  resume cursors and snapshot MID sweeps. Invalid records are rejected. Unverified
  records cannot enter the valid store and cannot poison a valid representative.
- `tests/support.py`: seeded, reproducible keys and signed fixtures.
- `tests/test_mesh.py`: all twelve acceptance cases and additional wire checks.
- `tests/test_carrier.py`, `tests/test_store.py`: framing, provenance, parsing,
  resource limits, candidate separation and cursor boundary checks.
- `tests/measure.py`: real-HTTP varied-subset and larger-set/churn measurements.

## Minimal API sketch

Add `experimental/punkti-v0.6-mesh/src` to Python's module path. Start two
`Node` instances with `.start()`, mutually configure each other's `.url` in
`.peers`, then call `a.connect(b.url)`. Both PUSH directions precede both PULL
directions. Always `.stop()` nodes in a finally block. Call `.sync_known()`
periodically to retry configured peers; `.discover()` returns peer hints for
explicit selection. No central scheduler or coordinator is required.

`Node([Subscription(xy_lo='gggh', xy_hi='gggj', z_min='0', z_max='100')])` accepts only
that range, independently of application payload. `Node()` subscribes to all;
`Node([])` accepts nothing. `node.add(raw_R)` verifies and admits a local candidate
under the same subscription policy. Network candidates also include declared
address and a transport digest. `node.pull(peer, scope, limit=16)` automatically
resumes the saved peer/scope cursor. `mode='mid'` performs a fresh address sweep;
optional `lo`/`hi` bounds are full qualified addresses. Lower-level HTTP queries
can explicitly carry a previous returned token as `cursor` (SUBSCRIBE FROM).

The caller should serialize sync operations per node. Stores and snapshots are
in memory; disconnect/reconnect preserves the node object, while process restart
requires a new epoch and full catch-up. No deletion, durable storage, production
transport authentication or rate limiting is implemented. Future opaque wrappers
replicate only for unrestricted nodes because their spatial address is unknown.
Missing-set reconciliation is omitted because the measured PUSH + Range PULL
converges in one round across differing subsets (see docs/measurement.md).
