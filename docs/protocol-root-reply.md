# Punkto ROOT/REPLY Board Model

## Purpose

This document defines the Punkto public conversation model before any protocol,
relay, storage, sync, or PWA behavior changes are implemented.

Punkto boards are rooted in one exact point in reality. A public conversation
starts with a `ROOT` atom at that point, and public `REPLY` atoms join that board
only by explicit parent/root atom references. Proximity never creates reply
membership.

## Terminology

- **ROOT atom**: a public atom with no parent reference. It starts a board.
- **REPLY atom**: a public atom that points to an existing board/root/parent atom
  by explicit atom id.
- **Board**: a ROOT atom plus public REPLY atoms attached by explicit ids.
- **Orphan reply**: a reply whose parent/root is not currently available on this
  node or client.
- **Genesis**: an optional special permanent ROOT atom. Genesis atoms are not the
  default board model.

## Core model

Every public board starts with a ROOT atom. A REPLY atom belongs to a board by
explicitly referencing a parent/root atom id. The reply relationship is explicit,
not inferred from distance, map clustering, building membership, floor, or
nearby coordinates.

A nearby atom with no parent/reply reference is a separate ROOT atom, even when
it is very close to an existing board.

Every conversation is public. Private or access-controlled threads are outside
this model.

## Future fields, not current runtime schema

The following fields describe future protocol intent only. They are not a schema
migration in this documentation PR and are not implemented by the current relay,
storage, sync, or PWA UI.

```json
{
  "parent_id": null,
  "root_id": "optional_atom_id",
  "relation": "root",
  "location_lock": true,
  "location_source": "root"
}
```

Suggested meanings:

- `parent_id`: `null` or absent for ROOT atoms; an atom id for REPLY atoms.
- `root_id`: optional atom id for the board root. A direct reply to a root may use
  the same id for `parent_id` and `root_id`.
- `relation`: logical classifier, either `"root"` or `"reply"`.
- `location_lock`: when true, declares that the reply location is locked to the
  board root location.
- `location_source`: for replies, `"root"` means the reply copied the location
  tuple from the root rather than using the current crosshair/device position.

Final field names may change during implementation, but these semantics should
remain.

## Rules

1. If `parent_id` is absent or `null`, the atom is a ROOT.
2. If `parent_id` is present, the atom is a REPLY.
3. A REPLY must copy the root location tuple exactly.
4. A REPLY should not be accepted as moving the board.
5. Client UI should create replies from board view only.
6. The Map `+` button creates a new ROOT at the crosshair.
7. A Reply button creates a REPLY at the root location, not the current crosshair.
8. If the parent/root is missing, UI may show `Reply to unknown atom`.
9. Nodes may serve recent replies even if the root is unavailable.
10. Important, pinned, or genesis roots may be served forever by node policy.

## Exact-location reply rule

A reply atom must carry the exact same location tuple as its root board. Replies
do not drift and do not relocate a board.

The tuple includes every location component present on the root, including:

- `lat`
- `lon`
- `altitude_m` / `z`
- `floor` / `level`, if present
- `punkto/location` id, if present

A REPLY must copy these values exactly from the root. If the root has altitude,
floor, level, or a Punkto location id, the reply must carry the same value. If a
client is currently viewing a nearby crosshair or has a newer GPS estimate, that
current position must not be used for the reply.

No drifting replies. No "nearby means reply". No "same building means reply".

## Board membership

Board membership is determined by explicit ids:

- A ROOT starts a board.
- A REPLY attaches to a board by `parent_id` and, when present, `root_id`.
- A reply to a reply still belongs to the root board, but its immediate parent is
  the atom named by `parent_id`.
- Spatial proximity may help discovery or rendering, but must not define reply
  membership.

If two atoms are near each other and neither references the other, they are two
separate ROOT boards.

## Orphan and missing-parent behavior

An orphan reply is a reply whose parent/root is not currently available on a node
or client. Missing local context should not automatically make the reply invalid.
It means the relationship is unresolved on that node/client until the referenced
parent/root is fetched, synced, or otherwise made available.

Recommended interpretation states for future implementation:

- **resolved reply**: parent/root is available and the explicit relationship can
  be shown in board context.
- **orphan reply**: parent/root is not currently available, but the reply carries
  a syntactically valid parent/root reference.
- **invalid reply reference**: the parent/root reference is malformed or fails
  future validation rules.

Client UI may show `Reply to unknown atom` for orphan replies. Nodes may serve
recent replies even if the root is unavailable, and nodes may keep important,
pinned, or genesis roots available forever by local serving policy.

## Product behavior intent

Future client behavior should preserve the board's exact point:

- Opening a board shows the ROOT and attached public replies.
- Creating from the Map `+` action creates a separate ROOT at the crosshair.
- Replying from a board creates a REPLY using the root's exact location tuple.
- Reply UI should live in board context so users do not accidentally create a
  reply at a nearby but different real-world point.

## Examples

### Example ROOT

```json
{
  "kind": "atom",
  "relation": "root",
  "parent_id": null,
  "lat": 55.7000,
  "lon": 12.5000,
  "altitude_m": 21,
  "floor": 7,
  "text": "Noise from ventilation here"
}
```

### Example REPLY

```json
{
  "kind": "atom",
  "relation": "reply",
  "parent_id": "atom_root_abc123",
  "root_id": "atom_root_abc123",
  "lat": 55.7000,
  "lon": 12.5000,
  "altitude_m": 21,
  "floor": 7,
  "text": "I hear it too"
}
```

### Example nearby-but-not-reply

```json
{
  "kind": "atom",
  "relation": "root",
  "parent_id": null,
  "lat": 55.7001,
  "lon": 12.5002,
  "altitude_m": 18,
  "floor": 6,
  "text": "Different issue on floor 6"
}
```

## Out of scope for this documentation PR

This document does not change runtime atom schema, relay validation, storage,
sync, PWA UI behavior, map/text/board behavior, Docker, Caddy, deployment, or any
hard marker. Implementation belongs in later, explicit PRs.
