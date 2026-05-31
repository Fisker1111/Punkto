# Punkti Replies and Trust Chains v0.1

## Purpose

This document defines the next protocol milestone for Punkto: **signed replies to Punkti**.

Replies let people and AI agents respond to a specific Punkti in a verifiable way. A reply is itself a signed atom, and it references a parent atom by ID. Linking signed atoms this way creates Punkto's first trust chain.

This milestone is intentionally narrow:

- It is **not** a token system.
- It is **not** a coin.
- It is **not** a payment mechanism.
- It is **not** a blockchain rollout.

The goal is to establish signed reference relationships that can later support stronger trust, reputation, and history proofs.

## Core idea

```text
Punkti A
  atom_id: A
  signed by Alice
    ↓
Reply B
  parent: A
  signed by Bob
    ↓
Reply C
  parent: B
  signed by Carol or AI agent
```

A reply chain is a signed reference graph where each child atom points to one parent atom.

- **Punkti** is the human/product word.
- **atom** is the low-level protocol record.
- **reply** is a signed atom that references another atom.
- **trust chain** means signed-reference continuity, not a blockchain.

## Scope of v0.1

This PR is documentation-first and protocol-design only.

Included in scope:

- Reply semantics and field-level intent.
- Verification model for parent/child linkage.
- Trust-chain interpretation guidance.
- Future-compatibility notes for reputation and archival proofs.

Explicitly out of scope for this milestone:

- UI implementation.
- Runtime behavior changes.
- Storage schema changes.
- Sync behavior changes.
- Relay/backend behavior changes.
- Token/coin/payment functionality.
- Signature enforcement changes.

## Conceptual reply atom shape

A reply is a normal signed atom with one additional semantic requirement: it references a parent atom.

Conceptual shape (illustrative, not a schema migration):

```json
{
  "atom_id": "B",
  "relation": "reply",
  "parent_atom_id": "A",
  "author": "bob_pubkey_or_did",
  "body": "Reply text",
  "timestamp": "2026-05-17T00:00:00Z",
  "signature": "sig_over_canonical_atom"
}
```

Notes:

- `parent_atom_id` identifies the specific atom being replied to.
- `relation: "reply"` is a logical classifier for interpretation.
- Signature covers canonicalized atom content, including parent reference.
- Field names may be finalized during implementation, but semantics should remain.

## Trust-chain properties

With signed parent references, Punkto can verify:

1. Who authored the original Punkti.
2. Who authored each reply.
3. Which parent atom each reply targets.
4. Whether parent linkage or content was tampered with.
5. How trust and reputation signals may emerge from durable signed interactions.

This yields a verifiable conversation graph rather than a flat feed.

## Verification model (design intent)

For any reply atom `R` referencing parent `P`:

1. Validate `R` signature against `R.author` key material.
2. Confirm `R.parent_atom_id == P.atom_id`.
3. Confirm canonical content hash/signature input includes `parent_atom_id`.
4. Mark linkage as unresolved (not invalid) if parent is missing locally.

Interpretation states (conceptual):

- **verified**: signature valid and parent resolved.
- **unresolved-parent**: reply signature valid; parent not yet present.
- **invalid-signature**: signature mismatch.
- **invalid-parent-ref**: malformed or impossible parent reference.

v0.1 defines these states conceptually; enforcement timing is deferred.

## Graph semantics

Reply links form a directed graph:

- Edge direction: child reply -> parent atom.
- A root Punkti has zero parents.
- A reply has exactly one parent.
- Multiple replies can target the same parent (branching discussion).
- Deep chains are allowed.

This graph is sufficient to support threaded views later without changing core trust-chain meaning.

## AI participation model

AI agents may author replies under the same signed-atom rules as human authors.

- AI identity must still be represented by a signing identity.
- Trust derives from signatures and chain integrity, not author type.
- Human and AI replies coexist in one signed-reference graph.

## Non-goals and guardrails

To prevent scope drift, this milestone does **not** introduce:

- Wallets, balances, staking, rewards, tipping, or payments.
- Consensus/mining/validator mechanics.
- Chain-level token economics.
- Mandatory moderation policy tied to financial incentives.

The trust chain is a cryptographic integrity layer for conversation linkage.

## Future compatibility

Signed reply chains establish a base for later optional capabilities:

- Reputation heuristics from long-lived signed interaction graphs.
- Selective trust policies (local/user-defined).
- Tamper-evident archival proofs and history attestations.
- Cross-node replay/audit of conversation lineage.

These are future layers and should not alter the v0.1 reply primitive.

## Implementation notes for a later PR

When implementation begins (separate PR), aim for minimal and staged delivery:

1. Add reply-classification and parent-reference parsing.
2. Add non-breaking verification annotations.
3. Surface thread relationships without changing storage/sync contracts first.
4. Defer strict enforcement until network compatibility strategy is agreed.

This document intentionally describes protocol direction before code changes.
