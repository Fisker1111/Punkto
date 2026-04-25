# Punkto — AI Node Instructions

Version: 0.2  
Status: Draft

---

## 1. What You Are

You are a node.

AI agents participate in the Punkto network as equal nodes — the same as any other client or server. There is no special AI interface. There are no AI-only endpoints. You read and write using the same protocol as everything else.

---

## 2. What the Network Is

Punkto is an append-only network of atoms anchored to 3D locations in the real world.

- Every atom has a location (a canonical Punkto identifier)
- Every atom has a timestamp
- Atoms are never deleted or modified
- No central authority exists

---

## 3. The Canonical Form

A Punkto address is:

```
p:<spatial>
```

or with an optional sub-location identifier:

```
p:<spatial>-<id>
```

Where:

- `<spatial>` — a **fixed 12-character** Base32 3D geohash, interleaving latitude, longitude, and altitude
- `<id>` — an optional alphanumeric sub-identifier within that location

Example:
```
p:u4pruydqqvj3-9xk3
```

Rules:
- Always use the canonical `p:` form when writing atoms
- `<spatial>` must be derived from real-world coordinates — never fabricated
- The canonical form must never be altered or reformatted

---

## 4. Minimum Atom

The bare minimum atom contains:

| Field | Type | Description |
|-------|------|-------------|
| `punkto` | string | Canonical `p:` address |
| `t` | int64 | Unix timestamp in **milliseconds** (13 digits) |

Example:
```json
{"punkto":"p:u4pruydqqvj3-9xk3","t":1745598371000}
```

Additional fields (payload, author, signature) are optional but recommended.

---

## 5. How to Read

**Full feed from a node:**
```
GET /feed
```
Returns `{cursor, atoms}`

**Feed since a cursor (incremental sync):**
```
GET /feed?since=<cursor>
```
Cursor is a byte offset integer. Store it. Resume from it next time.

**All atoms at a specific location:**
```
GET /punkto/<canonical>
```
Returns `{punkto, atoms}`

**Node health:**
```
GET /health
```
Returns `{status: "ok"}`

---

## 6. How to Write

```
POST /atom
Content-Type: application/json

{"punkto":"p:u4pruydqqvj3-9xk3","t":1745598371000,"payload":{...}}
```

Response on success:
```json
{"status":"accepted","cursor":"...","punkto":"p:u4pruydqqvj3-9xk3"}
```

Error response:
```json
{"error":"invalid_punkto","message":"..."}
```

---

## 7. Constraints

- **Do not fabricate locations.** Derive `<spatial>` from verified real-world coordinates only.
- **Do not rewrite records.** The network is append-only. Once written, atoms are permanent.
- **Do not assume completeness.** A node may have partial data. Multiple nodes may hold different subsets.
- **Sign when able.** Include `author` and `signature` fields if your system supports it.
- **Operate gracefully with missing data.** An empty feed is valid. An empty Punkto is valid.

---

## 8. Discovery

Nodes may advertise capabilities via `GET /info`:

```json
{"capabilities":["write","sync","ai"]}
```

The `ai` capability is a **discovery hint** only — it signals the node is known to be used by AI clients. It does not gate access. All nodes use the same API.

---

## 9. Compatibility

This protocol aligns with the Punkti protocol:

- `punkto` field maps to Punkti `h` (3D geohash)
- `t` field maps to Punkti `t` (int64 unix milliseconds)
- Atom format is a superset of the Punkti minimum atom

---

## Changelog

| Version | Change |
|---------|--------|
| 0.2 | Rewritten — AI are nodes, not a special class. Instruction set format. |
| 0.1 | Initial draft (archived as `punkto.ai.v0.1.md`) |
