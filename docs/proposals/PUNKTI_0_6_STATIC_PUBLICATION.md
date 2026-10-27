# Punkti 0.6 — Static Publication Architecture

**Status:** Founder-accepted architecture; final normative bytes/vectors pending CEO-OS #21.  
**Baseline branch:** `draft/punkti-0.6-static-first`  
**Evidence:** `experimental/punkti-v0.6-static/`

## Decision

Static publication is the normative Punkti 0.6 replication/correctness path.

A conforming implementation must be able to publish Punkti such that another implementation can replicate already-published data through ordinary static HTTP without requiring the publisher daemon to be alive.

Dynamic Mesh features are optional acceleration only.

## Minimal logical model

```text
mutable root
  -> immutable manifest
      -> immutable spatial indexes / replication packs
          -> immutable canonical R objects
```

The exact filesystem names from the experiment are not yet normative. The final spec should freeze logical objects and exact bytes, not incidental path aesthetics.

## Identity

- MID identifies the logical atom.
- SHA256(R) identifies the exact immutable transported record.
- The signature is not part of MID.
- Distinct R variants may share a MID.
- Invalid variants must not poison a valid record.

## Spatial model

`h=<xy>_<z>`

- XY: standard lowercase 2D geohash, 4–12 chars; 10 recommended/default only.
- Z: separate signed exact-decimal WGS84 ellipsoidal metres.
- Negative Z is valid.
- No artificial altitude range.
- No fixed decimal-place cap beyond canonical spelling/total address limits.
- XY prefix locality is usable for static publication/indexing; Z remains independent.

## Publication requirements

- keep mutable state minimal;
- immutable objects are content-addressed and verified by exact-byte digest;
- publish immutable dependencies before advancing the mutable root;
- stale/missing/corrupt objects fail safely and are retryable;
- canonical individual R objects remain addressable;
- immutable replication packs are the preferred bootstrap profile;
- unanchored atoms remain representable;
- a publication never proves global completeness/freshness.

## Optional accelerators

Implementations MAY provide:

- PUSH;
- Range PULL;
- notifications;
- peer/session state;
- dynamic query APIs;
- CDN-specific optimizations.

None are required for correctness.

## Experiment evidence

CEO-OS #20 / PR #116 demonstrated:

- daemon-free replication using `python3 -m http.server`;
- independent reader verification and republishing;
- two-node union convergence;
- three-node partial-overlap convergence;
- hostile/failure handling;
- 38/38 static experiment tests passing.

Request-count measurements favored immutable packs:

- 5k fresh subscriber: 5,005 index-only requests vs 26 pack requests;
- 100k replication: 100,005 index-only requests vs 398 pack requests;
- measured byte overhead for packs was about 1.2%.

Loopback dynamic Mesh was faster in elapsed time in the experiment, so dynamic APIs remain useful acceleration.

## Before freeze

CEO-OS #21 must reduce this architecture to the smallest normative publication contract and deterministic cross-implementation vectors. No production deployment, stable release tag or 0.6 freeze is implied here.
