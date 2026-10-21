# Clean-room interpretations

Only BRIEF.md, PUNKTI_0_6_LAYER3_RESET.md and PUNKTI_0_6_MESH.md
were used as protocol inputs. The brief authorizes this implementation despite
historical design-only language in the reset. These choices describe an
experimental candidate, not a frozen interoperability claim. References below
are to section names in those two documents.

1. **Negative-zero timestamp spelling.** Reset, Atom envelope: “JSON integer,
   0 through 9007199254740991, Unix milliseconds; fractional/exponent spellings
   rejected.” Possible readings accept JSON `-0` as numeric zero or require the
   minimal unsigned spelling used in C. We reject `-0` on envelope import and in
   C, alongside fractional/exponent forms. Mesh Z bounds still accept negative
   zero as a finite number. A peer accepting `-0` JSON may import a record we
   reject even though its reconstructed C would match positive zero.

2. **Ed25519 malformed-length classification.** Reset, Signature/provenance:
   “`pk` is the raw 32-byte public key and `sig` is the raw 64-byte Ed25519
   signature over `S`”. The text does not assign wrong lengths a specific failure
   tier. We classify wrong known-profile lengths as INVALID-structural; a
   correctly sized signature that fails cryptography's standard Ed25519 verifier
   is INVALID-provenance. A peer could call both provenance failures. Unknown
   algorithms require only nonempty key/signature bytes, never Ed25519 lengths.

3. **Legacy versus future versions.** Mesh, Carrier and admission: “The
   legacy-only UNVERIFIABLE-key state is reserved; no legacy adapter is
   advertised.” Reset's checklist separately requests legacy fixtures. We follow
   the narrower Mesh/brief deliverable: expose all six state identifiers, reserve
   UNVERIFIABLE-key, and reject `punkti/0.5.1` wrappers with
   INVALID-structural / `legacy-adapter-unavailable`. Non-v0.6 JSON envelopes are
   structurally rejected; unsupported namespaces are carried only in explicit
   wrappers. A reset-only peer could offer a legacy adapter and accept them.

4. **Future wrapper addresses.** Mesh, Carrier and admission: “Future namespace
   wrappers use the same item shape”. No separate outer address grammar is
   supplied. We apply the reset reference-target grammar to wrapper addresses,
   including known namespace SHA-256 lengths. Every namespace other than the two
   explicitly known versions is treated as unsupported future/opaque, without
   guessing its format. An interoperating peer could permit arbitrary outer
   address strings or require a version-number pattern; its admission set could
   differ. Transport SHA-256 is exactly 64 lowercase hexadecimal characters.

5. **Axis placement and XY-only fixtures.** Mesh, Subscriptions and cursors:
   “12 base32 characters encode 60 bits, interleaved latitude/longitude/altitude,
   20 bits each, MSB first.” We read that list as the repeating bit order:
   latitude first, longitude second, altitude third, starting at the high bit of
   the first base32 character. Each nonempty h consequently contains altitude;
   no sentinel for absent Z is specified. The brief's “XY-only h” vector means
   an h used with horizontal-only subscription bounds (`s00000000000`), whose Z
   integer is zero. The XY+Z vector changes that integer to one
   (`s00000000001`). A peer using a different bit phase or a missing-altitude
   sentinel would compute different Z selections. No alternate h encoding is
   invented.

6. **Scope omission, normalization and reversed ranges.** Mesh: “An empty scope
   selects all” and “Null is an unbounded endpoint.” Empty could mean `{}` or an
   object containing all four nulls. We accept both, fill omitted recognized
   members with null, reject unknown scope members, and use literal comparisons
   for reversed/equal ranges (empty matching sets). Z values are finite JSON
   numbers, excluding booleans; integer/float representation is retained. A peer
   might reject reversed ranges, reject omitted members, normalize `0.0` to `0`,
   or discard unknown members. This affects request acceptance or token hashes.

7. **Canonical scope-hash JSON.** Mesh: “SHA256 of canonical sorted compact JSON
   containing mode, normalized scope, lo and hi”. No canonical JSON standard is
   named. We use UTF-8 of Python JSON with sorted keys, separators `,` and `:`,
   ASCII escaping, no nonfinite numbers, the exact keys `mode`, `scope`, `lo`,
   `hi`, and normalized scope from item 6. Absent bounds become null. Hash output
   is lowercase hex. Python's finite-number spelling is retained, including
   `-0.0` versus `0.0`. Another canonical numeric format could yield a different
   hash. Tokens are store-local and consumers must echo them without recomputing.

8. **Query defaults and MID bounds in spatial mode.** Mesh supplies a query shape
   and says “MID bounds are optional full namespace-qualified addresses”. It does
   not explicitly assign defaults to every member or prohibit MID bounds in
   spatial mode. We default mode to `spatial`, scope to `{}`, bounds/cursor to
   null and limit to 32, reject unknown query members, and apply supplied MID
   bounds in either mode. Limits must be integers 1–32; above 32 is resource
   refusal. Another peer could require mode/scope or reject combined filters.

9. **MID ceiling representation.** Mesh: “A ceiling excludes concurrent inserts
   from the active sweep.” Its type is unspecified for MID mode. We use the local
   append-sequence high-water integer for both modes, filtering sequence before
   sorting MID records by `(address, digest)`. MID `after` is null initially and a
   two-string JSON array subsequently; an empty page preserves it. A completed
   MID cursor keeps its ceiling indefinitely; a null cursor starts a new sweep.
   Another peer could use a snapshot ID or maximum address pair. Cursors cannot
   be transferred between stores. Spatial tokens use the specified integer
   sequence and refresh ceiling only when incoming after equals ceiling.

10. **Candidate admission flag and capacity policy.** Mesh: “Only VALID enters
    the main store” and “UNVERIFIABLE-alg variants retain exact R in a separate
    digest-keyed candidate store”. It does not define candidate `admitted` or
    eviction policy. We return admitted=true when inserting into either eligible
    store, with the actual local state; duplicates/out-of-scope return false and
    a reason. The 128-candidate budget is shared by unknown algorithms and opaque
    versions; once full, new candidates receive resource refusal, without
    eviction or sequence allocation. Identical R under different unauthenticated
    opaque addresses deduplicates by digest, preserving the first wrapper's
    address. Another peer might report false for quarantined records, evict old
    candidates, or retain multiple wrapper claims per digest.

11. **Verified representatives and sequence allocation.** Reset: “retain a
    verified representative when available” and Mesh: “each unique admitted
    entry gets a monotonic local sequence.” We start sequence at 1, retain the
    first verified R per qualified address, and allocate one sequence per stored
    candidate digest. All new variants are locally verified before duplicate
    checks; rejected/duplicate records get no sequence. A peer retaining several
    valid signature representatives could transfer more R variants at one MID.
    Exact R bytes are preserved for every actual store entry. Imported JSON
    bytes are retained by `import_json`; the Mesh API does not offer JSON export.

12. **Bad request versus per-record rejection.** Mesh: “Bad requests return HTTP
    400; resource refusals return 413 with kind=`resource`” and PUSH returns
    per-record results. We use 400 for invalid HTTP/JSON/request/query/item
    shapes, address syntax and base64 encodings; well-shaped items with digest,
    recomputed-address, inner-R, or provenance failures receive per-record
    INVALID results in HTTP 200. Resource errors propagate as 413 even after
    partial admissions. Unknown wire item metadata, including peer validation
    claims, is ignored. Another peer could return per-record structural errors
    for malformed base64 or abort an entire batch on a bad signature. No client
    checkpoint advances past a resource refusal or invalid returned record.

13. **Response byte budget and local query cap.** Mesh: “Page assembly also caps
    response bytes.” No separate value or accounting convention is supplied.
    We cap serialized JSON responses at the same 8 MiB body budget, reserving
    2048 bytes for the bounded cursor/envelope and adding whole items only;
    PUSH batches are similarly bounded by serialized JSON bytes. A peer with a
    different budget may return fewer records despite the same requested limit.
    This implementation also limits the URL request target to 16 KiB and
    advertises `query_bytes` in /hello. Counts above the published maxima are
    resource refusals, not invalid application data. Standard HTTP framing
    requires one Content-Length and does not support chunked request bodies.

14. **Hello/limits, diagnostics and CLI spelling.** Mesh asks for “protocol …
    store incarnation `epoch`, subscriptions, configured peer origins,
    capabilities, and resource limits” but does not name the other JSON members
    or limit members. We use `protocol`, `epoch`, `subscriptions`, `peers`,
    `capabilities`, `limits`; limits are `canonical_body`, `record`, `references`,
    `relation_bytes`, `http_body`, `page`, `batch`, `candidates`, `query_bytes`.
    Errors use `{kind,reason}` and admission reasons are machine-readable strings.
    Epoch is a fresh UUID hex string per Node construction, preserved on server
    restart. The unspecified CLI/config convention is `--config FILE`, optional
    `--port`, with config keys `subscriptions`, `peers`, optional `port`; the first
    stdout line is `{url,epoch}`. Another implementation may use different
    auxiliary names or epoch types; this does not alter C/S/MID/R.

15. **Origins and callback phases.** Mesh: “Callback origins must already be
    configured locally” and “local PUSH … reciprocal PUSH … local Range PULL;
    reciprocal Range PULL.” We interpret a /sync phase as an instruction for its
    recipient to perform that named action toward the configured caller. Origins
    are explicit `http://127.0.0.1:port`, optionally ending in `/`; credentials,
    query/fragment/path and other hosts are rejected. `connect` requires existing
    local peer configuration too. A peer accepting localhost aliases, other
    interfaces, or dynamically adding callers would have different discovery or
    authorization behavior. Hints never change peer configuration automatically.

16. **Checkpoint granularity and unavailable peers.** Mesh: “PUSH checkpoints
    are keyed by remote origin, incarnation and subscriptions and advance only
    after successful delivery.” We checkpoint PUSH only after the entire bounded
    local snapshot is delivered, so a late error can repeat earlier successful
    batches. PULL checkpoints advance after each complete page. Subscription
    arrays retain order in PUSH checkpoint keys; semantically equivalent
    reordered lists can cause safe retransmission. /sync callback failure is
    502; explicit peer resource refusal propagates 413. `sync_known()` returns a
    per-origin status mapping and leaves scheduling to the caller. Another peer
    could checkpoint each PUSH batch, canonicalize subscription unions, or
    report failures through exceptions instead.

17. **Unknown namespace bounds in spatial history.** Mesh says “Unknown versions
    cannot be spatially classified and are carried only by unrestricted
    subscriptions.” We assign opaque records `h=None`; they match precisely
    scopes with all null endpoints, including in a spatial-history query, and
    still receive local sequence entries. An empty subscription list selects
    none. A peer could restrict opaque transfer to MID mode; it would need an
    additional catch-up mechanism to meet unrestricted replication.

The three full positive candidate vectors, including input seed/envelopes and
C/S/MID/address/R/signature bytes, are in `tests/vectors.json`; regenerate with
`python3 tests/vectors.py`. They are pinned regression data for this independent
implementation. External cross-implementation verification remains pending.

## Cross-implementation divergences (post-hoc, from the interop harness)

The interpretations above were recorded before any interoperability run. The harness then
exercised the same edges against the reference implementation and found seven
HTTP-request-validation differences, itemised in [../interop/interop_matrix.md](../interop/interop_matrix.md) and
[PROOF_REPORT.md](PROOF_REPORT.md):

1. duplicate JSON member names in a `/push` body (this implementation rejects with 400;
   the reference accepts, last key wins);
2. equal `h_lo == h_hi` bounds in a spatial query (this implementation answers with an
   empty page; the reference returns 400);
3. reversed elevation bounds (this implementation answers with an empty page; the
   reference returns 400);
4. equal elevation bounds (this implementation answers with an empty page; the reference
   returns 400);
5. an unknown query member (this implementation returns 400; the reference ignores it);
6. a declared address that does not match the record on `/push` (this implementation
   returns a per-record `INVALID-structural`; the reference returns 400 for the whole
   request);
7. an empty `records` batch (this implementation returns 200 with empty results; the
   reference returns 400).

Items 2-4 partially contradict interpretation 6 above, which expected literal comparison
for every bound pair: reversed `h` bounds are in fact rejected by both implementations,
while equal `h` bounds and equal/reversed elevation bounds are accepted here and rejected
by the reference. Items 1, 5, 6 and 7 correspond to interpretations 8 and 12. No carrier
byte, MID, address, signature, validation state of a well-formed record, or spatial
selection of valid records differs as a result.
