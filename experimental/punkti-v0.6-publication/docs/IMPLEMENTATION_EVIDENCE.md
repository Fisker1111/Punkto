# Revision 2 publication contract blocker

Implementation stopped under the task's instruction to “STOP and report the
specific counterexample” when a new byte-framing inconsistency surfaced during
testing. The normative contract has not been modified.

Revision 2 resolves the previously reported prefix-interval and collective
pack-membership blockers. Neither is being reported again.

## New counterexample: pack magic length (§6)

Section 6 specifies:

```text
pack := "PUNKTIPACK1"            (10 ASCII bytes, no terminator)
      || u32be(entry_count)
      || entry_count × ( u32be(len(R)) || R )
```

The specified literal `PUNKTIPACK1` is **11 ASCII bytes**, not 10:

```text
P U N K T I P A C K 1
1 2 3 4 5 6 7 8 9 10 11
```

Its exact hex encoding is `50554e4b54495041434b31`. Consequently no byte string
can satisfy both the exact literal and its stated 10-byte length.

For any one-entry pack following the literal, the count begins at offset 11
and is `00 00 00 01`. A reader following the specified 10-byte header length
instead reads offsets 10–13, `31 00 00 00`, as count **822083584**. Conversely,
a publisher using only ten bytes of the literal emits `PUNKTIPACK` and fails
the specified magic comparison. This counterexample applies regardless of the
record's contents, including every valid canonical carrier `R`.

The accepted experiment uses `len(MAGIC)` for parsing and therefore follows
the 11-byte literal. That is evidence of the existing implementation's choice,
not authorization to silently choose between conflicting contract requirements.
The spec author must resolve the literal/length discrepancy.

## Reproduction

Command run from the repository root (exit 0):

```bash
python3 - <<'PY'
import struct
magic = b'PUNKTIPACK1'
record = b'R'
raw = magic + struct.pack('>I', 1) + struct.pack('>I', len(record)) + record
print('magic =', repr(magic))
print('magic length =', len(magic))
print('magic hex =', magic.hex())
print('literal framing hex =', raw.hex())
print('count at offset 10 =', struct.unpack('>I', raw[10:14])[0])
print('count at offset 11 =', struct.unpack('>I', raw[11:15])[0])
assert len(magic) == 11
assert struct.unpack('>I', raw[10:14])[0] == 822083584
assert struct.unpack('>I', raw[11:15])[0] == 1
print('Counterexample confirmed')
PY
```

The single byte `R` is a framing demonstration only, not a claimed valid atom;
none of the assertions depends on it or on carrier validation.

Actual output:

```text
magic = b'PUNKTIPACK1'
magic length = 11
magic hex = 50554e4b54495041434b31
literal framing hex = 50554e4b54495041434b31000000010000000152
count at offset 10 = 822083584
count at offset 11 = 1
Counterexample confirmed
```

## Implementation and verification status

A preliminary implementation and vector suite were written before discovering
this inconsistency. The required discovery command was run:

```bash
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests -v
```

It reported `Ran 11 tests`, `FAILED (failures=6, errors=24)` (subtest failures
and errors). Pack readers following the documented 10-byte length rejected
packs emitted with the exact literal. This triggered the required stop; these
results are not a conformance pass. The incomplete, uncommitted implementation
and generated artifacts were removed rather than delivered as conforming work.
Only this evidence document is changed.

Acceptance criteria remain unmet. No successful full hostile suite, artifact
regeneration acceptance check, or separate-process static-only convergence
result is claimed. Manual browser verification is not applicable to this
experiment. No contract, approved codec, accepted experiment, production code,
or server state was changed. No push, PR, tag, deployment or merge was performed.
