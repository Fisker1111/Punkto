# Benchmark summary

Source data:

- `evidence/bench_static.json`
- `evidence/bench_mesh.json`

## Scope and method

- Loopback-only measurements on one host.
- Host: CPU count `1`, MemTotal KiB `2,009,888`, platform `Linux-7.0.0-38-generic-x86_64-with-glibc2.43`, Python `3.14.7`.
- Host constraints note: this benchmark host has one vCPU and limited RAM; wall-time numbers are comparative only and not directly comparable to typical multi-core developer machines.
- Static serving uses the stdlib HTTP server from `src/staticpub/httpsource.py`.
- Warm page-cache effects are expected; numbers are comparative, not absolute latency claims.
- Profile: `bounded` with repeats=3.

## Leaf-depth sweep

| Depth | Request score | Wall score (s) |
|---:|---:|---:|
| 2 | 1,358 | 13.250 |
| 4 | 1,374 | 12.456 |
| 6 | 1,390 | 14.448 |
| 8 | 1,414 | 13.432 |
| 10 | 5,664 | 18.030 |

Recommended leaf depth: **2**

## Matched static vs Mesh (1000 atoms)

| Scenario | Static A wall (median [min..max]) | Static A requests (median [min..max]) | Static B wall (median [min..max]) | Static B requests (median [min..max]) | Mesh wall (median [min..max]) | Mesh pull requests (median [min..max]) |
|---|---:|---:|---:|---:|---:|---:|
| fresh_subscriber_allspace | 4.517 [4.283..5.454] | 1,005 [1,005..1,005] | 4.119 [3.926..4.164] | 11 [11..11] | 0.836 [0.621..0.847] | 32 [32..32] |
| overlap_100 | 1.696 [1.671..1.836] | 1,005 [1,005..1,005] | 0.525 [0.522..0.529] | 11 [11..11] | 0.758 [0.628..0.981] | 32 [32..32] |
| overlap_0 | 4.731 [4.703..7.752] | 1,005 [1,005..1,005] | 4.182 [3.634..5.108] | 11 [11..11] | 0.708 [0.680..0.736] | 32 [32..32] |
| xy_prefix_subscription | 2.295 [2.256..2.404] | 337 [337..337] | 1.310 [1.178..1.355] | 5 [5..5] | 0.299 [0.251..0.323] | 11 [11..11] |
| broad_allspace_subscription | 5.327 [5.274..5.582] | 1,005 [1,005..1,005] | 3.659 [3.541..3.810] | 11 [11..11] | 0.736 [0.690..0.756] | 32 [32..32] |
| incremental_one_new_atom | 0.540 [0.531..0.554] | 4 [4..4] | 0.534 [0.501..0.574] | 5 [5..5] | 0.005 [0.004..0.009] | 1 [1..1] |

## Matched static vs Mesh (5000 atoms)

| Scenario | Static A wall (median [min..max]) | Static A requests (median [min..max]) | Static B wall (median [min..max]) | Static B requests (median [min..max]) | Mesh wall (median [min..max]) | Mesh pull requests (median [min..max]) |
|---|---:|---:|---:|---:|---:|---:|
| fresh_subscriber_allspace | 24.785 [22.913..29.665] | 5,005 [5,005..5,005] | 21.255 [19.469..22.474] | 26 [26..26] | 4.935 [4.838..5.026] | 157 [157..157] |
| overlap_100 | 9.149 [8.667..10.223] | 5,005 [5,005..5,005] | 2.798 [2.564..2.923] | 26 [26..26] | 5.372 [4.676..5.543] | 157 [157..157] |
| overlap_0 | 23.661 [23.196..25.006] | 5,005 [5,005..5,005] | 19.178 [18.372..21.195] | 26 [26..26] | 4.942 [4.731..7.134] | 157 [157..157] |
| xy_prefix_subscription | 7.494 [7.297..8.840] | 1,670 [1,670..1,670] | 5.966 [5.768..6.147] | 10 [10..10] | 2.427 [2.397..2.842] | 53 [53..53] |
| broad_allspace_subscription | 27.410 [26.167..43.408] | 5,005 [5,005..5,005] | 19.198 [17.308..21.910] | 26 [26..26] | 5.566 [4.782..5.661] | 157 [157..157] |
| incremental_one_new_atom | 3.212 [2.936..3.480] | 4 [4..4] | 2.700 [2.697..2.776] | 6 [6..6] | 0.005 [0.004..0.006] | 1 [1..1] |

## Storage amplification + rebuild (1,000 atoms)

| Mode | Publication bytes | Raw bytes | Amplification | Rebuild wall (s) |
|---|---:|---:|---:|---:|
| A | 365,619 | 183,429 | 1.993 | 0.864 |
| B | 553,537 | 183,429 | 3.018 | 0.390 |

## 100k scale run (fresh subscriber only)

| Mode | Publish wall (s) | Publish CPU (s) | Replication requests | Replication bytes | Replication wall (s) | Completed | Reason |
|---|---:|---:|---:|---:|---:|---|---|
| A | 402.939 | 129.992 | 100,005 | 36,886,475 | 681.524 | completed |  |
| B | 425.057 | 138.665 | 398 | 37,318,700 | 454.033 | completed |  |

Scale step completed: `True` (elapsed 2837.912s, budget 3,300s).

## Concurrency (shared publication, 1,000 atoms)

| Mode | Readers | Aggregate requests (median [min..max]) | Aggregate bytes (median [min..max]) | Wall (s) median [min..max] | Origin req (median [min..max]) |
|---|---:|---:|---:|---:|---:|
| A | 1 | 1,005 [1,005..1,005] | 365,619 [365,619..365,619] | 5.997 [5.530..7.528] | 1,005 [1,005..1,005] |
| A | 8 | 8,040 [8,040..8,040] | 2,924,952 [2,924,952..2,924,952] | 31.271 [30.861..33.318] | 8,040 [8,040..8,040] |
| B | 1 | 11 [11..11] | 370,108 [370,108..370,108] | 4.151 [3.706..4.473] | 11 [11..11] |
| B | 8 | 88 [88..88] | 2,960,864 [2,960,864..2,960,864] | 19.600 [19.244..19.867] | 88 [88..88] |

