# Mesh convergence measurement — executed on a live loopback HTTP host

Date: 2026-10-20 (re-run after the initial sandbox-blocked attempt; the reference
implementer's sandbox forbade loopback sockets, so the final authoritative run was
performed directly against the implementation on the un-sandboxed host).

## Summary verdict

**PUSH + HTTP Range PULL is sufficient for the task's required convergence
scenarios. No transport-independent missing-set reconciliation is added.** Three
independently-initialized nodes with different subsets converge on the union of
valid atoms in a single scheduled exchange round at every tested size (12, 96, 384).
Inserts behind an active MID cursor are the one case where a single page is not
enough — a fresh null-cursor sweep is required — exactly as the L3 reset's
"concurrent insertions behind a cursor" caveat predicts. A spatial high-water
resume `SUBSCRIBE ... FROM <cursor>` catches the missed records directly. Nothing
measured justifies a fifth missing-set mechanism; it would add complexity without
closing any observed gap.

## Reproduce

From the repository root, with Python 3.10+ and `cryptography` installed:

```sh
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests -v
python3 experimental/punkti-v0.6-mesh/tests/measure.py
```

The measurement runner uses three independently initialized stores, fixed key
seeds, fixed store epochs, separate real loopback HTTP servers and the standard
library `urllib`. It emits JSON only after every scenario completes and its set
assertions pass. It does not mock HTTP, skip socket failures or estimate observed
counts.

## Measured results

### Differing subsets — all converge in 1 round

Each scheduled round connects A↔B, B↔C, C↔A (6 directions: local + reciprocal PUSH,
local + reciprocal Range PULL per connect).

| Scenario | Initial A/B/C | Union | Rounds to converge | PUSH req/records | PULL req/records |
|---|--:|--:|--:|--:|--:|
| Small | 6 / 5 / 4 | 12 | 1 | 60 / 60 | 6 / 66 |
| Medium | 48 / 40 / 32 | 96 | 1 | 480 / 480 | 18 / 528 |
| Larger | 192 / 160 / 128 | 384 | 1 | 1920 / 1920 | 66 / 2112 |

After one round the valid-atom set is identical (size = union) on all three nodes.

### Churn behind a MID cursor (the one multi-sweep case)

| Metric | Value |
|---|--:|
| Initial atoms on A | 480 |
| Inserted behind the first MID page | 32 |
| First MID sweep count | 480 |
| Total MID sweeps | 2 |
| Fresh-sweep records | 512 |
| Spatial high-water resume records | 32 |
| Final count (union) | 512 |

A single active MID sweep's `ceiling` correctly excludes the concurrent inserts,
so the first sweep sees 480; a fresh null-cursor sweep reaches all 512. The spatial
high-water resume delivers exactly the 32 later records. Both behaviours are
deliberate L3 semantics, not a reconciliation gap.

## Reconciliation decision

Convergence across differing subsets at 12/96/384 atoms completes in one round
with only PUSH + HTTP Range PULL. The churn case is closed by a fresh MID sweep or
spatial `FROM <cursor>` resume within the existing two mechanisms. Therefore the
transport-independent missing-set reconciliation mechanism is **not justified by
measurement** and is omitted. The spec documents the omission and the exact
conditions under which a future measurement-based revisit would be warranted
(larger scale, adversarial withholding, partial retention, permanent partitions).

## Notes

- Counts (requests/records) rather than wall-clock time are the deterministic
  metric; ports are OS-assigned.
- Convergence here is multi-message eventual convergence, not a network-wide
  atomic transaction, even though one scheduled round suffices.
- This verifies the loopback-wire path of the reference implementation; it is not
  a claim of global completeness under hostile topology, which remains the Punkti
  Internet Red Team scope.