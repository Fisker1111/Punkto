# NairobiDot L3 clean-room experiment

This directory contains an independent Python implementation of the experimental
Punkti 0.6 carrier and loopback Mesh transport. Its `src/nairobidot/` package does
not import the reference implementation. This is an interoperability experiment,
not a production node or a deployment change.

Python 3.12+ and the implementation's `cryptography` dependency are required.
No additional dependencies are needed by the harness. Run from the repository root:

```bash
PYTHONPATH="$PWD/experimental/nairobidot-l3/src" python3 -m unittest discover -s experimental/nairobidot-l3/tests -v
python3 -m unittest discover -s experimental/nairobidot-l3/interop -v
```

Use the absolute `PYTHONPATH` shown above: a clean-room CLI test changes its
subprocess working directory. A relative path makes that existing test fail to
import the package. The interop suite does not use `PYTHONPATH`.

The interop command regenerates [the matrix](interop/interop_matrix.md) and
[the full JSON evidence](interop/interop_report.json), including on test failure.
It can also run as `python3 experimental/nairobidot-l3/interop/test_interop.py -v`.
Run the entire suite to regenerate the complete 14-row report.

## Process isolation and transport

`interop/ref_adapter.py` imports only the reference source tree;
`interop/nb_adapter.py` imports only the clean-room source tree. Each runs in its
own subprocess with inherited `PYTHONPATH` disabled. Stdlib and installed
cryptography remain available. The test runner imports neither implementation.
Static source checks and runtime module/path checks enforce that separation.

Both adapters accept `--stdin` for standalone mint/decode, or
`--serve config.json` for node RPC. Serve mode emits a JSON readiness line with
`url` and `epoch`. Commands and responses are one JSON object per line. Config
contains `subscriptions`, `peers`, and `port` (use 0 for an ephemeral port).
The RPC command names and mint fields follow the interop brief. The harness also
uses `configure` (explicit local peer configuration before reciprocal callbacks),
`sync_known` (call the real node method), and `isolation` (diagnostic paths/modules).
`decode` additionally exposes the implementation-decoded atom to compare opaque
`x`, `refs`, and `ext`; the harness never parses `x` as JSON.

`adapter_common.py` supplies RPC plumbing and deterministic Ed25519 keys/signing.
Canonical bytes, record framing, validation, and node behavior come from each
implementation's own APIs. It does not translate peer wire protocols or normalize
HTTP rejection responses. All peer traffic is actual HTTP over `127.0.0.1`.
`driver.py` owns process cleanup, bounded RPC waits, HTTP calls, and a restartable
TCP proxy that captures request/response bytes for cursor evidence.

Seeds, atom timestamps, and payload bytes are fixed. Ports and node epochs are
runtime identities, recorded only where needed for transport evidence. Reports
identify both source trees by per-file SHA-256. Convergence uses two clean-room
nodes and one reference with overlapping subscriptions, seeded entirely within
the common subscribed region. Proxy catch-up is checked with both implementations
as initiator: the resumed PULL reuses `after=3` and transfers exactly two new atoms.

## Result and retained divergences

Clean-room tests: **34 passed**. Interop matrix: **14 rows, 0 failures**.
Both implementations agree on canonical bytes and signatures, validation states,
XY_Z lower-edge scopes, exact decimal boundaries, and the full 13-vector freeze
corpus. The new spatial codec is independently structured but was implemented in
a shared session; the provenance record states the limits of that independence.
Scope shape: `{"xy_lo":null,"xy_hi":null,"z_min":null,"z_max":null}`.
Z bounds are canonical decimal strings; equal padded XY keys reject with HTTP 400.

The retained non-normative divergences are duplicate HTTP-envelope keys, unknown
PULL query members, and empty PUSH batches. Error wording is implementation-defined.
Equal/reversed bounds and declared-address mismatch now agree as required by #17.
See the regenerated matrix and the current correction in the proof report.

How the implementation was kept clean-room, and what is verifiable versus procedural about that claim, is recorded in [docs/CLEANROOM_PROVENANCE.md](docs/CLEANROOM_PROVENANCE.md).
