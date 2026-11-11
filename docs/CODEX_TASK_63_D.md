# CODEX TASK 63-D — addendum: the explore nudge must not blank out a known real place during a background resync

Repository: `Fisker1111/Punkto`
Branch: `feat/issue60-pwa-m8-ux` (HEAD is still `dfa29f1cbe753988300056ded01f7970cd400b22`
plus your uncommitted M8B work in the working tree)
Issue: https://github.com/Fisker1111/CEO-OS/issues/63

**Read first:** `docs/CODEX_TASK_63.md` (the normative M8B spec),
`docs/CODEX_TASK_63_B.md`, `docs/CODEX_TASK_63_C.md` (both already implemented in your
working tree), `pwa/app.js` (`refreshExploreNudge()`, `setSyncStatus()`,
`publicationReadState`), `pwa/core/explore.js`.

This addendum is normative and additive. If you believe any rule below is
contradictory or impossible, **stop and report** instead of silently choosing a
different design.

---

## 0. What Hermes measured in a real browser (read-only QA)

`pwa/app.js` currently renders the nudge like this:

```js
const html = publicationReadState === 'loading'
  ? '<p role="status">Loading published places…</p>'
  : publicationReadState === 'error'
    ? '<p role="status">Could not load published places. Try again.</p><button …>Retry</button>'
    : places.length ? explorePlacesHtml(places)
      : '<p role="status">No published places in this scope.</p>';
```

`setSyncStatus('syncing')` sets `publicationReadState = 'loading'`
(`pwa/app.js`: `publicationReadState = state === 'syncing' ? 'loading' : state;`),
and the sync engine runs every 30 s.

**Observed in Chromium (390×844, real read-only publication):** the nudge's place
button flickers out and back every sync cycle. Sampled 8× at 5 s intervals after
the page had fully loaded:

```
0 {"btn":true}   1 {"btn":true}   2 {"btn":true}   3 {"btn":true}
4 {"btn":false}  5 {"btn":false}  6 {"btn":true}   7 {"btn":true}
```

During the `false` samples the nudge reads "Loading published places…" and the
only way to reach the genuine published place is gone. That contradicts the
M8B goal that an unauthenticated visitor can "immediately find and open **one
genuinely published spatial place**" — the affordance must not blink out under
the visitor every 30 seconds. It also drops keyboard focus (the focused button
is removed from the DOM).

This is a defect of the M8B change itself, so M8B fixes it.

---

## 1. Required fix (minimal, inside `pwa/app.js` only)

Change the render precedence in `refreshExploreNudge()` so that **already known
real places keep rendering while a refresh is in flight**:

1. If `places.length > 0` → render `explorePlacesHtml(places)` **regardless of**
   `publicationReadState`. The known real place stays on screen, keeps focus and
   never blinks out during a background resync.
2. Else if `publicationReadState === 'loading'` → render the honest
   `<p role="status">Loading published places…</p>` state (unchanged wording).
3. Else if `publicationReadState === 'error'` → render the honest error line and
   the `data-action="retry-read"` Retry button (unchanged).
4. Else (no places, not loading, not error) → render
   `<p role="status">No published places in this scope.</p>` (unchanged).

Also keep the existing guard that avoids rewriting identical HTML:

```js
if (content.innerHTML !== html) content.innerHTML = html;
```

so a refresh that does not change the places does not touch the DOM at all and
cannot steal focus.

**Do not change** the rest of `refreshExploreNudge()`: the `hidden` computation
(`exploreDismissed || currentPage !== 'map' || hasOpenBoard()`), the
`frameInitialExplorePlace(primaryExplorePlace(places))` call, the
`data-action="explore-place"` / `data-action="dismiss-explore"` handling, the
`punkto.explored` persistence, or the wording of any string.

**Do not change** `setSyncStatus()`, `publicationReadState`, the sync engine, the
`sync-dot` classes, or anything outside `pwa/app.js`.

---

## 2. Required regression test

Extend `pwa/test-punkto-m8b-map-first.mjs` (do **not** create a second test
file). The renderer must become reachable from a test, so:

- Extract the nudge-body rendering into a small **pure** exported function in
  `pwa/app.js` — e.g. `export function exploreNudgeBodyHtml(places, readState)` —
  that returns exactly the HTML string described in §1. `refreshExploreNudge()`
  then calls it. Keep `refreshExploreNudge()`'s existing behaviour identical.
- The pure function must live in `pwa/app.js` and be exported from it.
  (`pwa/app.js` already imports from `pwa/core/explore.js`; do **not** move the
  function into `pwa/core/explore.js` — §3 restricts the files you may touch.)
- Add a check that:
  - with one known public place and `readState === 'loading'`, the rendered HTML
    still contains the place's `data-atom-id` and **does not** contain
    "Loading published places…";
  - with one known public place and `readState === 'syncing'`, same expectation;
  - with no places and `readState === 'loading'`, the HTML contains
    "Loading published places…" and no `<button data-action="explore-place"`;
  - with no places and `readState === 'error'`, the HTML contains the error line
    and a `data-action="retry-read"` button;
  - with no places and `readState === 'ok'`, the HTML contains
    "No published places in this scope.";
- The check must also assert the render still contains exactly one
  `data-action="explore-place"` button for one place.

**Important:** `pwa/app.js` imports browser-only modules (IndexedDB, the map,
`window`). If importing `pwa/app.js` from the plain-node test is not possible,
the test must instead exercise the pure function by extracting it in a way that
does not break the browser bundle. The simplest acceptable approach: put the
pure function in `pwa/app.js` and have the test import it **only if** that import
succeeds without side effects; if `import('./app.js')` cannot run under plain
node, then instead **move the pure function to `pwa/core/explore.js`** and export
it there (and re-export it from `pwa/app.js` if you like).

  Read the current `pwa/app.js` import graph before deciding. Choose **one**
  approach, implement it cleanly, and say in your report which one you chose and
  why. The requirement is: the test must run under plain `node` with no new
  dependency, and the browser behaviour must be unchanged.

---

## 3. Files you may touch

- `pwa/app.js`
- `pwa/test-punkto-m8b-map-first.mjs`
- `pwa/core/explore.js` **only** if — and only if — the plain-node import
  constraint in §2 forces the pure function to live there.

Do not touch anything else. In particular do **not** change `pwa/ui-map.js`,
`pwa/index.html`, `pwa/ui-board.js` or the CI workflow.

---

## 4. Definition of done

- `node --check pwa/app.js` and `node --input-type=module --check < pwa/app.js`
  pass (and the same for any new/changed module).
- `node pwa/test-punkto-m8b-map-first.mjs` passes with the new check included
  (paste the exact output, including the final summary line and the new pass
  count).
- `node pwa/test-punkto-m8-ux.mjs` still passes (paste the exact output).
- Paste the exact `git diff` of the files you changed.
- State explicitly that you did **not** commit, push, merge, deploy, create a
  PR, or write to any remote host.
