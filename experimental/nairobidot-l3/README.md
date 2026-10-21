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
Run the entire suite to regenerate the complete eleven-row report.

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

## Result and retained divergence

Clean-room tests: **23 passed**. Interop matrix: **10 PASS, 1 FAIL** across 11 test
methods. The failing rejection row has two assertions describing one divergence:

- A raw `/push` body contains duplicate `records` keys: first an empty list, then
  a list containing a valid record.
- Reference: HTTP **200**, `VALID`, `admitted=true`; the record enters its main store.
- Clean-room: HTTP **400**, `kind=request`, `reason=json`; its main store stays empty.

The test requires rejection and an unchanged store. It remains failing; there is
no expected-failure decorator or softened assertion. Each malformed-request case
uses fresh nodes, so the accepted duplicate-key request cannot contaminate the
noncanonical-base64 or forged-before-valid checks. Those checks pass. Both
implementations also agree on forged/truncated/flipped/trailing records,
unsupported algorithms, and future-version wrappers.

Neither implementation's `src/` nor `docs/` was changed. At task start the
clean-room sources, tests, and project metadata were present but **untracked**,
contrary to the brief's committed-source premise. This harness commit includes
only `interop/` and this README; reproducing it requires those existing clean-room
files with the source hashes recorded in the report. No browser verification is
applicable to this process/HTTP-only experiment.
