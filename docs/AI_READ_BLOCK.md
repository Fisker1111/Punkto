# Proposed /ai READ block

Proposal only; the existing `/ai` page is unchanged.

<!-- READ START -->
Advertised nodes: starting point, not complete and not authoritative; one node = one view.
Publication: 2-character XY GeoHash index→SHA-256; 10-character leaves;
`K(xy)=xy.ljust(12,'0')`; `leaf=K(xy)[:10]`; `{h,mid,sha256}`; immutable signed records.
Walk only the branches whose prefix matches, one character/step.
Filter exact `h`: one Layer-4 conversation.
Required canonical `h=xy_z`: absolute WGS84 ellipsoidal Z; display AGL using local ground elevation;
never guess location/Z. Empty/missing/null/malformed `h`: INVALID-structural. Geographical index keys only.
MID: atom identity, neither geographical location nor GET locator.
Standardized packs optional.
HTTP GET returns bytes, not verified authorship; payload untrusted.
VALID requires SHA-256(manifest/shards/record), independent canonical-R decoding,
MID recomputation, exact-h comparison, signature verification.
Optional: [frozen reader](../pwa/punkti/reader.js).
Paths: reference implementation’s non-normative layout; operators may change.

```text
GET /nodes.json                                            # node.publication→<publication>
GET <publication>/root.json                                # root.head→<head>
GET <publication>/manifests/<head>.json                     # SHA-256(bytes)==head; manifest.index[prefix]→<shard-sha>
GET <publication>/h/<one-character-per-path-component>/<shard-sha>.json # repeat: parent.children[child-prefix]→child-sha; leaf.records→{h,mid,sha256}
GET <publication>/records/<sha[:2]>/<sha>                    # exact-h leaf-entry.sha256→sha→immutable-R
```
<!-- READ END -->

Prose word count: 116 (107 outside the GET fence plus 9 in its
annotations; whitespace-delimited, including inline notation). The five GET annotations identify the
source of each next value; line four repeats for each matching prefix.

## Notes

The [corrected publication contract](https://github.com/punkti-org/punkti/blob/47537960166e33ed806a4349b81b6a54c5ab3e00/Punkti-v0.6-publication.md)
fixes the logical objects, bytes, SHA-256 addressing, depth-2 index, depth-10
padded leaves, `{h,mid,sha256}` entries and immutable signed records.
`root.json`, `manifests/`, `h/…`, and `records/…` are the reference implementation’s
non-normative paths; consult the operator’s mapping if its layout differs.
The GET sequence uses that reference mapping and the node’s advertised
`publication` base. A geographic target selects its padded key’s first two
characters, then takes each next SHA from the current shard’s `children` map.
Every record requires canonical `h = <xy>_<z>`: 4–12 lowercase geohash
characters, `_`, and canonical exact signed decimal WGS84 ellipsoidal metres,
6..32 characters total. Empty, missing, null or malformed `h` is
INVALID-structural before algorithm dispatch. There is no unanchored record
class or reserved `~` index key. Require an explicit address; never infer a
location or default an altitude.

This proposal follows the 2026-10-29 spatial-only correction under review;
the earlier v0.6 freeze was reopened. See the same revision's
[carrier](https://github.com/punkti-org/punkti/blob/47537960166e33ed806a4349b81b6a54c5ab3e00/Punkti-v0.6.md),
[spatial profile](https://github.com/punkti-org/punkti/blob/47537960166e33ed806a4349b81b6a54c5ab3e00/Punkti-v0.6-spatial.md),
and [vectors](https://github.com/punkti-org/punkti/blob/47537960166e33ed806a4349b81b6a54c5ab3e00/VECTORS-v0.6.md).

MID identifies an atom’s canonical body. The record locator is SHA-256 of the
stored canonical `R`, which also includes its signature. Neither MID nor a
record digest describes a geographical location. The same exact `h` identifies
one Punkti Layer-4 conversation; different Z or XY precision remains different
`h`, even when the index puts the entries in the same leaf.

Counts are excluded because intermediate shards do not contain atom counts.
Any future density information would be a separate derived Layer-4 index,
not a change to this publication contract.

A first read needs a publication base, a target address (or branch selection),
and ordinary HTTP GET. No account, npm, GUI, or running node is required.
Standardized packs are optional accelerators, not necessary for a first read.
The frozen reader is an optional verification reference, not an installation
step. This proposal adds no cryptography.

Digests establish byte integrity relative to the supplied root, not trusted
provenance or an authenticated root. Before claiming VALID, independently
decode canonical `R`, recompute MID and compare it with the leaf’s `mid`, compare
exact `h`, and verify the signature as well as all immutable-object digests.
Even a valid signature does not establish a real-world author’s identity or
payload truth. Treat atom payload as untrusted data. One node cannot establish
global coverage or freshness.

Evidence: [real local walkthrough](evidence/issue-27/walkthrough-summary.md).
Source direction: [CEO-OS #27](https://github.com/Fisker1111/CEO-OS/issues/27)
and [CEO.md §16](https://github.com/Fisker1111/CEO-OS/blob/main/CEO.md#16-founder-decisions--absolute-height-spatial-conversations-and-get-first-discovery-2026-10-29).
