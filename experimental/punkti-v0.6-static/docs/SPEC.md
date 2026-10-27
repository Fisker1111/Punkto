# Punkti 0.6 — static publication + read-only replication (experimental profile)

Status: **experiment / not frozen / not normative.** This document fixes the
experiment's shape so the reference implementation and the clean-room reader
cannot silently diverge. Nothing here changes atom C/S/MID/R, the approved
carrier, or the XY_Z spatial profile.

Source: CEO-OS Issue #20. Baseline carrier/spatial code is the accepted
`experimental/punkti-v0.6-mesh/src/{carrier,spatial}.py` as of branch
`fix/punkti-0.6-xy-z-spatial` (commit `1fd7858`).

## 0. First principle

> Nodes write/validate Punkti. Ordinary HTTP serves Punkti. Other nodes
> replicate Punkti by reading what a publication serves.

Consequences that MUST hold in the prototype and MUST be provable by tests:

- ordinary reads are satisfiable from static files;
- replication correctness does not require a live Punkti daemon at the serving
  side (a dumb static HTTP server must suffice);
- no peer session, no reciprocal callback, no dynamic query API is required
  for replication;
- optional announcements are accelerators only; correctness survives their
  total loss.

## 1. Terminology

- **Publication** — a directory tree served over plain static HTTP.
- **Root** — the mutable discovery pointer of a publication.
- **Manifest** — an immutable, content-addressed description of one published
  state of a publication.
- **Shard** — an immutable, content-addressed index node of the XY hierarchy.
- **Record object** — the exact immutable bytes `R` of one atom, addressed by
  `SHA256(R)`.
- **Pack** — an immutable, content-addressed segment bundling many records
  (optional accelerator; canonical record objects remain available).
- **MID** — the namespace-qualified logical address of an atom. Signature is
  excluded from MID.

## 2. Directory profile (proposed minimal static publication profile)

```
<pubroot>/punkti/
  root.json                              # tiny mutable discovery pointer
  manifests/<sha256>.json                # immutable publication manifest
  h/<xy0>/<xy1>/.../<sha256>.json        # immutable XY hierarchy shard
  records/<sha256[0:2]>/<sha256>         # exact immutable R bytes
  segments/<sha256[0:2]>/<sha256>       # optional immutable replication packs
```

The XY characters form the **directory** path of a shard; the **file name** is
the content address of the shard bytes. A shard version is therefore never
overwritten: a changed shard is a NEW file with a NEW digest, and the pointer
to it lives in the parent shard/manifest, which is itself immutable.

Rules:

1. Every object under `manifests/`, `h/`, `records/`, `segments/` is
   **content-addressed**: the file name is the lowercase hex `SHA256` of the
   file's exact bytes (shard and manifest files carry a `.json` suffix that is
   decoration only — the digest is over the file bytes), and a reader MUST
   reject an object whose bytes do not hash to its name.
2. `root.json` is the ONLY freely mutable file. It is small and points at the
   current manifest:
   `{"v":"punkti/pub/0.6-draft","seq":<int>,"head":"<manifest-sha256>","updated_at":"<rfc3339>"}`.
   `seq` is a monotone publication counter of that publication (not an atom
   ordering and not a global clock).
3. A manifest is immutable and contains:
   `{"v":..., "seq":<int>, "prev":"<manifest-sha256>|null", "created_at":"<rfc3339>", "depth":2, "index":{"<xy-prefix>":"<shard-sha256>"}, "record_count":<int>, "pack_count":<int>}`.
   `depth` is the length of the XY prefix keys listed in `index` (fixed at 2
   in this experiment; see §5).
4. A shard (`h/<xy chars>/<sha256>.json`) is immutable and contains:
   `{"v":..., "prefix":"<xy>", "children":{"<xy prefix>":"<shard-sha256>"}, "records":[{"mid":"<MID>","sha256":"<sha256>","h":"<xy_z or empty>"}], "packs":["<pack-sha256>", ...]}`.
   Shard path directories are the geohash characters of the prefix, so the
   tree depth equals the prefix length; the file name is the shard's own
   content address. A shard whose content changes is published as a NEW file
   (new digest); the previous version stays published so the previous
   manifest remains fully readable.
5. A record object is the exact bytes `R` of the atom carrier record (the same
   bytes the accepted Mesh stores and transmits). `SHA256(R)` is its name.
   `R` is never rewritten, re-encoded, or re-indented.
6. A pack is a byte string:
   `b"PUNKTIPACK1" + u32count + (u32len + bytes)*count`, where each entry is
   one exact `R`. A pack additionally carries, outside this framing, no
   metadata: the reader hashes each `R` and validates it, so packs need no
   per-entry digest. Pack names are content addresses too.

### 2.1 Mutability, ordering, recovery

- Canonical record `R` is immutable.
- Publish order MUST be: (a) write + fsync record objects and packs, (b) write
  + fsync new/changed shards, (c) write + fsync the new manifest, (d) atomically
  replace `root.json` (write temp file in the same directory, `fsync`, then
  `os.replace`). A reader must therefore never see a head that references an
  object that is not durably present.
- An interrupted publication MUST recover deterministically: the previous
  `root.json` still points at the previous, fully valid manifest; the next
  publish run recomputes the desired state from the durable store and rewrites
  the missing objects (content addressing makes this idempotent).
- Publication MUST be deterministic: publishing the same store twice yields
  byte-identical objects.

### 2.2 Identity rules

- Logical identity = namespace-qualified MID.
- Physical variants of the same MID are distinguished by `SHA256(R)`. Signatures
  are excluded from MID, so two different `R` may carry the same MID. An invalid
  variant MUST NOT poison the valid variant of that MID.
- The reader MUST verify `SHA256(R)` and MUST re-validate the record
  structurally/cryptographically via the accepted carrier validator before
  admitting it. No malformed or corrupt object may enter the valid store.
- `x` (Layer-4 payload) MUST NOT be reinterpreted, and the spatial address `h`
  MUST NOT be altered to suit the filesystem layout.

## 3. XY_Z projection (unchanged semantics)

- `h = <xy>_<z>`; `xy` = standard 2D geohash, canonical address precision
  4–12, precision 10 recommended/default; `z` = exact signed decimal WGS84
  ellipsoidal metres.
- Z is an exact signed decimal of unbounded *magnitude* — there is no
    artificial numeric ceiling, negatives are valid, and there is no fixed
    decimal-place cap. The canonical *textual* encoding of the address is
    nevertheless bounded by the APPROVED codec (`spatial.parse_h` /
    `spatial.parse_z`): the whole address `h` is at most 32 characters and the
    `z` component at most 27 characters (so with canonical precision 10 and the
    `_` separator, `z` is at most 21 characters). These are the accepted
    Issue #19 codec limits and MUST NOT be changed, widened or bypassed by this
    experiment. The tension between "unbounded Z" prose and the codec's
    character limits is a FINDING to report to the Founder, not something this
    experiment may silently resolve by editing the codec.
- unanchored `h=""` is supported (and is outside every anchored XY range).
- The static tree exploits **XY prefix locality only**: objects are filed
  under the geohash characters of `xy`. The canonical address is unchanged and
  MUST NOT depend on the filesystem layout.
- Subscriptions are the accepted lower-edge model: `xy_lo`/`xy_hi` compare
  12-character zero-padded keys; `z_min`/`z_max` compare exact decimals.
- A subscription with `h=""` (unanchored) is outside every anchored XY range.

## 4. Replication protocol (read-only, GET/HEAD only)

The replicator MUST use only static GET/HEAD semantics against the
publication. It MUST NOT require any endpoint other than plain file objects.

Reader algorithm (`read_publication`):

1. `GET /punkti/root.json` → parse; on failure the publication is
   unavailable (do not fall back to stale cached state silently unless a
   cached head is explicitly configured).
2. `GET /punkti/manifests/<head>.json` → verify `SHA256(bytes) == head`.
   Manifests are verified by content address, that is the sole integrity
   guarantee of the head pointer.
3. For each manifest index prefix that intersects the requested XY range:
   `GET /punkti/h/<prefix>/<shard-sha256>.json` → verify digest; walk
   `children` descending only into prefixes that still intersect the
   requested range. A range query on a prefix MUST request the minimal set of
   shard objects.
4. Shard `records` entries give `(mid, sha256, h)`. Two fetch modes:
   - **index-only (mode A)**: `GET /punkti/records/<sha[0:2]>/<sha>` per record.
   - **pack (mode B)**: `GET /punkti/segments/<sha[0:2]>/<sha>` for the packs
     covering the range and extract the needed `R` from the pack framing.
     Canonical record objects remain published in both modes.
5. Every fetched `R` is verified (`SHA256`), decoded and validated by the
   accepted carrier validator, and mapped to its MID.
6. Admission, dedup:
   - valid record → valid store keyed by MID (duplicate MID = idempotent no-op);
   - unverifiable-but-structurally-intact variant → separate candidate store
     keyed by `SHA256(R)` (must not displace or poison a valid MID);
   - structurally invalid / provenance-invalid / digest mismatch / truncated /
     corrupt → rejected, never stored in the valid store.
7. A replicator MAY filter by Z locally after fetching (Z is not part of the
   index key), but MUST be able to filter by XY prefix before fetching index
   shards.

Node-to-node behaviour required by the experiment:

- Node A publishes; Node B reads A's static publication and independently
  validates every imported record; B republishes the accepted records in B's
  own publication; A and B can each read the other's publication.
- Duplicates are harmless; divergent sets converge to the union under
  compatible coverage/retention and eventual access.
- No global completeness/freshness claim is made.
- Withholding by a source is detectable only by comparing with other
  publications.

## 5. Hierarchy depth

`manifest.index` maps a **depth-2 XY prefix** (first two geohash characters) to
a shard digest. Shard `children` map the next characters. Shards stop at depth
10 (canonical precision); a shard at depth 10 lists records directly.

Consequences: the manifest is bounded (≤1024 prefix entries — the geohash
alphabet has 32 symbols), a range query starts from the depth-2 prefixes
intersecting the range, and each level costs one request per visited shard. A depth-10 leaf holding N records is one
request; an XY-prefix-limited replication that resolves to a handful of leaves
costs O(visited shards) index requests plus the record/pack fetches.

## 6. Publication determinism and content addressing

The publisher MUST produce the same bytes for the same logical content
(canonical JSON: sorted keys, no insignificant whitespace, UTF-8, no NaN).
Consequently `root.json` may only change when the published state changes.

## 7. Dynamic ingest (allowed, small)

The prototype MAY retain a tiny dynamic ingest path:
`POST /submit → validate → dedupe → persist → update/rebuild publication`.
If implemented, it MUST be a separate process/daemon from the static serving
path, and the static serving path MUST NOT require it. The static files MUST be
fully sufficient for replication.

## 8. Trust boundary

- No node-reputation semantics in L3. Atom validity remains independently
  verifiable; node/service trust is client/operator policy; semantic trust
  stays Layer 4.
- Signing a publication/root MAY be prototyped but MUST NOT be a prerequisite
  for reading or verifying atoms.

## 9. Hostile requirements

Testing MUST cover: truncation; stale head; missing segment/object; corrupt
static object; mismatched digest; replay/duplicate; reordered publication
visibility; selective withholding; long offline/rejoin. No malformed or
corrupt object may enter the valid store, and a missing referenced object MUST
NOT produce a false checkpoint/admission.

## 10. Non-goals

No production deployment; no main merge; no release/tag; no 0.6 freeze; no
Layer-4/Punkto feature work; no BRTH changes; no node marketplace/reputation;
no mandatory CDN/object-store vendor; no rewrite of frozen v0.5.1; no change to
atom C/S/MID/R to suit the static tree.
