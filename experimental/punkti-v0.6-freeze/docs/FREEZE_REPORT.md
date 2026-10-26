# Punkti 0.6 XY_Z correction — Founder review

Status: **implemented candidate; no freeze, merge, tag, PR or deployment authorization.**
Base: `c835eb417190cf22d1e55a22eb9fd8d7c2efa340`.
Branch: `fix/punkti-0.6-xy-z-spatial`. The final exact SHA is in the handoff.
The prior #17 report remains available in the base commit's version of this file.

## Changes

The normative [XY_Z profile](../../../docs/proposals/PUNKTI_0_6_SPATIAL_XY_Z.md)
replaces the provisional interleaved 3D profile only for Punkti 0.6. Both Python
implementations validate `<xy>_<z>` in signed carriers. XY is standard 2D geohash,
4–12 characters, default 10; Z is canonical ASCII decimal WGS84 ellipsoidal metres,
compared exactly. The entire h is at most 32 characters. Empty h stays unanchored.

Both node implementations already delegate scope construction, serialization,
filtering and binding hashes to their spatial modules. Those modules now use
xy_lo/xy_hi and canonical string z_min/z_max; no node transport refactor was needed.
Selection and bound rejection use the same padded K keys. The resolved coarse/fine
rule is implemented as written, including HTTP 400 for [u3b,u3b0).

The PWA receives a pure standalone ES module and Node test. It is not wired into
the frozen create flow. Python uses Decimal; JS compares scaled BigInts. Float
client formatting first rounds the exact binary value to millimetres, ties to even,
then strips trailing zeros. String input must already be canonical.

Clean-room source remains free of reference imports and runtime reads. The same
agent wrote both replacements in one shared session, using separate implementations;
this is not a fresh sight-unseen implementation. See the honest
[CLEANROOM_PROVENANCE.md](../../nairobidot-l3/docs/CLEANROOM_PROVENANCE.md) update.

## Actual acceptance results

| Suite | Base count | XY_Z count | Result |
|---|---:|---:|---|
| Reference unittest | 32 | 37 | PASS |
| Clean-room unittest | 28 | 34 | PASS |
| Black-box interop | 13 | 14 | PASS |
| Hostile network | 125 | 144 | PASS |
| Freeze vectors | 11 | 14 | PASS |

The PWA XY_Z test passes 219 assertions, including byte-equivalent XY encoding,
identical decoded bounds/centres and float formatting in JS and both Python trees.
Ten JS files pass individual node --check (the new codec plus all nine existing
files listed in the task). Four module-mode syntax checks pass (codec, app, map,
board). The unchanged slice5 helper suite passes. git diff --check passes.

All 13 deterministic vectors pass on both isolated implementations (26 executions,
13 output comparisons), plus the explicit inventory test. Two consecutive
regenerations of vectors.json and NORMATIVE_VECTORS.md are byte-identical.
Clean-room pinned vectors regenerate identically as well.

No manual browser verification was performed: the codec has no DOM or shipped-flow
integration. Real HTTP, fault injection, admission, pagination and interop are
covered by the automated loopback suites. The full scale matrix, container, WAN and relay suites
were not rerun; relay is outside the authorized change scope.

## Vector coverage and retained #17 semantics

V1–V10 retain their original non-spatial assertions: canonical framing, initial
MID cursor, rejection tiers, descriptor atomicity, signature failures, timestamp
grammar, interrupted-page checkpoint safety, opaque preservation and HELLO limits.
V4 now pins separate XY and Z boundaries; spatial fixture bytes and scope bindings
are deliberately regenerated. V5's empty-PUSH observation stays non-normative.

V11 covers same-XY/different-Z C/MID/address, negative and fractional heights,
all required invalid spellings/lengths/separators, and pairwise exact Z ordering,
including adjacent 27-digit integers that binary doubles cannot distinguish.
V12 covers all 24 encode/decode ground-truth cases. Its bounds use an independent
integer-grid oracle. V13 covers prefix ranges, unanchored records, exact half-open
Z bounds, both coarse/fine counterexamples, equal padded-key HTTP rejection and
malformed string/numeric bounds. Existing node tests retain union/empty-list rules.
The interop suite also executes V11–V13 against both processes.

## Before/after signed-content scope

All seven pre-existing freeze fixtures contained nonempty spatial h. All seven
therefore change C, S, MID, address and R. The six Ed25519 signatures change;
the unsupported-algorithm fixture retains its opaque signature bytes. Every
other atom field is unchanged. This is a signed-content correction, not a framing/domain change.

| Fixture | Before h → after h | Before MID | After MID |
|---|---|---|---|
| canonical | `s00000000000` → `s00000000000_23` | `0224ff9b877ba0e74c7f103a7f32108e0393ea67a97abce136238c4d313dd895` | `82444945204576099501248b1a615c1c841b44981ae8e8bd1f89eb4e093f73ba` |
| opaque | `s00000000000` → `s00000000000_23` | `ad5bef0800968201b6044d27f28b275698b83cc2feab453e147d940e100f350f` | `8b6dca8bc139ff96f5b7e6c8841e88f6f5b5e50c45fc9e31e53be68e74c00969` |
| spatial0 | `000000000000` → `000000000000_-18` | `b8da0a3c616083fada8f7b5cc5c90faba1e2d1ba6719e96a05979a5d8ebee00e` | `b794c104861488e804b57a559bf62987731e79580267c007afe01568ff3233d6` |
| spatial1 | `s00000000000` → `s00000000000_23` | `efa769042ad022b66eaca4aa5cceae58d420f8baf546e7cadd2806fd2e749eaa` | `64787c65702b2091e07fca6d588dcccda806654248d9f62978af640994ad5342` |
| spatial2 | `s00000000001` → `s00000000001_23.025` | `f001cfc4becb89f3228bb414b3fb540e14ce41bcc1aa7653e8aa41268745e8d7` | `40d073c1656d7025c2342d2904800fa0ac2699254016277a61fd5432c8af5479` |
| spatial3 | `zzzzzzzzzzzz` → `zzzzzzzzzzzz_9000` | `f851c2c52242a4272f8ad0e21d71961bc9f34e82d198457dd75ea4c6fc75bfac` | `d71670ee11209e93d50c73b645714a57cea67a511c232ffb7d88f9ce80f96025` |
| zero | `s00000000000` → `s00000000000_23` | `42adf91cf60d1b538b2d060075ca993f8077afb57067cfea5d0494fde652c28e` | `16c16c69428c89562f5eef5f5d1c1986585356292889cc5350ae5ebecc682608` |

The clean-room pinned set retains the unanchored fixture byte-for-byte, including
C/S/MID/address/R/signature, and regenerates only its two spatial fixtures. The
interop unanchored fixture likewise retains its MID. New historical and selection
fixtures supplement the old freeze fixtures. Scope bindings and cursor tokens
change because the serialized keys change from h_lo/h_hi to xy_lo/xy_hi.

The protected-path comparison against the exact base is empty for `core/`,
`relay/`, `pwa/geohash3d.js`, `pwa/app.js`, and `pwa/core/location.js`. All existing
PWA files are untouched; only the new codec and its test are added. The frozen
v0.5.1 paragraph in the reset specification is byte-identical to the base.

## Remaining choices recorded in profile §10

1. Lower-edge containment is the resolved selection rule; region overlap is rejected.
2. Z precision is bounded by length (27), with no fixed decimal-place cap.
3. Z wire bounds are canonical strings to preserve exact boundaries.
4. Scope keys are xy_lo/xy_hi, deliberately changing scope hashes.
5. Published XY allows 4–12, recommends 10; a future precision-10-only restriction is undecided.
6. The whole address is limited to 32 characters, constraining XY and Z together.
7. Shipped PWA integration remains a separate authorized task; this delivery is standalone.

The prior non-normative HTTP differences remain: duplicate envelope keys, unknown
query members, empty PUSH arrays, and implementation-defined error wording. No
new normative divergence is claimed. Location remains a signed claim, not proof
of presence; x stays opaque. No static-tree transport is implemented.

## Reproduction

Use the commands in the task and each experimental README. Run the vector generator
before the freeze/interop suites, which consume the committed artifacts. Full
interop and hostile runs regenerate their reports. Protocol and network evidence
in this correction comes from the XY_Z suites; old scale/container measurements
remain historical and are not represented as newly verified.

## Regenerated evidence and changed files

Actual machine-readable acceptance counts, durations, artifact hashes and exclusions
are recorded in [xy_z_verification.json](../../punkti-v0.6-hostile/evidence/xy_z_verification.json).
The hostile protocol corpus contains 354 observations. Counts by implementation:

```json
{
  "nb": {
    "AGREE": 177
  },
  "ref": {
    "AGREE": 177
  }
}
```

Files changed relative to the exact base (the two supplied root task/profile files
remain untracked inputs):

```text
docs/proposals/PUNKTI_0_6_LAYER3_RESET.md
docs/proposals/PUNKTI_0_6_MESH.md
docs/proposals/PUNKTI_0_6_SPATIAL_XY_Z.md
experimental/nairobidot-l3/README.md
experimental/nairobidot-l3/docs/AMBIGUITIES.md
experimental/nairobidot-l3/docs/CLEANROOM_PROVENANCE.md
experimental/nairobidot-l3/docs/PROOF_REPORT.md
experimental/nairobidot-l3/interop/adapter_common.py
experimental/nairobidot-l3/interop/interop_matrix.md
experimental/nairobidot-l3/interop/interop_report.json
experimental/nairobidot-l3/interop/nb_adapter.py
experimental/nairobidot-l3/interop/ref_adapter.py
experimental/nairobidot-l3/interop/test_interop.py
experimental/nairobidot-l3/src/nairobidot/carrier.py
experimental/nairobidot-l3/src/nairobidot/spatial.py
experimental/nairobidot-l3/tests/test_carrier.py
experimental/nairobidot-l3/tests/test_node.py
experimental/nairobidot-l3/tests/test_revision.py
experimental/nairobidot-l3/tests/test_spatial.py
experimental/nairobidot-l3/tests/vectors.json
experimental/nairobidot-l3/tests/vectors.py
experimental/punkti-v0.6-freeze/README.md
experimental/punkti-v0.6-freeze/docs/FREEZE_REPORT.md
experimental/punkti-v0.6-freeze/docs/NORMATIVE_VECTORS.md
experimental/punkti-v0.6-freeze/src/make_vectors.py
experimental/punkti-v0.6-freeze/src/vector_suite.py
experimental/punkti-v0.6-freeze/tests/test_vectors.py
experimental/punkti-v0.6-freeze/vectors.json
experimental/punkti-v0.6-hostile/README.md
experimental/punkti-v0.6-hostile/docs/FINDINGS.md
experimental/punkti-v0.6-hostile/docs/HOSTILE_NETWORK_REPORT.md
experimental/punkti-v0.6-hostile/evidence/cross_impl_network.json
experimental/punkti-v0.6-hostile/evidence/network.json
experimental/punkti-v0.6-hostile/evidence/protocol.json
experimental/punkti-v0.6-hostile/evidence/xy_z_verification.json
experimental/punkti-v0.6-hostile/src/hostile/cases_protocol.py
experimental/punkti-v0.6-hostile/src/hostile/harness.py
experimental/punkti-v0.6-hostile/src/hostile/measure_scale.py
experimental/punkti-v0.6-hostile/tests/test_coverage_eclipse.py
experimental/punkti-v0.6-hostile/tests/test_cursor_spatial.py
experimental/punkti-v0.6-hostile/tests/test_replay_provenance.py
experimental/punkti-v0.6-hostile/tests/test_scale_envelope.py
experimental/punkti-v0.6-mesh/README.md
experimental/punkti-v0.6-mesh/src/carrier.py
experimental/punkti-v0.6-mesh/src/spatial.py
experimental/punkti-v0.6-mesh/tests/support.py
experimental/punkti-v0.6-mesh/tests/test_carrier.py
experimental/punkti-v0.6-mesh/tests/test_mesh.py
experimental/punkti-v0.6-mesh/tests/test_store.py
experimental/punkti-v0.6-mesh/tests/test_xy_z.py
pwa/spatial-xy-z.js
pwa/test-spatial-xy-z.mjs
```
