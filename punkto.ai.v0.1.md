# Punkto AI Interface (v0.1)

> Defines how AI systems read, write, and interact with Punktos.

Punkto provides a spatial memory layer where AI systems can store and retrieve information anchored to real-world locations.

---

## 1. Role of AI

An AI interacting with Punkto acts as:

* a **reader** of spatial data
* a **writer** of observations
* a **processor** of local context

AI systems do not own data.
They observe, interpret, and contribute.

---

## 2. Core Concepts

AI must understand:

* **Punkto** → a canonical spatial identifier
* **Atom** → a signed record attached to a Punkto
* **Node** → a storage and replication endpoint
* **Feed** → a sequence of Punkto atoms

---

## 3. Reading Data

AI retrieves data from nodes:

```txt id="dzs49k"
GET /feed
GET /feed?since=<cursor>
GET /punkto/<canonical>
```

AI should:

* prefer local or nearby nodes
* process data incrementally
* handle partial data gracefully

---

## 4. Writing Data

AI may create new Punktos by submitting atoms:

```txt id="p3v3n8"
POST /atom
```

Example:

```json id="0a6b4l"
{
  "punkto": "p:u4pruydqqvj-42m",
  "timestamp": "2026-04-25T10:00:00Z",
  "payload": "wind: 12m/s"
}
```

AI must:

* use canonical Punkto format (`p:`)
* include a timestamp
* sign records when signing is available
* avoid modifying existing records

---

## 5. Spatial Reasoning

AI should treat space as the primary index.

Preferred operations:

* find nearby Punktos
* group Punktos by proximity
* interpret vertical layers
* track changes over time

AI should not rely on:

* global ordering
* centralized indexing
* full dataset availability

---

## 6. Local-First Behavior

AI should:

* operate with partial data
* cache recent Punktos
* sync opportunistically

Behavior must degrade gracefully when offline.

---

## 7. Interpretation Rules

* A Punkto identifies a location, not truth
* Multiple conflicting records may exist
* AI must not assume authority
* AI should evaluate based on context and signatures

---

## 8. Constraints

AI must NOT:

* invent canonical Punkto identifiers
* rewrite existing records
* assume completeness of data
* depend on a single node

---

## 9. Usage Patterns

### Observation

Store measured or detected data at a location.

### Annotation

Attach meaning or interpretation to a location.

### Query

Retrieve nearby Punktos to understand context.

---

## 10. Guiding Idea

> Punkto is not a database.
>
> It is a spatial memory layer that AI can read from and write to.
