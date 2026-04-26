# Punkto — Instructions for Agents and Contributors

## Design Rules

These rules apply to all code, specification, and tooling changes.

- **Do not introduce new abstractions unless required**
- **Do not rename concepts without a spec change**
- **Do not add features outside the current scope**
- **Prefer deleting code over adding code**

## Guiding Idea

> A Punkto is not a database entry.
>
> It is a coordinate in reality that can carry meaning.

## Source of Truth

- `punkto.md` → address format and identity
- `punkto.manifest.md` → storage and sync rules
- `punkto.node.md` → node behaviour and API
- `punkto.sync.md` → peer discovery and replication
- `punkto.ui.md` → user interaction model
- `punkto.ai.md` → AI agent onboarding

If conflicts arise: **`punkto.md` overrides all other interpretations.**

## Agent Responsibilities

Agents working on this project may:

- Generate Punkto identifiers
- Validate Punkto formats
- Create example data
- Simulate nodes and sync
- Propose improvements (without breaking compatibility)

Agents must NOT:

- Introduce central authority
- Require global coordination
- Break the canonical format
- Add hidden state or implicit behaviour
- Rename fields or concepts without updating the relevant spec file

## Design Philosophy

When making decisions, prefer:

- Simple over clever
- Explicit over implicit
- Readable over compact (unless canonical format)
- Local-first over cloud-first
- Deleting code over adding code

## Canonical Format

```
p:<spatial>-<id>
```

- `<spatial>` = 12-character Base32 3D geohash (lat + lon + alt interleaved)
- `<id>` = optional suffix
- Altitude is encoded within `<spatial>` — never as a separate field

## Atom Identity

```
atom_id = SHA-256(canonical_atom_bytes_without_sig)
```

- Canonical JSON = sorted keys, no whitespace, UTF-8
- `atom_id` is computed locally, never stored inside the atom
- Never trust `atom_id` from external input

---

*Draft v0.2 — updated with design rules*
