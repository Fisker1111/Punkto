# Punkto — Core Specification (v0.2)

> Punkto defines how a point in 3D space is addressed, identified, and referenced.

A Punkto is a canonical identifier for a specific location in space, optionally bound to a signed message.

---

## 1. Definition

A Punkto is composed of:

* a **3D spatial component** — a Base32 geohash with interleaved latitude, longitude, and altitude
* an optional **content identifier**

A Punkto always refers to a location first. Data may be attached, but location defines identity.

Altitude is encoded inside the spatial component. There is no separate vertical field.

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
p:<spatial>-<id>
```

### Components

* `p:` → protocol prefix
* `<spatial>` → 12-character Base32 geohash, interleaved lat+lon+alt (3D)
* `<id>` → optional short identifier or reference

### Example

```
p:u4pruydqqvj3-9xk3
```

### Spatial encoding

The `<spatial>` component is a **12-character 3D geohash** compatible with the Punkti protocol.
It encodes latitude, longitude, and altitude interleaved into a single Base32 string.
At 12 characters, horizontal precision is approximately 2cm. Altitude precision is proportional.
This is sufficient to address individual cubic meters of physical space.

---

## 4. Minimal Punkto

A Punkto may omit the optional `<id>` component:

```
p:u4pruydqqvj3
```

This is a bare 3D location assertion — a point in space with no attached content identifier.

A Punkto may also use a shorter geohash as a spatial prefix:

```
p:u4pru
```

This represents a spatial region rather than a precise point.

---

## 5. Properties

A valid Punkto must be:

* **deterministic** — same input → same output
* **stable** — once created, it does not change
* **compact** — suitable for storage and transmission
* **location-first** — identity is derived from space
* **3D** — altitude is encoded, not implied

---

## 6. Derived Representations

A Punkto may be expressed in other forms for navigation, display, or human interaction.
All derived forms must resolve 1:1 to exactly one canonical Punkto.

### URI Form

```
punkto://<spatial>/<id>
```

Example:

```
punkto://u4pruydqqvj3/9xk3
```

### Web Form

```
https://punkto.xyz/p/<spatial>/<id>
```

### Human-writable Form

Named place segments may substitute for geohash prefixes:

```
punkto://dk/copenhagen/9xk3
```

Here `dk/copenhagen` resolves to a known geohash prefix. The resolver appends remaining
precision characters to form the full 12-character spatial component. Example resolution:

```
punkto://dk/copenhagen/fufksn
       → ifmrj + fufksn
       → p:ifmrjfufksn
```

The human-writable form is a Punkto layer concept. Resolution requires a named-place registry
or prefix map. It is not part of the Punkti protocol.

### Human-readable Display

```
Copenhagen / wind: 12m/s
```

Display only. Not reversible to canonical without additional context.

Derived forms are not canonical and must never replace the canonical representation
in protocol-level operations.

---

## 7. Equivalence

All valid derived forms must resolve to exactly one canonical Punkto.

```
p:u4pruydqqvj3-9xk3
⇄
punkto://u4pruydqqvj3/9xk3
⇄
https://punkto.xyz/p/u4pruydqqvj3/9xk3
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

## 9. Compatibility

The `<spatial>` component is directly compatible with the Punkti protocol `h` field.

Punkti atom `h` field: Base32, interleaved lat+lon+alt, 4–12 characters.
Punkto canonical spatial: Base32, interleaved lat+lon+alt, 12 characters (fixed).

A Punkto canonical spatial at full precision is a valid Punkti `h` value.
A Punkti `h` value at 12-character precision is a valid Punkto spatial component.

---

## 10. Design Principles

* A Punkto names space before it names data
* Altitude is part of the address, not an annotation
* Simplicity over completeness
* Explicit over implicit
* Readable where possible, strict where necessary
* No central authority
* Extendable without breaking compatibility

---

## 11. Future Extensions

Possible future additions include:

* sub-centimeter spatial encoding
* time dimension
* content-addressed identifiers (hash-based)
* semantic layers
* richer named-place resolution

Future extensions must not break existing canonical representations.

---

## 12. Changelog

| Version | Changes |
|---------|---------|
| v0.1 | Initial specification. Canonical form `p:<spatial>-<z>-<id>` with separate altitude component. |
| v0.2 | Altitude moved into 3D geohash. Canonical form simplified to `p:<spatial>-<id>`. Spatial fixed at 12 chars. Added human-writable URI form. Added Punkti compatibility section. |

---

## 13. Status

Draft v0.2 — 3D geohash canonical form
