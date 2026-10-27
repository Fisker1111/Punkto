# Publication contract blockers

Implementation stopped before writing code, as required by `CODEX_TASK.md`:
“STOP and report the specific counterexample”. The normative contract is
unchanged. This report does not choose replacement rules.

## 1. Empty XY prefix intervals (§4.1 and §8 step 3)

Section 4.1 defines `K(xy) = xy.ljust(12, "0")`. Section 8 step 3
defines prefix interval endpoints as `K(p).ljust(12,"0")` and
`K(p).ljust(12,"z")`. Since `K(p)` already has length 12, both
endpoints are identical for every publication prefix. Every interval is empty.

For example, prefix `u4` yields `[u40000000000, u40000000000)`.
An anchored record at `u4_0`, indexed under `u400000000`, lies in the
requested scope `[K("u4"), K("u5"))`, but the prescribed prefix interval
cannot overlap that scope. Literal implementation would exclude every XY
subtree from every spatially constrained read, defeating the required XY
selection behaviour and V6. The spec author must resolve the interval rule.

## 2. Pack membership for leaves larger than 256 records (§6)

Section 6 requires splitting the sorted leaf records into consecutive groups
of at most 256. It also requires that “a pack's extracted set MUST equal
exactly the leaf's record set”. A leaf with 257 distinct record objects
requires groups of 256 and 1. Neither pack equals the 257-record leaf set.
No pack encoding can satisfy both rules. Section 8 step 5 describes equality
for the extracted set of the leaf's packs collectively, which does not remove
the contradictory per-pack requirement in §6. There is no normative leaf
record-count limit that excludes this case, including for the `~` leaf.

## Reproduction

Command run from the repository root (exit 0):

```bash
python3 - <<'PY'
p = 'u4'
k = lambda xy: xy.ljust(12, '0')
lo, hi = k(p).ljust(12, '0'), k(p).ljust(12, 'z')
print(f'prefix={p}; lower={lo}; upper={hi}; empty={lo == hi}')
records = list(range(257))
groups = [records[i:i+256] for i in range(0, len(records), 256)]
print(f'leaf_records={len(records)}; pack_sizes={[len(g) for g in groups]}')
print(f'each_pack_equals_leaf={[set(g) == set(records) for g in groups]}')
assert lo == hi
assert all(set(g) != set(records) for g in groups)
print('2 counterexample checks passed')
PY
```

Actual output:

```text
prefix=u4; lower=u40000000000; upper=u40000000000; empty=True
leaf_records=257; pack_sizes=[256, 1]
each_pack_equals_leaf=[False, False]
2 counterexample checks passed
```

## Delivery status

Only this evidence document was added. No publication implementation or vectors
were created, and no normative rules were silently changed. Acceptance criteria
remain unmet pending resolution by the spec author. The conformance/hostile
suite, vector regeneration, static HTTP convergence and manual browser checks
were not run: implementation stopped at contract review. The two checks above
demonstrate the blockers; they are not conformance tests.
