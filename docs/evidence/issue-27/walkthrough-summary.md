# Issue 27: independent local GET walkthrough

This evidence was captured from real HTTP GETs against `http://127.0.0.1:38745`.
The fixture uses the existing Publisher and mesh fixture helpers, with four
valid signed atoms: two at `u3butz7k9q_23`, one at `u3bu_23`, and one at
`u3butz7k9q_24` to demonstrate exclusion from the same leaf.
No production endpoint was contacted. The ephemeral server is stopped after
verification; a rerun prints a new port. Its temporary publication is removed
on shutdown. Deterministic fixture atoms yield the same object hashes.

This transcript was regenerated from three real runs for the 2026-10-29
spatial-only correction (CEO-OS Issue #30), replacing the pre-correction run.
Every record requires an explicit canonical `h = <xy>_<z>`; empty, missing,
null or malformed addresses are INVALID-structural. The manifest contains only
geographical depth-2 index keys. No location or altitude is inferred.
The generator omits former fixture ID 3 and preserves IDs 1, 2, 4 and 5,
including their original signed bytes and MIDs.

The contract was checked against Stage A
`47537960166e33ed806a4349b81b6a54c5ab3e00` and Stage B implementation
`dce9f81cf24cc5df1031d284365409d82cfcd862`. This branch keeps its existing
Publisher/carrier dependencies; those anchored paths produce the corrected
fixture without importing Stage B or changing runtime code.

## Four stages

1. **Root:** use the fixture's printed publication base, then GET `root.json`.
   It supplies head `594964638a26a997f8a7d39a2a3cabf5ee2205c79491437b8cfe522d1189387f`.
   The root is mutable: its SHA is reported, not checked against a nonexistent
   upstream digest. The proposed `/nodes.json` bootstrap is documented but not
   exercised here; this fixture starts at a known publication base.
2. **Manifest:** GET `manifests/<head>.json`; all 156 bytes hash exactly to head.
   `index['u3']` supplies the first geographic shard SHA; it is the fixture's
   only index entry. The manifest counts four records.
3. **Geographic walk and exact filter:** start with two-character `u3`, follow
   parent `children` one character at a time to ten-character `u3butz7k9q`.
   Every shard digest matches. The leaf SHA is
   `17d44621212131298b44590b601208f6d7ff5aee16dac8cf4744f1bea8a04cad`.
   Two entries match `h=u3butz7k9q_23`; the `_24` entry is explicitly excluded
   before fetching its record. Thus one exact h contains multiple atoms, while
   sharing a leaf does not make a different height the same conversation.
4. **Records:** GET each matching immutable record by its leaf `sha256`, check
   byte digests, independently decode canonical LENGTH framing and fields, and
   compare the decoded exact h. The transcript prints every URL, byte length,
   SHA, upstream hash source, matching entry, excluded entry and decoded field.
   Binary fields are labelled hex; payload text is escaped JSON and untrusted.

## Padding evidence

For `u3bu_23`, `K(u3bu)=u3bu00000000`; the leaf is `u3bu000000`, not `u3bu`.
The walk shares `u3`, `u3b`, `u3bu` with the first target, then selects `u3bu0`
instead of `u3but`, continuing through padded zero prefixes to length ten.
Its leaf SHA is `6fa6a7f5cb79b9180e6b85f50ffbef3d4d18ca40845e9e560e47167917e7c01c`.
One record matches; the address in the signed record remains `u3bu_23`.

Z is absolute WGS84 ellipsoidal height, not AGL. Padding affects routing
only; it never changes the exact address in a signed record.

## Observed exact paths and hashes

Paths below are relative to the real base above. This table is extracted from
captured GET output, with duplicate fetches consolidated. For immutable objects,
the digest in the path equals the observed SHA-256; the root has no such address.

| Exact path | Bytes | Observed SHA-256 |
|---|---:|---|
| `root.json` | 104 | `91ff48520c1f812a5687e4953628f419ecb53fd40cfa3970f19904ca3f2bf582` |
| `manifests/594964638a26a997f8a7d39a2a3cabf5ee2205c79491437b8cfe522d1189387f.json` | 156 | `594964638a26a997f8a7d39a2a3cabf5ee2205c79491437b8cfe522d1189387f` |
| `h/u/3/a8d99b59c664e44225297969aa545830c8506738f6e42f3a4c66481d078e2d98.json` | 146 | `a8d99b59c664e44225297969aa545830c8506738f6e42f3a4c66481d078e2d98` |
| `h/u/3/b/4bd065e5d6e4e1bf5acc9b2a95fb93a70bb9e39b376116c2e8a8442810ce8e5e.json` | 148 | `4bd065e5d6e4e1bf5acc9b2a95fb93a70bb9e39b376116c2e8a8442810ce8e5e` |
| `h/u/3/b/u/72444597c4659792b3d0516023f222d35deba33f664b327a4e7c7088bc0c92db.json` | 225 | `72444597c4659792b3d0516023f222d35deba33f664b327a4e7c7088bc0c92db` |
| `h/u/3/b/u/t/273be401ca6721d81e11c73f7dbd2ddafdea743a38e3b652aa885e03cd501e88.json` | 152 | `273be401ca6721d81e11c73f7dbd2ddafdea743a38e3b652aa885e03cd501e88` |
| `h/u/3/b/u/t/z/0b1c36d610db69cd52d0b5ffe68928d0c557deebcea170ac90314e4b90c3d5c2.json` | 154 | `0b1c36d610db69cd52d0b5ffe68928d0c557deebcea170ac90314e4b90c3d5c2` |
| `h/u/3/b/u/t/z/7/4d15f6e97f07bc9c2527a4290877be6abda4127cce6ff1edbcc5ac9ad7cf12a0.json` | 156 | `4d15f6e97f07bc9c2527a4290877be6abda4127cce6ff1edbcc5ac9ad7cf12a0` |
| `h/u/3/b/u/t/z/7/k/7d9529ae15d1282e5697ac513dc3f781945b1a8de23360489f780fb7aa3c9154.json` | 158 | `7d9529ae15d1282e5697ac513dc3f781945b1a8de23360489f780fb7aa3c9154` |
| `h/u/3/b/u/t/z/7/k/9/2540f1d40df2bb608765e65809663e127c540d1b18292202b35157514dc099d5.json` | 160 | `2540f1d40df2bb608765e65809663e127c540d1b18292202b35157514dc099d5` |
| `h/u/3/b/u/t/z/7/k/9/q/17d44621212131298b44590b601208f6d7ff5aee16dac8cf4744f1bea8a04cad.json` | 627 | `17d44621212131298b44590b601208f6d7ff5aee16dac8cf4744f1bea8a04cad` |
| `records/95/95302f1de4f761378f45f5691aec2d8e689961b79445bcd2d363159b10782924` | 175 | `95302f1de4f761378f45f5691aec2d8e689961b79445bcd2d363159b10782924` |
| `records/f2/f21d132410fbdaad5cc5edd0988e66db55b89f284b8d2824a29ef8ae8e309d55` | 175 | `f21d132410fbdaad5cc5edd0988e66db55b89f284b8d2824a29ef8ae8e309d55` |
| `h/u/3/b/u/0/b837ded2dd7bb68ed2f0d509293c07c4a68e18f9912d9d76498e1812343e453e.json` | 152 | `b837ded2dd7bb68ed2f0d509293c07c4a68e18f9912d9d76498e1812343e453e` |
| `h/u/3/b/u/0/0/9fb7050a3227c4341a58a2cb463f47227a2b151151223d43a50a476f28f770d5.json` | 154 | `9fb7050a3227c4341a58a2cb463f47227a2b151151223d43a50a476f28f770d5` |
| `h/u/3/b/u/0/0/0/04f4114da1b45d59aef350ed93d1ef45f82e187a7c8c646bd72789435591f675.json` | 156 | `04f4114da1b45d59aef350ed93d1ef45f82e187a7c8c646bd72789435591f675` |
| `h/u/3/b/u/0/0/0/0/1a615a76d78a58246e129e0042516fd972500dc9e1b0932e25d543af5690ac86.json` | 158 | `1a615a76d78a58246e129e0042516fd972500dc9e1b0932e25d543af5690ac86` |
| `h/u/3/b/u/0/0/0/0/0/2a0f13049bd426a1d3ed2958c753f3628d45df5a5062782a01dea6389b00f8fd.json` | 160 | `2a0f13049bd426a1d3ed2958c753f3628d45df5a5062782a01dea6389b00f8fd` |
| `h/u/3/b/u/0/0/0/0/0/0/6fa6a7f5cb79b9180e6b85f50ffbef3d4d18ca40845e9e560e47167917e7c01c.json` | 257 | `6fa6a7f5cb79b9180e6b85f50ffbef3d4d18ca40845e9e560e47167917e7c01c` |
| `records/24/245cad10b9865213922e2821db1f7d63e88961967916b3e7ac010237145d9230` | 169 | `245cad10b9865213922e2821db1f7d63e88961967916b3e7ac010237145d9230` |

## Exact-h results

- `MATCH {"h": "u3butz7k9q_23", "mid": "punkti/0.6:d26e8ae338c1c092119a45327db9fbb09ef39c4cf4ab5a04235eda8488ab95ed", "sha256": "95302f1de4f761378f45f5691aec2d8e689961b79445bcd2d363159b10782924"}`
- `EXCLUDED exact-h mismatch {"h": "u3butz7k9q_24", "mid": "punkti/0.6:ed92a014d8fb61e52a7dbc572a0cf71c58ff88411e9b68da508c76df27fb7787", "sha256": "a90e4bb9ce63efcc6687f3498149c1c2b7c42df586d2be8a6a8fbe25a3db5fb0"}`
- `MATCH {"h": "u3butz7k9q_23", "mid": "punkti/0.6:169af90d1484d5178fc63b7bd5f131d3a6a46b304d5fd196021488c4aaa4b613", "sha256": "f21d132410fbdaad5cc5edd0988e66db55b89f284b8d2824a29ef8ae8e309d55"}`
- `MATCH {"h": "u3bu_23", "mid": "punkti/0.6:c36b39413d02b9888b8a060f8d4c58f78e442b4b84559d467cccd98e6ca45341", "sha256": "245cad10b9865213922e2821db1f7d63e88961967916b3e7ac010237145d9230"}`

## What was and was not verified

The two raw runs verify SHA-256 of every fetched immutable object, canonical
JSON encoding, prefix links along the selected path, structural/canonical record
decoding, and exact h. They do not verify signatures, recompute MID, establish
author identity, or prove global completeness/coverage. Hashes alone cannot
authenticate the mutable root or prove authorship. This demonstration is not a
full publication admission implementation: it has no checkpoint/staleness state
and does not audit every unselected branch.

A third run passes `--verify-with-frozen-carrier`. Only that optional stage
imports the frozen carrier; neither fetching nor independent decoding uses it.
Both selected records report `VALID`, and the carrier's recomputed MID and h
match their leaf entries. This verifies signatures for those keys, not real-world
identity, payload truth, or global completeness. No new cryptography was added.
No pack was required or fetched.

## Exact reproduction commands

Run from the repository root. Start the fixture in one terminal:

```sh
python3 -B docs/evidence/issue-27/tools/make-ai-read-fixture.py
```

Actual startup output:

```text
BASE=http://127.0.0.1:38745
HEAD=594964638a26a997f8a7d39a2a3cabf5ee2205c79491437b8cfe522d1189387f
TARGETS=['u3butz7k9q_23', 'u3bu_23', 'u3butz7k9q_23', 'u3butz7k9q_24']
```

These exact capture commands were run in a second terminal. Substitute the newly
printed base when reproducing; leave the target addresses unchanged.

```sh
python3 -B docs/evidence/issue-27/tools/ai-read-walkthrough.py --base http://127.0.0.1:38745 --h u3butz7k9q_23 > docs/evidence/issue-27/walkthrough-transcript.txt
python3 -B docs/evidence/issue-27/tools/ai-read-walkthrough.py --base http://127.0.0.1:38745 --h u3bu_23 >> docs/evidence/issue-27/walkthrough-transcript.txt
python3 -B docs/evidence/issue-27/tools/ai-read-walkthrough.py --base http://127.0.0.1:38745 --h u3butz7k9q_23 --verify-with-frozen-carrier >> docs/evidence/issue-27/walkthrough-transcript.txt
```

All three exited 0. Their matching-record totals were 2, 1, 2; the final
run reported `FROZEN REFERENCE VERIFIER (not GET path): VALID` twice.
Stop the fixture with Ctrl-C to remove its temporary directory.

[Full unedited captured stdout](walkthrough-transcript.txt) ·
[GET client](tools/ai-read-walkthrough.py) ·
[Fixture builder](tools/make-ai-read-fixture.py) ·
[Proposed READ block](../../AI_READ_BLOCK.md)

## Additional checks

All 38 captured GET responses were compared with the fixture files before
shutdown: every byte length and SHA-256 matched, and all 20 distinct paths
appear in the table above. All four fixture records decoded independently to
the explicit addresses listed in the startup output. The manifest has only
`u3` and `record_count=4`; no removed-key path was generated.
Six invalid spatial inputs (empty, null, missing separator, empty Z, negative
zero and a redundant fractional zero) were rejected by the independent decoder's
spatial validator. These checks are separate from the unedited HTTP transcript.
The fixture server was stopped and its temporary publication directory removed.
