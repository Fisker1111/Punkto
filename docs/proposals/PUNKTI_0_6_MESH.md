# Punkti 0.6 Mesh — reference wire and sync specification

Status: experimental candidate, not frozen or production ready. Implements the
[L3 reset](PUNKTI_0_6_LAYER3_RESET.md) without changing its envelope, C, S, MID or R.

## Carrier and admission

The wire carries exact canonical R bytes in padded canonical base64. An item is
`{"address":"punkti/0.6:<mid>","sha256":"<SHA256 of R>","record":"<base64 R>"}`.
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

Bad requests return HTTP 400; resource refusals return 413 with kind=`resource`,
not an invalid-atom classification; unreachable callbacks return 502. PUSH batches
may be partially admitted before an error: retry is safe. Admission is idempotent.
Limits: C <= 1 MiB, R <= 2 MiB, <=256 refs, relation <=1024 UTF-8 bytes,
HTTP bodies <=8 MiB, pages/batches <=32 records, <=128 unverified candidates/store.
Page assembly also caps response bytes. The valid store/log is in-memory and
unbounded for this experiment; production storage budgets and rate limits remain
future work. Resource refusals prevent a successful sync checkpoint.

## Subscriptions and cursors

A scope is `{"h_lo":null,"h_hi":null,"z_min":null,"z_max":null}`. Null is an
unbounded endpoint. h endpoints are 1–12 characters from the geohash alphabet;
prefix endpoints participate in literal lexicographic `[lo,hi)` comparison, not
prefix expansion. The geohash alphabet order equals ASCII order. For example use
`gggh..gggj`; `i` is not a geohash character. Multiple scopes form a union.
An empty scope selects all, including unanchored h="". Any spatial constraint
excludes unanchored records. Empty subscription lists select nothing.

Elevation uses a **provisional profile**, pending the reset's geohash review:
12 base32 characters encode 60 bits, interleaved latitude/longitude/altitude,
20 bits each, MSB first. Altitude cell center is
`-500 + (z_integer + 0.5) * 9000 / 2^20` metres. This is the existing 3D profile,
implemented independently in the experiment without production imports. z bounds
are finite numbers with lower inclusive and upper exclusive semantics. Filtering
reads only addressed h and its decoded altitude, never x. Spatial ordering is not
claimed to be a rectangular geographic bounding box.

Query: `{"mode":"spatial"|"mid","scope":scope,"lo":null,"hi":null,
"cursor":null,"limit":32}`. MID bounds are optional full namespace-qualified
addresses with inclusive lo and exclusive hi. Scope can further restrict a MID
sweep. Response: `{"records":[item,...],"cursor":token,"end":true|false}`.

Tokens are JSON objects with `epoch`, `scope` (SHA256 of canonical sorted compact
JSON containing mode, normalized scope, lo and hi), `after`, and `ceiling`.
Tokens are opaque to consumers, store-local, scope-bound and not authentication
credentials. Page size may change without changing token scope. A changed store
epoch or changed scope requires a new null cursor. No timestamps order sync.

For spatial history, each unique admitted entry gets a monotonic local sequence.
`after` is that sequence; `ceiling` captures the log high-water on the first page.
A page scans only matching entries up to ceiling. At end, after advances to ceiling,
including nonmatching gaps. Reusing this finished token implements SUBSCRIBE FROM:
it captures a new high-water and returns only later matching entries. Partial
pages retain their original ceiling. The shared append log is logically projected
into each subscription; no full retransmission is needed at reconnect. Unknown-alg
variants also have distinct sequence entries. No deletion/retention is implemented.

MID pages sort by `(full_address, transport_digest)` so unverified signature
variants survive pagination; `after` holds that pair. A ceiling excludes concurrent
inserts from the active sweep. Always start a fresh null-cursor sweep to discover
later insertions, including those behind the address cursor. `end` means only the
end of this peer's bounded view, never global completeness.

## Discovery and convergence

Configured peers bootstrap operation without a coordinator or mandatory origin.
`/hello` supplies peer hints; `discover()` returns hints for explicit selection,
not automatic crawling or authority. Reciprocal sync needs mutually configured
origins. Each connect/reconnect performs: local PUSH relevant to remote advertised
subscriptions; reciprocal PUSH relevant to local subscriptions; local Range PULL;
reciprocal Range PULL. PUSH checkpoints are keyed by remote origin, incarnation
and subscriptions and advance only after successful delivery. Pull checkpoints
advance only after an entire page is processed. Retries may repeat candidates.
Periodic `sync_known()` retries configured peers, reporting unavailable peers.
The caller controls scheduling. Store replacement changes epoch, forcing catch-up.

The reference retains state during a server disconnect; it does not persist stores
across process exits. Multi-hop convergence requires repeated fair peer exchanges,
eventual delivery, compatible scopes/resource policies and retained records. An
atom cannot traverse a permanently uninterested intermediate node. There is no
promise of completeness, deletion consensus, authority, or convergence during a
permanent partition. Repeated MID sweeps or spatial high-water catch-up cover
concurrent inserts. Missing-set reconciliation is omitted pending measurement;
see the experiment's measurement document for the final decision and counts.
