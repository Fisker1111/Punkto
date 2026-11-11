# CODEX TASK 63-C — addendum: remove the last 2px mobile bottom-sheet / bottom-nav overlap

Repository: `Fisker1111/Punkto`
Branch: `feat/issue60-pwa-m8-ux` (HEAD is still `dfa29f1cbe753988300056ded01f7970cd400b22`
plus your uncommitted M8B work in the working tree)
Issue: https://github.com/Fisker1111/CEO-OS/issues/63

**Read first:** `docs/CODEX_TASK_63.md` (the normative M8B spec),
`docs/CODEX_TASK_63_B.md` (the camera-padding addendum, already implemented in your
working tree), and `pwa/index.html` (the CSS for `#map-board-sheet` and `#bottom-nav`).

This addendum is normative and additive. If you believe any rule below is
contradictory or impossible, **stop and report** instead of silently choosing a
different design.

---

## 0. What Hermes measured in a real browser (read-only QA)

CEO-OS #63 requires: *"Maintain 44px touch controls / **zero mobile bottom-sheet
overlap**, keyboard accessibility, correct header h/absolute Z, trust labels."*

Measured on the M8B working tree, mobile viewport 390×844, Chromium, against the
**real** read-only publication:

```
#map-board-sheet (the fixed container)  top 189  bottom 712
#bottom-nav                             top 710  bottom 830
overlap                                 2 px
```

The `#map-board-sheet` container has `padding: 0 12px` (no vertical padding) and
its child `.board-detail` is the visible card, so the visible card's bottom edge
is the container's bottom edge — the card really does sit **2 px underneath the
top edge of the bottom nav**.

Root cause, in `pwa/index.html`:

```css
#map-board-sheet {
  position: fixed;
  ...
  bottom: calc(132px + var(--safe-b));
}
```

The mobile nav footprint is **134 px**: in the `max-width: 899px` media query the
app declares `:root { --nav-h: 134px; }`, and the measured nav element occupies
exactly 134 px of the viewport (`710 → 844`, of which 120 px is the visible nav
and 14 px is the safe-area strip). `132px` is 2 px short.

This is **pre-existing** in PR #154 (the same `132px` literal is on the base
commit `dfa29f1`); it is not a regression of the M8B change. It is nevertheless
inside the M8B acceptance criteria, so M8B closes it.

---

## 1. Required fix (minimal, inside `pwa/index.html` only)

1. Change the mobile/default `#map-board-sheet` bottom offset from
   `calc(132px + var(--safe-b))` to `calc(134px + var(--safe-b))`.

   Do **not** use `var(--nav-h)` here: `--nav-h` is `134px` on mobile but `60px` on
   desktop, and the desktop bottom offset is already overridden by the
   `@media (min-width: 900px)` block (`bottom: 20px`), so the literal keeps the
   two breakpoints independent and avoids double-counting `--safe-b` (which is
   already inside the 134 px footprint).

2. Change nothing else in that rule — not `top`, not `max-height`, not `padding`,
   not the `.board-detail` child rule, and not the `@media (min-width: 900px)`
   desktop block.

3. Do **not** touch any other file except the test file named in §2.

4. The result must be a **0 px** overlap between the visible `.board-detail`
   card and `#bottom-nav` at 390×844 (and at 360×640), with the sheet still fully
   readable and the "← Back to map" button still reachable.

---

## 2. Required regression test

Extend `pwa/test-punkto-m8b-map-first.mjs` (do **not** create a second test
file) with one focused check that the mobile bottom-sheet offset clears the
mobile nav footprint:

- read `pwa/index.html` (already read by the suite as `index`);
- assert the `#map-board-sheet` rule's `bottom:` value is
  `calc(134px + var(--safe-b))` — i.e. parse the `#map-board-sheet { ... }` block
  and assert the `bottom:` declaration is `calc(134px + var(--safe-b))` (allow
  whitespace variation);
- assert the same media-query block declares `:root { --nav-h: 134px; }` for the
  mobile breakpoint, so the two numbers stay tied together;
- assert the desktop `@media (min-width: 900px)` override still sets
  `bottom: 20px` (the desktop dock is unaffected).

The test must remain a plain `node` script with no new dependency and no DOM.

---

## 3. Files you may touch

- `pwa/index.html`
- `pwa/test-punkto-m8b-map-first.mjs`

Do not touch anything else. In particular do **not** change `pwa/app.js`,
`pwa/ui-map.js`, `pwa/core/explore.js`, `pwa/ui-board.js` or the CI workflow.

---

## 4. Definition of done

- Exactly these two files changed relative to your previous working-tree state
  (plus your previous, already-uncommitted M8B work).
- `node --check pwa/test-punkto-m8b-map-first.mjs` and
  `node --input-type=module --check < pwa/test-punkto-m8b-map-first.mjs` pass.
- `node pwa/test-punkto-m8b-map-first.mjs` passes with the new check included
  (paste the exact output, including the final summary line and the new pass
  count).
- `node pwa/test-punkto-m8-ux.mjs` still passes (paste the exact output).
- Paste the exact `git diff` of your two files.
- State explicitly that you did **not** commit, push, merge, deploy, create a
  PR, or write to any remote host.
