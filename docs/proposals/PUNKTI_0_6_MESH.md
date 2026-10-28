# Punkti 0.6 Mesh — reference wire and sync specification

Status: experimental candidate, not frozen or production ready. Implements the
[L3 reset](PUNKTI_0_6_LAYER3_RESET.md) without changing its envelope, C, S, MID or R.

## Carrier and admission

The wire carries exact canonical R bytes in padded canonical base64. An item is
`{"address":"punkti/0.6:<mid>","sha256":"<SHA256 of R>","record":"<base64 R>"}`.
The item MUST have exactly these three members: a syntactically valid full address
string, 64 lowercase hexadecimal SHA256 digits, and canonical padded base64 R.
JSON carrier import accepts `t` only with spelling `0|[1-9][0-9]*` and integer
value <=9007199254740991; `-0`, negatives, leading zeros, plus signs, decimal
points and exponents are INVALID-structural. Canonical C and R are unchanged.
The transport digest checks transfer integrity; it is not provenance evidence.
Known carrier addresses are independently recomputed. The receiver checks every
candidate locally, including signature variants of an already known MID. Peer
validation claims are ignored. Only VALID enters the main store. Invalid structure
and supported-signature failures are rejected, so a forged variant cannot poison
an address before or after a valid record arrives.

UNVERIFIABLE-alg variants retain exact R in a separate digest-keyed candidate store
and can replicate without promotion. Future namespace wrappers use the same item
shape, but `record` contains opaque original bytes: only the transport digest is
checked and the state is OPAQUE-version. Declared future MIDs are unauthenticated.
Such candidates never overwrite verified entries. Unknown versions cannot be
spatially classified and are carried only by unrestricted subscriptions. The
legacy-only UNVERIFIABLE-key state is reserved; no legacy adapter is advertised.
No application payload, reference relation or extension schema is interpreted.

## HTTP operations

All bodies are UTF-8 JSON. This reference uses `http.server` and `urllib` on
`127.0.0.1` with separate servers/stores. It has no external service dependency.
Transport authentication, TLS, semantic trust and L3 provenance are distinct;
loopback HTTP supplies neither peer authentication nor semantic trust.

- `GET /hello`: protocol `punkti-mesh/0.6-draft`, store incarnation `epoch`,
  subscriptions, configured peer origins, capabilities, and resource limits.
  Capabilities are `push`, `range-mid`, `range-spatial`, `opaque-wrapper`.
- `POST /push`: `{"records":[item,...]}`. Locally validate each candidate and return
  `{"results":[{"state":"VALID","admitted":true},...]}`. Duplicates and valid
  out-of-scope records return admitted=false with a reason. PUSH accepts candidates,
  not authoritative assertions of validity.
- `GET /pull?q=<URL-encoded JSON query>`: Range PULL, described below. This is an
  application-level HTTP range API, not HTTP byte-range/206 semantics.
- `POST /sync`: `{"peer":"http://127.0.0.1:<port>","phase":"push"|"pull"}` invokes
  one reciprocal phase. Callback origins must already be configured locally;
  unsolicited URLs do not authorize callbacks. Success is `{"ok":true}`.

### Normative error tiers

| Failure | HTTP / outcome |
|---|---|
| Descriptor: non-object, missing/extra members, invalid/null address, noncanonical base64, malformed/mismatched SHA256, or locally recomputed 0.6 address mismatch | 400 error object; MUST admit no record from the request |
| Record content: structure/framing or supported-signature failure | 200 results, INVALID-structural / INVALID-provenance, admitted=false |
| Unsupported algorithm / future namespace | 200 results, UNVERIFIABLE-alg / OPAQUE-version candidate; admission depends on duplicate, scope and capacity |
| Legacy punkti/0.5.1 namespace | 200 per-record rejection, reason=legacy-adapter-unavailable |
| Duplicate / out-of-scope | 200 results, admitted=false with reason |
| Protocol size/limit excess | 413 error object with kind=resource; not an invalid-atom classification |
| Malformed range/limit | 400 error object |

Both PUSH servers MUST pre-validate every descriptor before admitting any record.
After descriptor validation, record-content failures and resource refusals may
leave earlier records admitted; retries are idempotent and safe. A decoded R over
the record limit is a resource refusal (413), with no admission from that request.
Limits: C <=1 MiB, R <=2 MiB, <=256 refs, relation <=1024 UTF-8 bytes,
HTTP request/response bodies <=8 MiB, pages/PUSH batches <=32 records,
<=128 unverified candidates/store; query bytes are locally bounded (16384 in
these experiments). All excesses return 413, including page limit 33.
A non-integer JSON number, bool, string or limit <1 returns 400.

### Required hello.limits members

| Member | Maximum | Unit |
|---|---:|---|
| body | 1048576 | canonical body bytes |
| record | 2097152 | single transport record bytes |
| page | 32 | records per page and per PUSH batch |
| http | 8388608 | HTTP request/response body bytes |
| candidates | 128 | stored unverified candidates |

These five names and integer JSON types are REQUIRED. A node MAY advertise lower
values for local policy. Additional members MAY be present; consumers MUST ignore
unknown members. These experiments emit exactly the five core members.

Page assembly also caps response bytes. The valid store/log is in-memory and
unbounded for this experiment; production storage budgets and rate limits remain
future work. Resource refusals prevent a successful sync checkpoint.

## Subscriptions and cursors

A scope is `{"xy_lo":null,"xy_hi":null,"z_min":null,"z_max":null}`.
The normative [XY_Z profile](PUNKTI_0_6_SPATIAL_XY_Z.md) defines
`h = <xy>_<z>`: standard 2D geohash (4–12 characters, default 10) and
canonical decimal WGS84 ellipsoidal metres, at most 32 characters total.
The empty h is unanchored. Z has no artificial altitude clamp.

XY bounds are null or 1–12 geohash characters. Compare the lower-edge keys
`K(xy) = xy.ljust(12, '0')`, inclusive below and exclusive above. Selection
consults only this key, never region size or overlap. Thus `[u3bu,u3bu000001)`
selects `u3bu`, while `[u3butz7k9q,u3butz7k9r)` does not.
Z bounds are null or canonical ASCII decimal strings (1–27 characters),
compared as exact decimals, never binary floats; lower inclusive, upper exclusive.
Reject equal/reversed XY keys, equal/reversed numeric Z bounds, and MID
`lo >= hi` with HTTP 400. In particular `[u3b,u3b0)` is rejected.
Invalid subscription bounds fail at construction as structural configuration errors.

Multiple scopes form a union. An empty scope selects all including unanchored
records; any spatial constraint excludes unanchored records. Empty subscription
lists select nothing. Filtering reads only the signed address, never payload x.
Spatial ordering is not a rectangular geographic bounding box. Renaming scope
members changes the scope binding hash and therefore cursor tokens.

Query: `{"mode":"spatial"|"mid","scope":scope,"lo":null,"hi":null,
"cursor":null,"limit":32}`. MID bounds are optional full namespace-qualified
addresses with inclusive lo and exclusive hi. Scope can further restrict a MID
sweep. Response: `{"records":[item,...],"cursor":token,"end":true|false}`.

Tokens are JSON objects with `epoch`, `scope` (SHA256 of canonical sorted compact
JSON containing mode, normalized scope, lo and hi), `after`, and `ceiling`.
Tokens are opaque to consumers, store-local, scope-bound and not authentication
credentials. Clients MUST echo server-issued tokens and MUST NOT construct `after`
tokens. Page size may change without changing token scope. A changed store
epoch or changed scope requires a new null cursor. No timestamps order sync.

For spatial history, each unique admitted entry gets a monotonic local sequence.
`after` is an integer sequence (initially 0), valid only in spatial mode; `ceiling` captures the log high-water on the first page.
A page scans only matching entries up to ceiling. At end, after advances to ceiling,
including nonmatching gaps. Reusing this finished token implements SUBSCRIBE FROM:
it captures a new high-water and returns only later matching entries. Partial
pages retain their original ceiling. The shared append log is logically projected
into each subscription; no full retransmission is needed at reconnect. Unknown-alg
variants also have distinct sequence entries. No deletion/retention is implemented.

MID pages sort by `(full_address, transport_digest)` so unverified signature
variants survive pagination; `after` holds that pair, or JSON null initially.
Null `after` is valid only in MID mode. An empty first MID page MUST emit
`"after":null`; `["",""]` MUST NOT be emitted and need not be accepted. A ceiling excludes concurrent
inserts from the active sweep. Always start a fresh null-cursor sweep to discover
later insertions, including those behind the address cursor. `end` means only the
end of this peer's bounded view, never global completeness.

## Discovery and convergence

Configured peers bootstrap operation without a coordinator or mandatory origin.
`/hello` supplies peer hints; `discover()` returns hints for explicit selection,
not automatic crawling or authority. Discovery MUST skip each unreachable or
malformed hello (protocol must be `punkti-mesh/0.6-draft` and peers must be a list).
Each hint MUST independently validate as a loopback HTTP origin; invalid hints
are skipped without losing valid siblings. Return distinct valid origins minus
self. Discovery MUST NOT auto-connect, mutate configured peers, or admit records. Reciprocal sync needs mutually configured
origins. Each connect/reconnect performs: local PUSH relevant to remote advertised
subscriptions; reciprocal PUSH relevant to local subscriptions; local Range PULL;
reciprocal Range PULL. PUSH checkpoints are keyed by remote origin, incarnation
and subscriptions and advance only after successful delivery. Pull checkpoints
advance only after an entire page is processed. Retries may repeat candidates.
Periodic `sync_known()` retries configured peers, reporting unavailable peers.
The caller controls scheduling.

### Peer failures and interrupted pages

Interoperable retry distinguishes `unreachable` (connect/TCP failure), `timeout`
(local deadline exceeded), `protocol` (non-2xx except resource refusal, invalid
response shape or unsupported protocol), and `resource` (413 refusal). Message
wording is implementation-defined; consumers MUST NOT infer retry safety from
strings. No protocol-level fixed deadline exists. Each peer operation MUST be
bounded by a documented local deadline: ordinary requests use 5 seconds in both
experiments; reciprocal `/sync` callbacks use 300 seconds.

A truncated, unreadable or invalid-JSON HTTP page MUST admit no records and MUST
NOT advance its pull checkpoint. After full decoding, the receiver MUST validate
every descriptor and local carrier before admitting any item. Any malformed item,
INVALID-structural or INVALID-provenance invalidates the entire page: raise a
peer/protocol error, admit none, retain the cursor, and retry from it. Duplicates,
out-of-scope outcomes and resource refusals do not classify a page as invalid.
After successful admission processing, advance the cursor exactly once. Earlier
completed pages remain committed. A failed operation MUST NOT advance its PUSH
or PULL checkpoint; retries are safe because admission is idempotent and
checkpoints only advance after success.

`connect()` is an orchestration helper, not a protocol operation. `/sync` performs
exactly one named reciprocal phase and MUST NOT recurse into `connect()`. A
synchronous callback executes a whole PUSH or PULL phase and may legitimately
exceed an ordinary request deadline. It MUST be bounded locally (300 seconds in
these experiments). Callback failure is a non-fatal peer failure and advances no
checkpoint for that failed operation. Callers MUST NOT assume both directions
complete within one fixed deadline or any fixed round count.
Store replacement changes epoch, forcing catch-up.

The reference retains state during a server disconnect; it does not persist stores
across process exits. Multi-hop convergence requires repeated fair peer exchanges,
eventual delivery, compatible scopes/resource policies and retained records. An
atom cannot traverse a permanently uninterested intermediate node. There is no
promise of completeness, deletion consensus, authority, or convergence during a
permanent partition. Repeated MID sweeps or spatial high-water catch-up cover
concurrent inserts. Missing-set reconciliation is omitted pending measurement;
see the experiment's measurement document for the final decision and counts.

Coverage advertisements and successful sync prove nothing global. Punkti MUST NOT
claim global completeness or freshness from peer coverage claims, successful sync,
a finite peer set, or retained cursors. Withholding, partitions and retention can
hide records indefinitely. `end:true` means only the end of that peer's bounded
view at that ceiling, not a statement about unseen peers or newer records.
