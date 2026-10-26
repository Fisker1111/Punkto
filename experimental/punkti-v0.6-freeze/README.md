# Punkti 0.6 freeze-candidate vectors

Thirteen deterministic, publishable vectors for Founder review. This experiment does
not freeze or release the protocol. `docs/NORMATIVE_VECTORS.md` contains exact
inputs, canonical fixture bytes, expected results and state transitions;
`vectors.json` is the machine-readable artifact.

From the repository root:

```sh
python3 experimental/punkti-v0.6-freeze/src/make_vectors.py
PYTHONPATH="$PWD/experimental/punkti-v0.6-freeze/src" python3 -m unittest discover -s experimental/punkti-v0.6-freeze/tests
```

Generation first independently mints every fixture with ref and nb, checks all
canonical fields, then verifies all thirteen vectors on both implementations before
writing either artifact. Repeated generation is byte-for-byte deterministic.
Tests read the committed artifact without regenerating expectations. The fourteen
unittest methods cover thirteen vectors × two implementations plus inventory coverage;
each vector also compares normative outputs across implementations. Empty PUSH
in V5 is recorded separately and excluded from normative pass/fail totals.

The harness imports neither implementation. It reuses `Adapter`, `http` and
`HERE` from `experimental/nairobidot-l3/interop/driver.py` via sys.path insertion.
Each implementation runs in its own isolated subprocess and serves actual
loopback HTTP. V8 uses a controlled standard-library HTTP peer, including an
incomplete response with an oversized Content-Length. No new dependencies.
The additive adapter commands are `import_json` (exact JSON bytes) and
`pull_from` (one catch-up pass using each implementation's own checkpoint).
These expose only ok/error. The new `spatial` RPC delegates pure codec operations
to each implementation and returns their values; it does not implement the codec.

Runtime epochs are checked against HELLO, never pinned or compared between nodes.
No WAN, deployment, production storage or manual browser testing is implied.
See `docs/FREEZE_REPORT.md` for review scope, limitations and complete suite counts.

V11 pins historical XY_Z addresses, canonical grammar and exact total Z order.
V12 pins all eight geohash rows at three precisions, including decoded bounds and
centres. V13 pins lower-edge containment, the coarse/fine counterexample, exact
Z boundaries, unanchored selection, and HTTP 400 for equal padded XY keys.
