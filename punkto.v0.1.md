# Punkto — Core Specification (v0.1)

> Punkto defines how a point in 3D space is addressed, identified, and referenced.

A Punkto is a canonical identifier for a specific location in space, optionally bound to a signed message.

---

## 1. Definition

A Punkto is composed of:

* a **spatial component** (geohash-based)
* an optional **vertical component (Z / altitude)**
* an optional **content identifier**

A Punkto always refers to a location first. Data may be attached, but location defines identity.

---

## 2. Canonical Identity

A Punkto has exactly **one canonical representation**.

The canonical representation is the only form used for:

* identity
* signing
* hashing
* storage
* replication
* equality checks

All other representations are **derived views**.

> Canonical first. Everything else is translation.

---

## 3. Canonical Format

The canonical Punkto format is:

```
p:<spatial>-<z>-<id>
```

### Components

* `p:` → protocol prefix
* `<spatial>` → base32 geohash (latitude/longitude)
* `<z>` → altitude or vertical layer (e.g. `42m`, `-5m`, `L3`)
* `<id>` → optional identifier or reference (e.g. short ID or hash)

### Example

```
p:u4pruydqqvj-42m-9xk3
```

---

## 4. Minimal Punkto

A Punkto may omit optional components:

```
p:u4pru
```

This represents a spatial region without altitude or content.

---

## 5. Properties

A valid Punkto must be:

* **deterministic** — same input → same output
* **stable** — once created, it does not change
* **compact** — suitable for storage and transmission
* **location-first** — identity is derived from space

---

## 6. Derived Representations

A Punkto may be expressed in other forms for navigation, display, or interaction.

### URI Form

```
punkto://<spatial>/<z>/<id>
```

Example:

```
punkto://u4pruydqqvj/42m/9xk3
```

### Web Form

```
https://punkto.xyz/p/<spatial>/<z>/<id>
```

### Human-readable Form

```
Punkto u4pruydqqvj at 42m
```

Derived forms are not canonical and must never replace the canonical representation in protocol-level operations.

---

## 7. Equivalence

All valid derived forms must resolve to exactly one canonical Punkto.

```
p:u4pruydqqvj-42m-9xk3
⇄
punkto://u4pruydqqvj/42m/9xk3
⇄
https://punkto.xyz/p/u4pruydqqvj/42m/9xk3
```

Rules:

* Conversion must be **lossless**
* No additional meaning may be introduced
* No ambiguity is allowed

If a representation cannot resolve unambiguously to one canonical Punkto, it is not valid.

---

## 8. Interpretation Rules

* A Punkto identifies **space**, not ownership
* Multiple records may exist for the same Punkto
* A Punkto does not imply authority or truth
* Meaning is derived from associated data, not the identifier itself

---

## 9. Design Principles

* A Punkto names space before it names data
* Simplicity over completeness
* Explicit over implicit
* Readable where possible, strict where necessary
* No central authority
* Extendable without breaking compatibility

---

## 10. Future Extensions

Possible future additions include:

* true 3D spatial encoding (beyond lat/lon + Z)
* time dimension
* content-addressed identifiers (hash-based)
* semantic layers

Future extensions must not break existing canonical representations.

---

## 11. Status

Draft v0.1 — foundational specification
