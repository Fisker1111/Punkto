# Issue #18: six required coverages

The ten published vectors V1–V10 remain unchanged. Issue #18's six required
coverage areas map to the exact machine-readable `expected` values in
[`vectors.json`](../vectors.json); `tests/test_vectors.py` runs them against both
independent implementations and compares their normative results.

| Required coverage | Published vectors | Exact acceptance/rejection oracle |
|---|---|---|
| 1. Canonical record, MID, signature | V1 | Pinned C, R, MID, signature and address; VALID; HTTP 200; admissions `[true,false]`, duplicate reason `duplicate`; trailing framing rejected as INVALID-structural. |
| 2. Initial cursor and first pull | V2 | HTTP 200; empty records `[]`, end `true`, MID after `null`, spatial after `0`; first two addresses pinned in `page_addresses`, MID tokens contain `[address,sha256_R]`. |
| 3. Equal/reversed range rejection | V3 | Statuses `[400,400,400,400,400,400,200,200,200]`; state unchanged. |
| 4. Spatial XY and exact Z boundaries | V4 | HTTP 200; exact four address lists pinned in `addresses`, including empty result below the lower altitude and inclusion at the lower bound. |
| 5. Malformed, tampered, digest/address mismatch | V5 + V6 | V5: four HTTP 400 responses with no admission. V6: HTTP 200 with VALID/true, INVALID-provenance/false, then INVALID-structural/false; exactly the canonical valid address remains. |
| 6. Interrupted/corrupt page and cursor atomicity | V8 | Both failure modes: outcomes `[false,true,true]`, cursors `[null,null,token]` with exact token pinned; one final valid address and log count 1. |

V5's empty PUSH batch is explicitly non-normative and is excluded from normative
equality. V7, V9 and V10 retain additional timestamp, opaque payload and hello
coverage. No coverage gap required adding or renumbering vectors.

## Baseline byte preservation

`tests/test_baseline_bytes.py` pins `golden_base.json`, captured from hardening
baseline `aea705e`, rather than comparing two freshly generated fixture sets.
It uses `vector_suite.spec()` inputs and independently invokes each current carrier
in a subprocess. Three fixtures cover canonical, zero timestamp and opaque L4.
The assertions cover C, full R framing, SHA-256(R), MID/address, signature,
validation state, UTF-8 payload bytes and decoded extension bytes.

The supplied baseline's future-signature fixture has an Ed25519-generated opaque
signature over that future-algorithm body. The published V9 mint adapter instead
uses 64 zero bytes for an unknown algorithm. The regression test deliberately
reproduces the baseline convention without changing V9 or the adapters; both
records remain UNVERIFIABLE-alg. The NFD `e` + combining acute is preserved.
