# Punkto discovery index — PROTOTYPE ONLY

An isolated Layer-4 static GeoHash density index over an already-published
Punkti 0.6 tree. **The discovery index is not verified content.** The frozen
Layer-3 publication, its object shapes, and its bytes are unchanged. This is
an experiment, not a production design commitment or deployment.

A fresh GET-only client follows:
`nodes.json → node.index → occupied 2/6/10-character prefixes → exact h → records`.
It can discover populated regions without knowing a manifest, an exact place,
or a height. Golden Gate's approximate coordinate selects region `9q8zhu`;
this is prefix discovery, not geocoding or a unique landmark lookup.

## Run from the repository root

Python standard library and existing repository dependencies only. No install,
npm, bundler, mandatory JavaScript, or new dependencies.

```bash
python3 -c "import cryptography, yaml"
export PYTHONPATH=experimental/punktto-discovery-index/src:.
(cd experimental/punktto-discovery-index && PYTHONPATH=../.. python3 -m unittest discover -s tests -p 'test_*.py' -t .)
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
python3 -m discovery.generator /path/to/publication
python3 -m discovery.metrics
```

The generator defaults to `<publication>/discovery/index.json` and
`<publication>/discovery/d/<sha>.json`. An optional `--output` must name a
direct child directory of the publication: the specified `../records/...`
links depend on that layout. It never writes a frozen publication object.
Dynamic path components cannot contain traversal, controls, empty segments,
absolute paths, or invalid digests/prefixes. The sole fixed parent hop is the
schema's prescribed `../records/<sha[:2]>/<sha>`, confined to the publication.

To try a complete isolated fixture on loopback:

```bash
export PYTHONPATH=experimental/punktto-discovery-index/src:.
python3 - <<'PY'
from pathlib import Path
from punkti_node.publication import Publisher
from discovery.generator import generate
from discovery.metrics import fixture_records, bootstrap

directory = Path('/tmp/punktto-discovery-demo')
Publisher(directory / 'publication').publish(fixture_records())
generate(directory / 'publication')
bootstrap(directory, 'http://127.0.0.1:8088')
PY
python3 -m http.server 8088 --bind 127.0.0.1 --directory /tmp/punktto-discovery-demo
```

In another shell, from the repository root:

```bash
export PYTHONPATH=experimental/punktto-discovery-index/src:.
python3 -m discovery.client http://127.0.0.1:8088
python3 -m discovery.client http://127.0.0.1:8088 --prefix 9q8zhu
python3 -m discovery.client http://127.0.0.1:8088 --exact-h 9q8zhuwqcp_0 --cross-check
```

The optional node config field is
`bootstrap.nodes[].index: http://127.0.0.1:8088/publication/discovery/index.json`.
It uses the same URL validation as existing node URLs. Omission leaves the
bootstrap response unchanged; its version remains `punkti/bootstrap/1`.
No running node configuration is changed by this prototype.

## Integrity and snapshots

Generation reuses frozen root/manifest/shard validators and verifies source
object hashes. Counts distinguish record variants from distinct exact addresses.
Short XY spellings remain exact in entries while indexing under padded-10
leaves. Every entry requires a canonical anchored `h = <xy>_<z>`; an
unrestricted scope selects all anchored records through the same XY tree.
The derived format is now `punkti/discovery/0.2`: the former unanchored root
member and empty-prefix terminal are rejected. Older derived indexes trigger
the GET-only publication fallback and can be regenerated.

The synthetic fixture signs fresh records at explicitly chosen addresses,
including `0000_0` (the all-zero geohash cell, not a default location or height).
Historical signed fixtures are not rewritten; Stage B preserves them separately
under `legacy-unanchored/` archives. Only derived objects and measurements are
regenerated here.

All children are fsynced before an atomic same-directory root replacement.
The source root is reread before exposure; a changed head aborts. An interrupted
refresh leaves the previous root intact (or no root on a first run). Immutable
orphan files may remain after failure and old snapshots remain on refresh.
This is a single-writer prototype; it does not lock an independently running
publisher across the final root comparison and replacement.

The client verifies canonical discovery objects, child hashes, snapshot bindings,
counts, and raw record hashes. It explicitly reports stale indexes by comparing
the current publication root. Missing index/child/terminal, corrupt objects, or
inconsistent metadata trigger frozen root → manifest → shards → records fallback.
If the frozen source is also corrupt or unavailable, the read fails.

Hash integrity is **not cryptographic authorship**. The optional `--cross-check`
uses the authoritative `punkti_node.publication.Reader`, requires its head/seq
to match the discovery snapshot, compares selected record bytes and metadata,
and separately reports signature/MID verification. Unsupported algorithms remain
unverified candidates. A stale index can still navigate immutable bytes, but
cross-checking against a newer current publication fails explicitly. Neither
mode claims global completeness or trust in a bootstrap provider.

## Measurements

Generated by `python3 -m discovery.metrics` (the durable 10,000-cell corpus can
take many minutes on a slow filesystem); machine-readable evidence is
[evidence/metrics.json](evidence/metrics.json). Each scenario uses a fresh client
against a real stdlib HTTP server. Counts include bootstrap and record GETs;
discovery also includes its freshness root GET. Bytes are uncompressed response
bodies, excluding headers. Optional authorship cross-check traffic is excluded
from both paths. The known-place scenario fetches the three atoms at
`9q8zhuwqcp_0`; the unknown visitor fetches all seven atoms across five exact
anchored addresses, including `0000_0`. No cached results or packs are used.

The seven-atom fixture produces **13 files / 6,479 bytes**.

| Scenario | Path | GETs | Body bytes | Records |
|---|---|---:|---:|---:|
| unknown | discovery | 22 | 8,038 | 7 |
| unknown | frozen | 46 | 8,410 | 7 |
| known | discovery | 9 | 3,773 | 3 |
| known | frozen | 15 | 3,275 | 3 |

| Synthetic atoms / distinct cells | Discovery files | Total bytes |
|---:|---:|---:|
| 10 | 31 | 14,012 |
| 100 | 301 | 138,574 |
| 1,000 | 2,381 | 1,160,976 |
| 10,000 | 20,956 | 10,587,214 |

Discovery reduces fixture requests from 46 to 22 (unknown) and 15 to 9
(known). Body bytes decrease from 8,410 to 8,038 for the unknown visitor
and increase from 3,275 to 3,773 for the known place. These are corpus-specific tradeoffs.

File totals below measure only actual generated discovery files in fresh
directories, not the underlying frozen publication or filesystem block overhead.
The synthetic corpus spreads one atom per distinct XY cell deterministically.
Refreshes retain previous immutable files; long-running retention would increase
these totals. This prototype does not implement garbage collection.

The results measure this corpus and these traversal policies, not a general
performance claim. A client stopping at region descriptors would fetch fewer
records; a broad discovery traversal may spend more bytes on descriptors even
when it reduces requests. Sparse cells still cost roughly two derived objects
per atom plus shared depth-2 branches: tiny-file growth remains material.

## Tests and boundaries

Tests exercise every level's counts, exact heights and short XY, the all-zero
geohash cell and empty regions, independent GeoHash encoding and reference vectors, real GET-only
reads, frozen-reader verification, legacy bootstrap compatibility, deterministic
regeneration, stale snapshots, head-change failure, interrupted writes, atomic
ordering, malicious paths, missing/corrupt objects, and measured corpus growth.

No PWA code, publication schemas, relay, deployment, DNS, or production state is
changed. Manual browser acceptance is not applicable to this HTTP-only prototype.
The short proposed READ introduction is in
[docs/DISCOVERY_AI_READ.md](../../docs/DISCOVERY_AI_READ.md).
