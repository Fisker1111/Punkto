# CODEX_TASK_60_C — M8 accessibility close-out: reduced-motion + no-location fallback evidence

Repo: `Fisker1111/Punkto`. Branch: `feat/issue60-pwa-m8-ux` (HEAD `e00ad6c`).
Issue: CEO-OS #60 (M8) · PR: Fisker1111/Punkto#154 (review-only, never merged/deployed here).

## Goal

The founder's approved-direction comment on CEO-OS #60 asks the review PR to
provide "accessibility/reduced motion and no-location fallback" evidence. The
branch already ships a global CSS `prefers-reduced-motion` rule
(`pwa/index.html`) and honours reduced motion in the two **viewport-padding**
`easeTo` calls (`pwa/ui-map.js`). It does **not** honour it in the **camera
animations** that this branch introduced or relies on:

- `pwa/ui-map.js` `flyToPlace(loc)` → `map.flyTo({ center, zoom: 16, duration: 1200 })`
  (used by `frameInitialExplorePlace()` — the M8B first-visit camera framing — and
  by `focusPunktoOnMap()`).
- `pwa/ui-map.js` pitch/bearing `easeTo({ pitch: 45, bearing: -10, duration: 800 })`
  and its reset `easeTo({ pitch: 0, bearing: 0, duration: 800 })`.
- `pwa/app.js` post-publish `map.flyTo({ center, zoom: max(getZoom(), 14) })`
  (no explicit duration; MapLibre default is animated).

Under `prefers-reduced-motion: reduce` these must not animate. Fix that, and
lock it with an automated regression test.

## Scope — allowed to change (nothing else)

- `pwa/ui-map.js`
- `pwa/app.js`
- `pwa/test-punkto-m8b-map-first.mjs` (add assertions to the existing suite)
- a **new** focused test file only if the existing suite is the wrong home; if
  you create one, it must be `pwa/test-punkto-m8-a11y.mjs` and it must be wired
  into `.github/workflows/pilot-ci.yml` in the `pwa-validation` job with a job
  step name starting `M8 accessibility regression suite`.
- `docs/CODEX_TASK_60_C.md` (this file) — you may append a short
  "Implementation record" section; do not rewrite the spec above.

## Scope — forbidden

- No protocol, crypto, signer, identity, IndexedDB-schema, carrier, sync,
  node, relay, Worker/MCP, Caddy/DNS or publish-API change.
- No new dependency, bundler or build step. No framework change. No visual
  redesign. Do not touch MapLibre/deck.gl vendored files (`pwa/lib/**`).
- No change to `pwa/index.html`, `pwa/ui-text.js`, `pwa/ui-board.js`,
  `pwa/core/**`, `pwa/sync/**` unless a line is strictly required for the
  reduced-motion fix — if you believe one is, stop and report instead.
- No deployment, no merge, no push to `main`, no write to any live node.
- Do not edit `docs/UX_AUDIT_60.md`, `docs/UX_CONCEPTS_60.html`,
  `docs/evidence/**`, `docs/CODEX_TASK_60*.md` (other than this file) or any
  file outside the allowed list.

## Normative requirements

1. **One helper, one truth.** Add a single small helper in `pwa/ui-map.js`,
   e.g. `export function prefersReducedMotion()` returning
   `!!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches`, and use
   it for **every** camera animation in that file. `pwa/app.js` must reuse the
   same helper (import it) rather than re-implementing the check.
   The existing two inline `window.matchMedia?.('(prefers-reduced-motion:
   reduce)').matches` reads in `pwa/ui-map.js` (the viewport-padding paths)
   must be replaced by the helper so there is exactly **one** implementation.
2. **Reduced motion ⇒ no animation.** When reduced motion is on:
   - `flyToPlace` must use `duration: 0` (or `jumpTo` semantics), never 1200.
   - The pitch/bearing `easeTo` calls must use `duration: 0`.
   - The post-publish `map.flyTo` in `pwa/app.js` must use `duration: 0`.
   - Normal motion (the default) must keep the **existing** durations exactly:
     `flyToPlace` 1200 ms, pitch/bearing 800 ms, post-publish flyTo unchanged
     (MapLibre default). Do not change the felt motion of the default path.
3. **Runtime change is honoured.** If the helper can be a live
   `MediaQueryList` query, a user toggling the OS setting must be respected
   without a reload; if you cannot do that cheaply, a plain query at call time
   is acceptable — state which you implemented. Either way the check must be
   evaluated **at animation time**, not cached at module load.
4. **No regression.** With reduced motion **off**, every existing behaviour and
   every existing test result must be identical. With reduced motion **on**,
   no animation duration above 0 may be passed to `flyTo`/`easeTo`.
5. **Tests.** Extend `pwa/test-punkto-m8b-map-first.mjs` (or the new file) with
   assertions that:
   - a reduced-motion media query makes every camera animation duration `0`
     (assert on the calls the code actually makes, via an injected/faked map
     object or by exporting a pure decision helper);
   - the default (no reduced motion) path keeps duration `1200` for
     `flyToPlace` and `800` for the pitch/bearing ease;
   - the helper reads the media query **at call time** (changing the fake
     between two calls must change the result).
   Follow the existing suite's style: plain `node` script, `check(name, fn)`
   helper, `PASS` lines and a final `N/N ... passed` summary, exit code
   non-zero on failure.
6. **Style.** Match the surrounding code: 2-space indent, single quotes,
   `const`/`let`, no semicolonless style, no new dependencies, no `console.log`
   noise left behind (temporary debug logs must be removed).

## Required checks before you stop

```bash
node --check pwa/ui-map.js
node --check pwa/app.js
node --input-type=module --check < pwa/app.js
node pwa/test-punkto-m8b-map-first.mjs
node pwa/test-punkto-m8-ux.mjs
node pwa/test-punkto-reply.mjs
node pwa/test-slice5.mjs
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-ai-coldstart.mjs
node pwa/test-ai-hostile.mjs
node pwa/test-ai-cli.mjs
node pwa/test-exact-identity.mjs
```

All must exit 0. Paste the **real** output in your final report.

## Commit

- One focused commit on `feat/issue60-pwa-m8-ux`, message
  `fix(pwa): honour prefers-reduced-motion in camera animations (CEO-OS #60)`.
- **Do not push.** The Hermes shell pushes (Codex has no usable git SSH in this
  environment). If committing fails with a read-only `index.lock` error, leave
  the changes staged/uncommitted and say so — the Hermes shell commits.

## Stop condition

Stop and report — do not improvise — if:

- the reduced-motion fix cannot be made without touching a forbidden file;
- any required check other than the new accessibility suite fails for a reason
  your change caused (report the exact output; do not weaken an existing test
  or a threshold to make it pass);
- the spec contradicts the code (quote the exact contradiction).

Do not merge, deploy, or open a PR.
