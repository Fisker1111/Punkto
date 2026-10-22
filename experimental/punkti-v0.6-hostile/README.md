# Hostile-network Mesh experiment

A test harness for the reference and NairobiDot clean-room Punkti 0.6 Mesh
implementations. It starts isolated adapter subprocesses and injects faults through
real loopback TCP/HTTP proxies. Neither implementation is imported into the test
runner. Deterministic signed fixtures are compared using implementation-owned
stores, hashes, candidate stores and append logs.

This proves only the assertions exercised against these two implementations.
It does not prove production networking, authentication, Internet resilience,
durable storage, arbitrary topology convergence or compatibility with other
implementations. All traffic is loopback; no deployment is involved.
**Nothing here is frozen.**

## Run

From the repository root, with Python 3.12+, cryptography, and loopback sockets
available (no extra harness dependencies):

```sh
PYTHONPATH="$PWD/experimental/punkti-v0.6-hostile/src" python3 -m unittest discover -s experimental/punkti-v0.6-hostile/tests -v
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests -v
PYTHONPATH="$PWD/experimental/nairobidot-l3/src" python3 -m unittest discover -s experimental/nairobidot-l3/tests -v
python3 -m unittest discover -s experimental/nairobidot-l3/interop -v
```

The hostile suite has 125 test methods in six modules:

- `test_network_hostile.py` / `test_cross_impl_network.py`: ten real-HTTP fault
  scenarios, each also run with both implementations as initiator.
- `test_envelope_adversarial.py`: 79 envelope/framing cases per implementation.
- `test_replay_provenance.py`: provenance, replay, unknown algorithm and opaque
  version cases.
- `test_cursor_spatial.py`: cursor, ordering, XY+Z and overlapping-scope cases.
- `test_coverage_eclipse.py`: hello capabilities, stale coverage, withholding and
  discovery/eclipse manipulation.

The partition test executes its body three times with fresh runners and requires
identical status, admitted addresses and store sizes. Each adversarial case is
recorded in `evidence/protocol.json` and classified AGREE / DIVERGE / DEFECT for
both implementations; divergences are pinned by tests and explained in FINDINGS.
Baselines contain 27 reference, 23 clean-room and 13 interop tests.
Interop regenerates its own report; restore incidental report changes before
committing this experiment.

Scale measurement (real loopback HTTP, no reconciliation protocol):

```sh
python3 experimental/punkti-v0.6-hostile/src/hostile/measure_scale.py
```

It rewrites `evidence/scale.json` and `docs/SCALE_MEASUREMENT.md`.

## Layout and faults

- src/hostile/faultproxy.py: bounded wire capture and request fault plans.
- src/hostile/harness.py: process lifecycle, deterministic fixtures, store checks,
  evidence serialization; reuses the existing interop adapter plumbing.
- src/hostile/cases_network.py: shared scenario assertions.
- tests/test_network_hostile.py: ten scenarios and partition determinism guard.
- tests/test_cross_impl_network.py: twenty bidirectional scenario tests.
- docs/FINDINGS.md: results, assumptions and proposed specification clarifications.
- evidence/network.json and evidence/cross_impl_network.json: committed evidence
  regenerated on each full run, including diagnostics on scenario failure.
- evidence/verification.json: exact counts and durations for both verification
  runs, plus partition determinism outcomes from each run.

Faults include partitions, drops before forwarding and after admission,
duplicated requests, reversed PUSH batch/order, delayed responses, stalls,
slow-drip delivery, truncated pages and single-byte corrupt JSON responses.
Scenarios also kill/restart real peer processes, exercise stale epochs and
saved cursors, and verify recovery after first-page and later-page interruptions.

Evidence records status, admitted addresses, store/candidate sizes, retries,
errors, healing rounds and exact timeout error shapes for both implementations.
Each proxy captures original/forwarded bytes (base64 in JSON), byte counts,
fault counters and elapsed time. Captures are bounded to 4 MiB per exchange and
4096 exchanges per proxy. Request/byte totals cover instrumented links and both
TCP legs, excluding direct callback/control HTTP; they are not network-wide
totals. Runtime ports, epochs, timing, error strings and request counts may vary.
Only semantic outcomes are compared for determinism.
