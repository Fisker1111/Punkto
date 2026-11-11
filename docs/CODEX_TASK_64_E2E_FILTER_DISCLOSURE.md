# Codex task — fix browser-e2e gate blocked by collapsed Advanced filters disclosure (CEO-OS #64)

## Status

ACTIVE.

Repository: `Fisker1111/Punkto`
Base branch: `fix/issue64-pwa-e2e-filter-disclosure` (branched from `origin/main` = `d2dabeb29abbc805bd8ade23a03c53aeb6591a15`, the merge commit of PR #154)

Read `AGENTS.md` before editing.

## Context

PR #154 (M8/M8B PWA UX) landed on `main` and changed `pwa/index.html`: the world-scope controls
`#world-xy-prefix`, `#world-z-min`, `#world-z-max`, `#world-apply`, `#world-clear` are now inside

```html
<details class="main-card ui-card">
  <summary>Advanced filters</summary>
  ...
</details>
```

The `<details>` is closed by default (correct UX: advanced filters stay collapsed).

The repository's browser E2E harness `pwa/test-punkti-static-e2e.mjs` still assumes the old flat
layout. In `realPwaStaticReadTest()` it does:

```js
await page.waitForSelector('#world-apply', { timeout: 15000 });
await page.click('#world-apply');
```

`#world-apply` is now inside a closed `<details>`, so it is not visible and Playwright times out.

Confirmed failure from the official image workflow run 43007555979
(https://github.com/Fisker1111/Punkto/actions/runs/43007555979, job `browser-e2e`,
head SHA `d2dabeb29abbc805bd8ade23a03c53aeb6591a15`):

```
page.waitForSelector: Timeout 15000ms exceeded.
  - waiting for locator('#world-apply') to be visible
    34 × locator resolved to hidden <button type="button" id="world-apply" class="btn btn-primary">Apply world scope</button>
    at realPwaStaticReadTest (pwa/test-punkti-static-e2e.mjs:234:18)
```

The `image` job was SKIPPED, so no image was published from that SHA.

## Goal

Make the browser E2E harness open the collapsed **Advanced filters** disclosure the way a real user
does, so the meaningful filter/scoping assertions still run and the hard publish gate can pass.

## Scope — allowed

Only the browser E2E harness file `pwa/test-punkti-static-e2e.mjs` may change, plus this task
file itself (`docs/CODEX_TASK_64_E2E_FILTER_DISCLOSURE.md`) if you want to record the outcome.

## Requirements

1. Before touching `#world-apply`, the harness must open the **Advanced filters** disclosure by
   clicking its `<summary>` — the real user interaction — and then assert that `#world-apply` (and
   `#world-xy-prefix`) are visible. Use a robust locator, e.g.

   ```js
   const filtersSummary = page.locator('#main-feed details')
     .filter({ hasText: 'Advanced filters' })
     .locator('summary');
   await filtersSummary.click();
   await page.waitForSelector('#world-apply', { state: 'visible', timeout: 15000 });
   ```

   Do NOT set `details.open = true` via `page.evaluate` — that bypasses the real interaction and
   would not exercise the disclosure the product actually ships.
2. Preserve every meaningful existing assertion: the baseline "cards > 0 or count > 0" wait, the
   `#world-xy-prefix = 'zzzz'` zero-scoped wait, the cleared-scope restore wait, the exact-identity /
   canonical-link / QR checks, the console-error tolerance, the legacy-path and publication-request
   checks, and the final assert block.
3. Do NOT weaken, skip, comment out or soften any assertion. Do NOT change timeouts to hide the
   problem. Do NOT add `test.skip`, `try/catch` swallowing, or `.catch(() => {})` around the
   disclosure interaction.
4. Do NOT change `pwa/index.html`, `pwa/app.js`, `pwa/ui-*.js`, any production code, any signed data,
   any config, DNS, MCP content or replication settings.
5. Do NOT reopen the Advanced filters panel by default in the product to placate the test. The
   collapsed-by-default UX is the approved behaviour and must stay.
6. The later `page.click('#world-apply')` calls (after `page.fill('#world-xy-prefix', 'zzzz')` and
   after clearing it) must still find the button visible. If the disclosure gets closed by a re-render
   during those steps, reopen it in the same realistic way — do not assume it stays open.

## Checks to run

```bash
node --check pwa/test-punkti-static-e2e.mjs
node pwa/test-punkti-static-e2e.mjs
```

The full harness must exit 0. If Playwright browsers or the pinned playwright package are missing
locally, install per the repo's CI setup (see `.github/workflows/` for the browser-e2e job: pinned
playwright package + `npx playwright install chromium` with `--with-deps` if needed) and still run
the harness to green before reporting.

Also run the PWA syntax checks listed in `AGENTS.md` if you touch anything besides the test file
(you should not).

## Stop condition / out of scope

- Do NOT commit. Do NOT push. Do NOT open a PR. Hermes commits, pushes and opens the PR.
- If the harness still fails for a reason unrelated to the disclosure (a product regression rather
  than a harness/UX mismatch), STOP and report the exact failure output instead of patching product
  code.
- Report: files changed, the exact diff hunks, the commands run, and the harness result (pass/fail
  with the final assertion output).
