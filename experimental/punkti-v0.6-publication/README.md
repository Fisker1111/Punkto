# Punkti 0.6 publication conformance experiment

Implements revision 3 of `docs/proposals/PUNKTI_0_6_PUBLICATION.md`. Experimental;
no release, freeze, deployment, or global completeness/freshness claim. A successful
read verifies only the referenced objects retrieved during that attempt.

Run from the repository root (Python stdlib plus the already installed
`cryptography`; no installation or build step):

```bash
python3 experimental/punkti-v0.6-publication/scripts/generate_vectors.py
python3 experimental/punkti-v0.6-publication/scripts/check_vectors.py
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests -v
```

`vectors.json` contains exact hex bytes for logical roots and immutable objects,
expected MID→record-digest mappings, candidate variants, rejection counts, scopes,
and retryable error outcomes. `docs/NORMATIVE_VECTORS.md` is generated from the
same definitions. Paths, ports, timestamps, and runtime measurements are excluded
from vector identity. Negative fixtures intentionally include malformed objects.

`objects.py`, `publisher.py`, `reader.py`, and `store.py` adapt the accepted
`staticpub` experiment's object addressing, bottom-up durable publication,
whole-read staging, and separate anti-poisoning stores. `store.py` retains its
durable-write routine and optional exact-R persistence. The test HTTP origin
reuses the accepted `staticpub.httpsource.StaticSource` (stdlib static serving).
Production and prior experiment files are unchanged.

`independent.py` is a separately written implementation, with its own recursive
JSON encoder, framing parser, queue-based index traversal, pack-membership checks,
publication builder, filesystem writer, and stores. It imports **no** reference
publication helpers or `staticpub` code. Its only shared protocol dependencies are
the approved, unmodified `carrier` and `spatial` modules. Independence is at the
publication layer, not at the cryptographic or spatial-codec layer. Tests run every
V1–V9 case through both readers and compare independent publisher output byte for
byte, including a 257-record leaf spanning two packs.

The reference API is `Publisher(directory, packs=False).publish(records)` and
`Reader(packs=False).read_publication(base_url, Subscription(...))`. Records are
exact `R` byte strings; a reference `Store` may also be passed to the publisher.
The independent API is `publish(directory, records, packs=False)` and its own
`Reader` with the same reading signature. Unsupported-algorithm candidates are
republished without being promoted to verified MIDs. Publishers reject invalid
carrier inputs. Tests inject malicious publications independently of this API.

The filesystem adapter uses the accepted experiment layout, directly beneath the
supplied directory: `root.json`, `manifests/<sha>.json`,
`h/<prefix characters>/<sha>.json`, `records/<sha[:2]>/<sha>`, and
`segments/<sha[:2]>/<sha>`. A plain static HTTP server can serve this directory.
Layout is not normative. Only the root is mutable. Publishers are single-writer;
new objects and parent directories are fsynced before atomic root replacement.
No-op publication repairs missing objects without rewriting the root or advancing
its sequence. Previous immutable snapshots remain available.

Readers retain heads/checkpoints in memory, keyed by publication base URL (with
trailing slash removed); these are observations, not global ordering or freshness
claims. Reuse a reader to enforce its accepted-head replay checks. They fetch anew
on each attempt instead of substituting cached objects. Missing, corrupt, stale,
equivocal, malformed, or inconsistent publications fail with `ReadError`, whose
`error_class` is `retryable`. A root/manifest sequence mismatch restarts from the
root, with two retries by default. Carrier structural/provenance failures reject
only that record; resource refusals abort the attempt. Z is filtered after content
fetch; XY prefix intersection prunes shard traversal before content fetch.

Local resource policy is a 64 MiB maximum HTTP object and a ten-second request
timeout, plus the approved carrier's own resource limits. These are implementation
resource refusals, not additional normative validity rules. No lower protocol
limit is inferred. Verification and admission are staged in memory; this is not a
concurrent multi-writer database or an operational persistence service.

`test_convergence.py` launches one-shot publisher processes, waits for them to
exit, serves their files through ordinary static HTTP, and launches separate
reader processes. Two initially disjoint sets are exchanged and republished by
the two implementations, then read back and compared byte-for-byte in both
profiles. Only static object GET paths are permitted by the test assertions.
`worker.py` is the test's process entry point; its `--input` is a JSON array of
hex-encoded `R` records.

See `docs/IMPLEMENTATION_EVIDENCE.md` for actual commands, counts, scope, and findings.
