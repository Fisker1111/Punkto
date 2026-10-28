# CODEX_TASK_22 — STAGE 4 (real-PWA static acid test + evidence close-out)

Read `docs/CODEX_TASK_22.md` first (full contract), then `docs/CODEX_TASK_22_STAGE3.md`
(Stage 3 scope, already implemented in the working tree). Stage 3 MUST keep passing.

**Do not commit. Do not push. Do not deploy. Do not build or push any Docker image. Do not
touch any server.**

---

## Stage 4 goal

Close the last real acceptance gap: the browser E2E currently drives the **Punkti client
module** in a synthetic `acid.html` page. The Issue's hard acid test requires the
**actual Punkto PWA** to load, verify and **display** atoms from a **dumb static server**
with the Punkti daemon **stopped**.

Stage 3's own report (`docs/INTEGRATION_22.md` §5) currently marks acceptance criteria
**9, 10 and 11 as NOT RUN** because Playwright could not find a browser. That blocker is
now resolved — see "Playwright availability" below. Those three criteria must be
**re-run and updated**.

---

## Playwright availability (resolved — use this)

The host caches Chromium revision **1243**. Two Playwright versions exist in the npx
cache:

| Playwright | Path | Chromium revision |
|---|---|---|
| 1.63.0 | `/home/hermes/.npm/_npx/420ff84f11983ee5/node_modules/playwright/index.mjs` | **1243 (matches the cached browser)** |
| 1.64.1 | `/home/hermes/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs` | 1248 (NOT cached — fails) |

Run the E2E with:

```bash
PLAYWRIGHT_MODULE="file:///home/hermes/.npm/_npx/420ff84f11983ee5/node_modules/playwright/index.mjs" \
  node pwa/test-punkti-static-e2e.mjs
```

Stage 3's `pwa/test-punkti-static-e2e.mjs` has already been fixed to send a correct
`Content-Type` for `.js` files (browsers enforce strict MIME checking for ES module
imports; without it the module import fails). That fix is already in the working tree —
keep it.

The E2E script already supports `PLAYWRIGHT_MODULE`; do not add a committed
`node_modules`, do not add a bundler, do not add a `package.json` to the repo.

---

## S4.1 — Real-PWA static-only acid test

Add a new test (extend `pwa/test-punkti-static-e2e.mjs` with a third scenario, or add
`pwa/test-punkti-pwa-static-e2e.mjs` — your choice, but state which) that proves the
**real PWA application** works against a dumb static server.

Required assertions:

1. **Real app shell loads.** Serve the actual `pwa/` directory (not a synthetic page)
   with a plain Node `http` static server that declares correct MIME types.
2. **The Punkti daemon is NOT running.** Only the dumb static server serves the origin.
   The publication directory (materialised from
   `experimental/punkti-v0.6-publication/vectors.json` fixture `index`) is served at the
   **same origin** under the path the PWA expects for the publication.
3. **The PWA reads and displays valid atoms.** After load, the Text page shows at least
   one atom card derived from the publication (assert on real DOM: the feed list /
   `main-feed-list` contains a card, and/or the visible atom count in `#count-num` is
   `> 0`). Use the app's own DOM, not internal JS state.
4. **XY-prefix browsing works.** Drive the World-view scope control (`#world-xy-prefix`
   plus `#world-apply`) and assert the visible atom count changes consistently with the
   scope (e.g. a prefix that matches nothing yields `0` visible atoms; a matching
   prefix yields the same count as unfiltered). Assert the *outcome*, not just that a
   click happened.
5. **No dynamic read dependency.** Record **every** request the page makes and assert
   **no** request path contains `/pull`, `/sync` or `/push`. Also assert the page made
   **no** request to a node-only dynamic endpoint for reads (e.g. `/node/info` failure is
   tolerated — it is a status lookup, not a read — but record what was requested so the
   evidence is honest).
6. **Console errors.** Collect `pageerror` / console `error` events. Report them. Fail
   only on errors caused by the static-only path (e.g. a failed publication fetch, an
   uncaught module error). Map-tile network failures from the external tile server are
   expected in a sandbox and must be reported but not treated as a failure.

### Practical notes

* The PWA is a **vanilla ES-module** app served from `pwa/`. Its map layer needs
  MapLibre/deck.gl, which are **vendored locally** in `pwa/lib/` — no CDN needed.
* The PWA reads the publication from `window.location.origin + '/publication'`
  (see `pwa/app.js`, `NODE_URL` and `punktiClient.publicationBase`). So the dumb static
  server must expose the publication at `/publication` on the same origin as the app.
  Confirm the exact path by reading the code — do not guess.
* The PWA uses IndexedDB (Dexie, vendored) and `nacl.min.js` (vendored). It may require
  an identity only for **publishing**; reading must work without one.
* If the full app shell cannot be driven headlessly for a reason you cannot work around
  (e.g. the map requires a WebGL context unavailable in this environment), fall back to
  the largest honest subset and **state precisely what was and was not proven**. Do not
  fabricate a pass. Note that `chromium_headless_shell` is available, so WebGL may work
  via SwiftShader — check before giving up.
* Serve the PWA with `spa_fallback` semantics **off**; the app is a plain multi-file
  static app.

---

## S4.2 — Write-to-static round trip through the real PWA

The existing Stage 3 E2E proves the round trip at module level (`POST /submit` → node
validates → publication advances → static read sees the atom → duplicate submit is
idempotent). Keep that test.

Additionally, if feasible, extend it to submit **through the real PWA create flow**
(the create sheet in the UI). If the UI-driven publish path cannot be driven headlessly
for an honest reason, say so explicitly and keep the module-level round trip as the
evidence, clearly labelled as module-level rather than UI-level.

---

## S4.3 — Docker/E2E status

There is **no docker daemon on this host** (`docker` is not installed). The Docker/E2E
acceptance criterion therefore remains **NOT RUN (no docker daemon on the build host)**.
Do not fabricate Docker output. `scripts/acceptance_static_first.sh` (Stage 3) is the
operator-runnable script for it — verify it is **syntactically valid and coherent**
(`bash -n`, and read it end-to-end), and confirm it covers the Issue's Docker/E2E list:
build image, launch fresh node, browser smoke test, submit/read, restart container, data
still present, second node static-replicates, application logic stopped while the static
publication still serves, and amd64+arm64 build invocation. Fix any gap you find in the
script. Note that the script must not *claim* the browser smoke test is automated if it
is not — if it needs a human, say so in the script output.

---

## S4.4 — Update the integration report and evidence

1. Update `docs/INTEGRATION_22.md`:
   * §5 acceptance table — re-evaluate criteria **9, 10, 11** with the new real
     results. Replace every "NOT RUN (playwright unavailable)" with the actual
     **PASS / FAIL** and the correct evidence file. If any part of criterion 9 is still
     unproven (e.g. only module-level and not UI-level), state exactly that.
   * §2 (PWA redesign) — describe what a user actually sees now.
   * §6 — list the final evidence bundle.
   * §7 — refresh the cutover recommendation and the open-gates list.
2. Put the **raw command output** of every command you run under
   `docs/evidence/issue-22/` with descriptive filenames. Overwrite the stale
   `check-06b-static-e2e-nodepath.txt` blocker log with the resolved run, and keep the
   old one only if you rename it to reflect that it is the historical blocker (e.g.
   `check-06b-static-e2e-blocked-superseded.txt`).
3. `docs/INTEGRATION_22.md` must remain truthful: **no fabricated results**, and every
   NOT RUN must carry its concrete reason.

---

## S4.5 — Checks that must pass before you report done

```bash
cd /home/hermes/.hermes/kanban/workspaces/t_3d146aba/punkto

for f in pwa/*.js pwa/*/*.js; do node --check "$f" || exit 1; done
node --input-type=module --check < pwa/app.js

node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-slice5.mjs

PLAYWRIGHT_MODULE="file:///home/hermes/.npm/_npx/420ff84f11983ee5/node_modules/playwright/index.mjs" \
  node pwa/test-punkti-static-e2e.mjs

python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests

python3 -m punkti_node --check-config --config node-config.example.yml
PUNKTO_WEB_ROOT="$PWD/pwa" python3 -m punkti_node --check-config --config punkto-config.example.yml

bash -n scripts/acceptance_static_first.sh

for f in .github/workflows/*.yml *.yml; do
  python3 -c "import yaml,sys;yaml.safe_load(open(sys.argv[1]))" "$f" || exit 1
done
```

All must exit 0, except where the report explicitly marks a criterion NOT RUN with a
concrete reason.

---

## S4.6 — Report

1. Files changed/added/deleted.
2. Real output of every command in §S4.5.
3. The updated acceptance table.
4. Exactly what a human must still decide (design acceptance, Docker-daemon E2E,
   production cutover).
5. Confirmation: nothing committed, nothing pushed, no image built or pushed, no
   deployment, no server touched.

## S4.7 — Spec-first rule

If you find a genuine contradiction in the frozen normative contracts, **STOP and report
it with a concrete counterexample** instead of guessing. Do not change the frozen
protocol semantics.
