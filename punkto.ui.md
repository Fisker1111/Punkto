# Punkto UI Guidelines (v0.1)

> Punkto is spatial first. The interface must reflect that.

---

## 1. Core Principle

Users do not think in hashes.

They think in:

* places
* directions
* height
* context

The UI must translate Punkto into spatial understanding.

---

## 2. Spatial First Interaction

The primary interaction model is movement through space.

Users should:

* explore by moving across a map or 3D view
* discover Punktos based on location
* interact with nearby space, not abstract identifiers

Typing or pasting IDs is secondary.

---

## 3. Visual Representation

A Punkto should be shown as:

* a **point in space**

Optionally enhanced with:

* a glow or beacon
* a label
* a vertical indicator (height/depth)

A Punkto should feel like something that exists in the world.

---

## 4. Interaction Model

Users should be able to:

* tap or click a location
* place a Punkto directly in space
* view nearby Punktos automatically
* navigate by movement rather than search

---

## 5. Display and Identity

Punkto has two representations:

### Human-readable (default)

```
Zealand / 42m / wind: 12m/s
```

### Canonical (on demand)

```
p:u4pruydqqvj-42m-9xk3
```

Rules:

* UI defaults to human-readable
* canonical form is hidden unless explicitly requested
* canonical form must never be altered

---

## 6. Layers

Punktos may exist across spatial layers:

* surface
* underground
* atmospheric

UI should allow:

* filtering layers
* toggling visibility
* understanding vertical separation

---

## 7. Density and Relevance

When many Punktos exist:

* cluster distant points
* fade low-relevance data
* highlight nearby or recent data

Relevance should prioritize:

* proximity
* recency
* user context

---

## 8. Local-First Behavior

The UI should:

* function offline when possible
* allow local creation of Punktos
* sync when connectivity is available

Users should feel ownership of their local data.

---

## 9. Minimal UI Philosophy

* avoid dashboards
* avoid complex forms
* avoid unnecessary abstraction
* prefer direct interaction

The UI should feel:

* immediate
* physical
* intuitive

---

## 10. Guiding Idea

> A Punkto should feel like placing a marker in the world, not writing to a database.
