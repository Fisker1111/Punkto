# Clean-room provenance

This file records how the `nairobidot` implementation was produced, what is verifiable
from the repository, and what is only procedural.

## Procedure actually used

1. A fresh, empty git repository was created outside the Punkto working tree, containing
   exactly two files under `docs/`: `PUNKTI_0_6_LAYER3_RESET.md` and
   `PUNKTI_0_6_MESH.md`, copied byte-for-byte from branch `proposal/punkti-0.6-mesh`
   @ `6a2c9a6`.
2. A short `BRIEF.md` was written stating the deliverable (module layout, envelope rules,
   transport operations, test obligations) and the explicit constraint: the only normative
   inputs are those two documents plus the brief; no other Punkti implementation exists on
   the machine and none may be read, imported or copied; every unstated detail must be
   recorded in `AMBIGUITIES.md` rather than invented silently.
3. An implementing agent was run inside that isolated repository with the instruction not
   to read anything outside it. It produced `src/nairobidot/`, `tests/` (23 tests, all
   passing), `tests/vectors.json`, and `AMBIGUITIES.md` (18 recorded interpretations).
   The isolated repository's history is two commits: the documents/brief, then the
   implementation.
4. The resulting `src/` and `tests/` trees were copied into this repository **unmodified**.
   The copy was verified byte-identical (`diff -r`) against the isolated tree before commit.
5. Separately and afterwards, a black-box interoperability harness was built. Only the
   harness — never the implementation — was written with knowledge of how the reference
   node is started and configured over HTTP. The harness drives the reference as a
   process-isolated peer; it does not translate wire formats and does not normalise
   responses between implementations.

## What a reviewer can verify from this repository

- `../interop/test_interop.py::test_no_reference_imports` scans every file under
  `../src/nairobidot/` for reference imports and for any mention of the reference tree, and
  asserts the package imports in an isolated interpreter (`-I`, only
  `experimental/nairobidot-l3/src` on `sys.path`) with no `carrier`, `mesh` or `spatial`
  module loaded.
- `../interop/test_interop.py` asserts, for every adapter process, that its `sys.path` contains
  only its own implementation tree and that the clean-room process has loaded no reference
  module.
- `../interop/interop_report.json` records a per-file SHA-256 manifest of both source trees,
  so every conformance claim in `PROOF_REPORT.md` is pinned to exact bytes.
- Reading `../src/nairobidot/` shows no Punkto, relay, PWA, BRTH, identity, news or
  application-schema concept: the only inputs are the envelope fields, the canonical byte
  procedure, spatial addresses, opaque bytes, and the four HTTP operations.

## What is only procedural (not independently verifiable here)

- That the implementing agent never read the reference source. The isolation was enforced
  by directory contents and instruction, not by a sandbox audit log; the isolated
  repository's history is evidence of the two-step process but is not published here.
- That the brief itself introduced no reference-implementation detail. The brief is a
  restatement of the two documents plus delivery logistics (module names, test list); a
  reviewer can check this claim against `PROOF_REPORT.md` and `AMBIGUITIES.md`,
  which quote the document sentences each interpretation resolves.

The strongest available substitute for the unverifiable part is the outcome: an
independent implementation, written without sight of the reference code, reproduced every
canonical byte and every qualifying validation state exactly, and diverged only on HTTP
request-validation rules the specification does not state (see `PROOF_REPORT.md` §5).
A copy-based reimplementation would not be expected to diverge at all.
