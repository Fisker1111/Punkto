# CODEX TASK 60-B — addendum: the focused test suite required by `docs/CODEX_TASK_60.md` §5

Repository: `Fisker1111/Punkto`
Branch: `feat/issue60-pwa-m8-ux` (already contains the M8 implementation, commit `46aafa4`)
Base: `main`
Issue: https://github.com/Fisker1111/CEO-OS/issues/60

**Read first:** `docs/CODEX_TASK_60.md` (the normative spec), `docs/UX_AUDIT_60.md`
(the Phase A audit), `AGENTS.md`, `PUNKTO_UI_PRINCIPLES.md`.

This document is normative and additive: it covers **only** the test work that
§5 of `docs/CODEX_TASK_60.md` requires and that commit `46aafa4` does not yet
contain. The implementation in `46aafa4` is accepted — **do not change it**,
except where a test proves it wrong (in that case: fix the implementation
minimally, say so explicitly in your report, and keep the change inside
`pwa/**`).

**There is no network in your sandbox.** Everything you need is in the repo:

- `pwa/tests/publication-live-60.json` — the live publication snapshot
  (15 real records) decoded with the repo's own `pwa/punkti/carrier.js`.
  Regenerable with `node scripts/decode-live-publication.mjs` (needs network —
  not needed by you).
- `pwa/core/read-state.js`, `pwa/sync/punkti-client.js`, `pwa/ui-text.js` —
  the modules under test.

If you believe a rule below is contradictory or impossible, **stop and report**
instead of silently choosing a different design.

---

## 0. What already exists (do not redo it)

Commit `46aafa4` already implements the three M8 improvements:

- `pwa/sync/punkti-client.js` — `mapRecordToAtom()` now reads `record.atom.refs`
  and sets `relation` / `parent_id` / `root_id` (MID form kept verbatim).
- `pwa/core/read-state.js` — new module with `trustLabel()`, `heightLabel()`,
  `placeHtml()`, `isQaRecord()`, `readStateHtml()`.
- `pwa/ui-text.js` — `boardReplies()` exported; `isRootAtom()` exported; the
  reply composer is gated on `hasIdentity`; the board detail shows the exact
  address via `placeHtml()`.
- `pwa/ui-board.js` — map sheet takes `hasIdentity`, back label
  `"← Back to map"`, and closing the sheet keeps the selection.
- `pwa/app.js` — the Text feed and the counts are derived from one atom set
  (`_mainFeedAtoms = enriched`, count = roots), the first-visit explainer
  (`#first-visit-explore`) is added, `Advanced filters` is demoted into a
  `<details>`, the read state is `loading`/`error` with a retry action, and
  the per-item button is now **"Open board"** and opens the board sheet.
- `pwa/index.html` — the mobile nav/panel/onboarding overlap fix.

**Your job: the tests.** Exactly the coverage list of §5.1 of the spec, plus
the end-to-end reply read-back of §5.

---

## 1. New focused test file(s)

Add **one or more** new files under `pwa/`, following the existing
`pwa/test-*.mjs` style — plain Node, `node:assert/strict`, no test framework,
no new dependency, no network, no browser. Name them so the purpose is
obvious, e.g. `pwa/test-punkto-m8-ux.mjs` (a sibling suite is fine too).

The tests must be **pure and DOM-light**. Where a behaviour is only reachable
through DOM wiring, extract the pure decision into a small exported helper
(you may add helpers to `pwa/core/read-state.js` or `pwa/ui-text.js` — keep
them exported and side-effect free) and unit-test the helper. **Do not build
a DOM test harness** and **do not add jsdom or any dependency**.

### 1.1 Reply relation mapping (spec §5.1 item 1)

Load `pwa/tests/publication-live-60.json` and drive
`mapRecordToAtom()` from `pwa/sync/punkti-client.js` over the real records.

Assert, at minimum:

1. The record with `mid` starting `punkti/0.6:e1865d1e` (the real reply to
   `u3butz7k9q_23`) maps to an atom with `relation === 'reply'`, and
   `parent_id` / `root_id` set.
2. That `parent_id` **keeps the full `punkti/0.6:` MID prefix verbatim** — it
   is NOT stripped. Assert the exact expected string
   (`punkti/0.6:19cf1ba8…`, the value present in the fixture's `refs` array),
   not just "starts with".
3. The parent record (`punkti/0.6:19cf1ba8…`) maps to a **root**: `relation`,
   `parent_id` and `root_id` are all unset.
4. The second real reply (`punkti/0.6:70e0da2f…` → `punkti/0.6:fc188702…`)
   maps the same way.
5. The `refs` source **wins** over a conflicting `payload.meta.relation`:
   construct a synthetic record that carries BOTH `refs: [{target, rel:'reply'}]`
   and `x` whose parsed JSON has `meta.relation = 'reply'` with a *different*
   `parent_id`; assert the resulting `parent_id` is the `refs` target.
6. A record with no refs maps to a root (no relation fields).

The fixture records carry `x` (raw payload string) and `x_json` (parsed
payload when it is JSON). `mapRecordToAtom()` expects the carrier record
shape — build the record as the reader would (`{ mid, h, atom: { x, refs } }`).
Read `pwa/sync/punkti-client.js` and `pwa/punkti/carrier.js` to get the exact
shape right; do not guess.

### 1.2 Trust label honesty (spec §5.1 item 2)

`trustLabel()` from `pwa/core/read-state.js`:

- `verification_state === 'VALID'` → a label that **contains** "Verified".
- a present but non-`VALID` state (e.g. `INVALID-provenance`) → the label
  must **not** contain "Verified"; it must say the signature was not verified.
- an atom with a `sig` but **no** `verification_state` → the label must **not**
  contain "Verified" (it must say "Signed" or equivalent).
- an atom with neither → "Unsigned".
- No label may claim the **author identity** is verified (assert the label
  does not contain "identity" / "author verified").

### 1.3 Floor vs ellipsoidal height (spec §5.1 item 3)

`heightLabel()` from `pwa/core/read-state.js`:

- an atom with `floor` → the label names that **real floor**;
- an atom with only an ellipsoidal height → the label must **not** present a
  floor number, and must name it as an absolute WGS84 ellipsoidal height;
- an atom with neither → an honest "unavailable" label.

### 1.4 Feed / count consistency (spec §5.1 item 4)

The top-bar count and the Text list must come from the **same** atom set. The
implementation detail in `pwa/app.js` is: `refreshUI()` sets
`_mainFeedAtoms = enriched` (all in-scope atoms) and the counts are the
**root** count of that set; the Text list renders the roots of that same set.

Test the pure part of this decision. Either:

- export a tiny helper from `pwa/app.js` is **not** possible (it is a browser
  entry point) — so instead test it through the module that owns the rule:
  `pwa/ui-text.js` exports `isRootAtom()`; and `renderTextFeed()` is DOM-bound,
  so the testable invariant is: *the number of root atoms in the feed set
  equals the number of cards the Text view would render for the "Visible"
  tab.* Implement that as a small pure helper (e.g. `visibleRootCount(atoms)`
  in `pwa/ui-text.js`) and use it in **both** `renderTextFeed()` and
  `refreshUI()` so the invariant is real, not just asserted. Then test it.
- Additionally assert with the real fixture: an atom whose coordinates lie
  outside any plausible map viewport is **still counted and still listed** —
  i.e. the feed is not viewport-scoped any more.

### 1.5 Reply grouping (spec §5.1 item 5)

Two atoms with the same `h`, one carrying a reply relation to the other, group
as **one board with one reply**:

- `boardReplies(root, atoms)` from `pwa/ui-text.js` returns exactly the reply
  for that root, and **not** the root itself.
- The reply is **not** rendered as an independent top-level card: the "Visible"
  tab's card set is the root set (use `isRootAtom()` / the helper from §1.4).
- Use the real fixture records (root `punkti/0.6:19cf1ba8…` / `h = u3butz7k9q_23`
  and its reply `punkti/0.6:e1865d1e…`) — assert the grouping holds for the
  **real** publication, not only for hand-written atoms.

### 1.6 Error / loading states (spec §5.1 item 6)

`readStateHtml()` from `pwa/core/read-state.js`:

- loading → a loading state (not an empty state);
- error → an **error** state that contains a **retry affordance**
  (`data-action="retry-read"`), and does not present itself as "nothing here";
- neither → an empty string (no state chrome).

Assert the error string mentions a way to try again and that the empty state
is not shown for an error.

### 1.7 Touch targets on the new/changed surfaces (small, in scope)

Measured in the browser on the M8 branch at 390×844 (and identical on live
`punkto.xyz` today), the interactive elements on the surfaces this branch
touched are **30 px tall**:

- the board-card action buttons in the Text feed (`Open board`, `Show on map`,
  `Copy exact link`, `Print this Punkti`) — `#main-feed-list button` → 30 px;
- the new first-visit buttons (`Explore published text`, `Dismiss`) inside
  `#first-visit-explore` — 30 px.

The Issue's acceptance criteria require **good touch targets**, and
`PUNKTO_UI_PRINCIPLES.md` sets a 44 px minimum for interactive controls.
The existing `#main-feed summary { min-height: 44px; }` rule in `pwa/index.html`
shows the intended pattern.

**Required change.** Raise these specific controls to at least **44 px** of
touch height, without changing their visual design language and without
breaking the desktop layout. Prefer a CSS rule scoped to these selectors
(e.g. in `pwa/index.html`) over per-element inline styles:

- `#main-feed-list .ui-btn` (board-card action buttons)
- `#first-visit-explore .ui-btn` (first-visit buttons)

Do **not** shrink any existing control to fix a layout problem, do not change
the `Text | Map | + | Settings` navigation model, and do not change the
bottom-dock geometry that §4.3 of the main spec already fixed.

### 1.8 The "Visible / Activity" tab switch is dead (pre-existing bug, in scope)

Measured on **live `punkto.xyz`** (so this is pre-existing, not a regression
from `46aafa4`) and still broken on the M8 branch: clicking the **Activity**
chip does nothing.

- Live, 390×844: after `document.querySelector('[data-tab=activity]').click()`,
  `#main-feed-heading` still reads `"Visible here"` and the chip's `active`
  class stays on **Visible** (`[true, false]`).
- Branch, 390×844: identical — heading stays `"Visible here"`.

**Root cause.** `pwa/ui-text.js` `initTextView()` attaches its click handler to
the feed list only:

```js
const list = document.getElementById('main-feed-list');
if (list) {
  list.addEventListener('click', (e) => {
    …
    const tabBtn = e.target.closest('[data-action="text-tab"]');
```

but the tab chips live **outside** `#main-feed-list` in `pwa/index.html`
(they are in the `.main-category-chips` block above it), so the click never
reaches the handler.

**Required change.** Make the **Visible / Activity** switch work:

- The handler must receive clicks on the chips (e.g. bind the listener to a
  container that contains both the chips and the list, or bind the chips
  directly). Do **not** introduce a second competing handler for the same
  chips — there must be exactly one source of truth for `_activeTab`.
- Clicking **Activity** must switch the heading to `Activity`, the subtitle to
  the activity wording, and the list to the activity set (roots **and**
  replies).
- Clicking **Visible** must switch back and show only roots.
- The `active` class and `aria-selected` on the two chips must follow the
  selected tab (`_syncTabUi()` already does this — make sure it is called).
- Keep the tab behaviour identical to the intent already written in
  `renderTextFeed()` (`'Activity'` / `'Visible here'` headings, the
  `' public activity items'` / `' public boards'` counts). Do not invent new
  copy.

This matters for M8: "Activity" is the only surface that shows the public
reply activity in the feed, and an honest read state is one of the three
selected improvements — a dead tab makes the reply stream invisible.

### 1.9 Run the new suite in CI (small, in scope)

The repo's `.github/workflows/pilot-ci.yml` runs on every pull request to
`main` and is the hard pre-deploy gate. It currently executes the PWA syntax
checks and the protocol suites, but it would **not** execute the new M8 suite,
so a future regression in the reply grouping / trust labels / count
consistency would not be caught by CI.

**Required change.** Add one step to the `pwa-validation` job in
`.github/workflows/pilot-ci.yml`, right after the existing PWA suite steps,
that runs the new M8 test file(s) with `node`. Keep it minimal — e.g.:

```yaml
      - name: M8 UX regression suite (reply grouping, trust labels, feed consistency)
        run: node pwa/test-punkto-m8-ux.mjs
```

Use the **actual** filename(s) you create. Do not reorder, remove or weaken any
existing CI step, and do not add a dependency, a browser or a network call to
CI. Do not add `pwa/test-punkti-static-e2e.mjs` to CI — it needs playwright,
which CI does not install, and it is deliberately out of scope.

---

## 2. End-to-end reply proof through the PWA client path (spec §5, last paragraph)

`pwa/test-punkto-reply.mjs` is the isolated end-to-end surface: it starts a
real local `punkti_node` on 127.0.0.1 with an isolated publication, submits a
signed reply, and re-reads it. It currently passes (8/8) — **keep it passing**
and **keep its loopback-only network guard intact**.

Extend it (or add a sibling suite) so that the published reply is **read back
through the PWA client path** (`pwa/sync/punkti-client.js` →
`mapRecordToAtom()` → `pwa/ui-text.js` `boardReplies()`) and asserted to be
grouped under its parent:

1. publish a root and a signed reply to it in the isolated fixture;
2. read the publication back through the Punkti client;
3. assert the reply atom has `relation === 'reply'` and a `parent_id` that
   matches the root's `atom_id`;
4. assert `boardReplies(root, atoms)` returns the reply.

Never write to a public node; never use a test key for a real write; every
HTTP request must stay on 127.0.0.1 (keep the existing guard and its
assertions).

---

## 3. Hard boundaries (unchanged from the spec)

- No change to the core signer, key management, or crypto primitives.
- No change to the Punkti L3/L4 protocol semantics, `parse_h`/`encode_h`,
  `format_z`/`parse_z`, the carrier wire format, or the `refs` encoding.
- No IndexedDB schema migration (`pwa/storage/db.js` `db.version(...)` must
  stay exactly as-is).
- No worker / node / relay / backend / Caddy / DNS / deployment change.
- No POST to `/submit` or to any node other than the loopback test node.
- Do not touch `pwa/ai.html`, `pwa/ai-first/`, `pwa/print-pdf.js`,
  `pwa/protocol/`.
- No new dependency, bundler, build step, or package-manager file.
- No `console.log` in production code paths.
- 2-space indent, single quotes, semicolons, ES modules with explicit `.js`
  import specifiers.

---

## 4. Verification you must perform (report with real output)

1. `node --check` on every file you add or change, plus
   `node --input-type=module --check < pwa/app.js`, `< pwa/ui-text.js`,
   `< pwa/ui-board.js`.
2. **All** existing suites must stay green, with real output pasted:
   `pwa/test-slice5.mjs`, `pwa/test-punkti-vectors.mjs`,
   `pwa/test-punkti-publication.mjs`, `pwa/test-spatial-xy-z.mjs`,
   `pwa/test-ai-coldstart.mjs`, `pwa/test-ai-hostile.mjs`, `pwa/test-ai-cli.mjs`,
   `pwa/test-exact-identity.mjs`, `pwa/test-punkto-reply.mjs`.
   `pwa/test-punkti-static-e2e.mjs` requires playwright, which is **not
   installed** in this environment — it fails with
   `Error: playwright unavailable: Cannot find package 'playwright'`. That is a
   pre-existing environment limitation, not a regression. Report it as such;
   do not try to install it and do not change the suite.
3. Your new test file(s), with real output.
4. `git diff --stat` and a list of the files you changed with one line each.

## 5. Commit

**Include these already-present, Hermes-authored files in your commit** — they
are the Phase A audit trail and the founder-requested design artifacts for this
Issue, and they are already staged in the working tree:

- `docs/UX_AUDIT_60.md` (Phase A audit — do not edit it)
- `docs/CODEX_TASK_60.md` (the original normative spec — do not edit it)
- `docs/CODEX_TASK_60_B.md` (this addendum — do not edit it)
- `docs/UX_CONCEPTS_60.html` (the three wireframe-level UX concepts with
  trade-offs, requested in the founder's 2026-11-10 checkpoint comment — do
  not edit it)
- `docs/evidence/issue-60/*.png` (before/after browser screenshots: mobile
  first-visit map, mobile Text tab, branch first-visit Text, branch board
  thread, branch map, branch desktop — do not edit them)

Your own work, on top of that:

- the new test file(s) under `pwa/`
- the minimal helper extraction they need in `pwa/**`
- the touch-target CSS (§1.7) and the tab-handler fix (§1.8) in
  `pwa/ui-text.js` / `pwa/index.html`
- the one CI step (§1.9) in `.github/workflows/pilot-ci.yml`

**Do not** modify `pwa/tests/publication-live-60.json`, and **do not** amend
`46aafa4`.

One focused commit on `feat/issue60-pwa-m8-ux`:

```
test(pwa): M8 focused UX regression suite over the live publication fixture (CEO-OS #60)
```

(If you also touched `pwa/ui-text.js` / `pwa/index.html` /
`.github/workflows/pilot-ci.yml` for §1.7–§1.9, say so in the commit body —
the subject stays as given.)

If the sandbox cannot write the git index (read-only `.git/worktrees` →
`index.lock: Read-only file system`), that is expected: leave the changes in
the working tree, report the exact file list and the diffstat, and say clearly
that the orchestrator will commit. Do not try to work around it and do not
change git config.
