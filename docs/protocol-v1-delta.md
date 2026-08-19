# Protocol v1 Delta — Freeze Document (Kernel §A)

> Implements Pilot 1 work packages **P-1, P-2, P-3, P-4** against the merged spec's Kernel contracts §A.
> Status: **for ChatGPT review before code** (builder AZ, reviewer ChatGPT per the 2026-07-26 workflow).
> Rule of this document: every line is load-bearing. If it isn't enforceable in relay validation and PWA code, it doesn't belong here.

## 0. Current wire format (baseline)

An atom is a canonical JSON object (sorted keys, no whitespace, UTF-8). Today the meaningful top-level fields are:

| Field | Type | Meaning |
|---|---|---|
| `punkto` | string | `p:<spatial>-<id>` address; altitude inside `<spatial>` |
| `t` | int | creation timestamp, unix **milliseconds** |
| `text` | string | human message |
| `pub` | string | author Ed25519 public key (hex) |
| `sig` | string | signature over canonical bytes **without** `sig` |
| `parent` | string (optional) | `atom_id` of parent — marks a reply (punkti.replies.md v0.1) |

`atom_id = SHA-256(canonical bytes without sig)`, computed locally, never stored in the atom, never trusted from input. Relay acceptance: `t` within the live window (default 24h, `atom_too_old`). Relay serving: recent window, `pinned_atoms`, or archive per node policy.

## 1. New fields (the entire delta)

Four optional fields. **All are part of the signed payload** — they appear in canonical order and are therefore covered by `sig` and hashed into `atom_id`. No unsigned side channels, ever.

| Field | Type | Optional | Meaning |
|---|---|---|---|
| `exp` | int (ms) | yes — **required iff `kind == "urgent"`** | expiry timestamp; after `exp` the atom is *settled* (§4) |
| `kind` | string enum | yes | closed vocabulary: `"note"` (default when absent), `"infra"`, `"urgent"`, `"event"` |
| `rel` | string enum | yes — requires `parent` | typed relation to parent: `"replies-to"`, `"confirms"`, `"disputes"`, `"supersedes"` |
| `acc` | number (meters) | yes | horizontal positional uncertainty from the device at create time |

Naming follows the existing style: short lowercase keys, no nesting, no arrays, no nulls. Absent means undefined — fields are omitted, never `null`.

## 2. Validation rules (relay MUST, PWA SHOULD match)

### `exp`
- If present: integer, `exp > t`, and `exp - t ≤ 30 days` (2,592,000,000 ms). Reject otherwise: `invalid_exp`.
- If `kind == "urgent"`: `exp` required, and `exp - t ≤ 7 days` (604,800,000 ms). Reject otherwise: `urgent_requires_exp` / `invalid_exp`.

### `kind`
- If present: must be one of `note | infra | urgent | event`. Unknown values rejected: `invalid_kind`. The vocabulary is **closed** — adding a kind is a protocol change, not a client choice.
- Absent = `note` (everyday). Clients must never need to store the default explicitly.

### `rel`
- If present: must be one of `replies-to | confirms | disputes | supersedes`. Unknown values rejected: `invalid_rel`.
- `rel` without `parent` is rejected: `rel_requires_parent`.
- `parent` without `rel` remains legal and means a plain reply (backward compatible with v0.1 replies; treated as `replies-to` by the derivation rule §5).
- No approval-shaped relation exists by construction. There is no `likes`, no `endorses`, no `upvotes` — and there must never be a way to express one inside this vocabulary.

### `acc`
- If present: finite number, `0 < acc ≤ 100,000` (meters). Reject otherwise: `invalid_acc`.
- Clients record `acc` from `GeolocationCoordinates.accuracy` at create time. Altitude uncertainty is not frozen in v1 (phones lie about altitude; the honest floor chip already says "estimated") — tracked as follow-up, not silently added later.

### Forward compatibility
- Relays MUST preserve unknown top-level fields untouched (store, serve, federate) but MUST NOT validate or interpret them. A v1 relay receiving a future field stores it verbatim. This is how the vocabulary grows without a flag day.
- Relays MUST reject atoms that fail the rules above with the named errors. Old atoms without the new fields remain valid and served unchanged.

## 3. Serving and expiry semantics

- **Settled atoms** (`exp` present and `exp < now`): excluded from default feed (`/feed`, `/latest`) and default sync responses. Retained in the log; retrievable by direct `atom_id` lookup with `settled: true` in the response envelope **[envelope shape confirmed at implementation]**.
- A settled **urgent** atom must never be served in any live view. Stale warnings mislead — this is the abuse-resistance floor of the urgency kind.
- Serving-policy overrides (`pinned_atoms`, archive mode) apply to recency windows only; they do **not** resurrect settled atoms into live feeds. An archive node may serve settled atoms for historical queries, always flagged settled.
- Expiry is **not deletion**. Nothing is removed from the append-only log; settled is a serving state, not a tombstone. (Tombstones/retractions are Kernel §A.3 follow-up, out of this delta.)

## 4. Derived state rule (the hydrant display)

Displayed thread state is **computed, never stored**. Given a root atom and its relation graph:

- `confirmations` = count of direct `confirms` children from distinct `pub` keys (one confirmation per author — later duplicates from the same key collapse to the earliest)
- `disputes` = same rule for `disputes`
- `status` = `resolved` if any `supersedes` child exists whose own status is not disputed; otherwise `open`
- freshness = from `t` of the most recent relation child

Example rendered by the client (never stored): **"3 confirmations · open · 11 days"**.

Relay: MUST expose the raw relation children (clients can derive); MAY precompute derived counts as a convenience field in the response envelope, clearly marked derived and recomputed per request — never persisted into any atom.

## 5. PWA create-flow changes (P-4 and UX)

- Every created atom records `acc` from the live geolocation fix; if the fix reports no accuracy, `acc` is omitted (absent = unknown — never invented).
- Urgent creation: `kind: "urgent"` with `exp` defaulting to `now + 24h`, user-adjustable up to the 7-day ceiling. The create sheet states expiry plainly: *"Visible for 24 hours."*
- Board actions set relations explicitly: **Reply** → `rel: "replies-to"`; **Confirm** → `rel: "confirms"`; **Dispute** → `rel: "disputes"`; **Mark resolved** → `rel: "supersedes"`. All set `parent` to the board's root atom. Existing plain-reply behavior is unchanged.
- Compose stays independent of map load (C-1): none of these fields require the map to be ready.

## 6. Federation

- The new fields travel inside the atom JSON; sync is field-agnostic and already carries them.
- A receiving relay validates per §2 and rejects invalid atoms from peers exactly as from clients (logged as peer rejections).
- Mixed-version federation: a pre-v1 relay stores and serves v1 atoms untouched (unknown-field preservation, §2). It cannot enforce urgency expiry — acceptable during transition; v1 clients still hide settled atoms client-side. Document in the ops notes; do not engineer around it.

## 7. Test requirements (extend `relay/test_relay.py`, currently 56 green)

| WP | Tests |
|---|---|
| P-1 `exp` | accept valid `exp`; reject `exp ≤ t`; reject `exp - t > 30d`; settled atom absent from `/feed` and `/latest`, present by direct lookup with settled flag; old atoms (no `exp`) unaffected |
| P-2 `kind` | accept each vocabulary value; reject unknown kind; urgent without `exp` → `urgent_requires_exp`; urgent with `exp - t > 7d` → `invalid_exp`; settled urgent absent from all live serving modes incl. pinned |
| P-3 `rel` | accept all four relations with parent; reject `rel` without parent; reject unknown rel; plain `parent`-only reply still accepted; derivation: 3 confirms from 3 keys counts 3, 2 confirms from 1 key counts 1, supersedes resolves, disputed resolution stays open |
| P-4 `acc` | accept valid; reject 0 / negative / non-number / > 100 km; absent tolerated; `acc` covered by signature (tamper → invalid sig) |

All 56 existing tests must stay green — backward compatibility is a test result, not an intention.

## 8. Explicitly not in this delta

- Tombstones/retractions and author key rotation (Kernel §A.3 follow-up)
- Altitude uncertainty field (§2 note — follow-up after honest research)
- Moderation actions (delist, precision-blur) and their federation envelope (G-5 document first, then a separate protocol delta)
- Aggregate bbox+zoom endpoint (R-2 — a query contract, not an atom change)
- Any rendering rule (R-1 owns the urgent register and liveness grammar)

---

*Authored by AZ 2026-07-26 per Pilot 1 Phase P. Awaiting ChatGPT review; P-1 implementation starts after review sign-off.*
