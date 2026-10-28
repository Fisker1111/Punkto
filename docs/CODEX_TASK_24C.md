# CODEX TASK 24C — `/ai`: repair the shipped hostile harness and gate it in CI

**Status:** ACTIVE
**Base branch:** `origin/main` (merge commit `e4a37b1`, contains PR #119).
**Work branch:** `fix/ai-e3-followup` (already checked out in this directory; your earlier
Task 24B work is present as uncommitted changes in the working tree — keep it).

Do **not** commit and do **not** push. Hermes commits and pushes from its own shell.

Read `AGENTS.md` first. Do **not** modify the frozen modules `pwa/punkti/carrier.js`,
`pwa/punkti/spatial.js`, `pwa/punkti/reader.js`, `pwa/punkti/submit.js`, or any frozen
vector file.

---

## 0. What is broken, and why it matters

PR #119 was merged into `main`. Two CI gaps shipped with it:

**Gap 1 — a committed harness fails on `main`.**
`pwa/test-ai-hostile.mjs` asserts that the served `/ai` page contains the literal
`'not a complete view'`. The merged, E0-approved page (commit `a9b5004`) contains
`"The list is only a starting point, not a trust authority or a complete view of Punkto."`.
The literal `'not a complete view'` is **not** a substring of that sentence, so the harness
fails on `origin/main`:

```
AssertionError [ERR_ASSERTION]: required page text: not a complete view
    at file:///.../pwa/test-ai-hostile.mjs:118:13
```

This was never caught because **neither AI harness is wired into Pilot CI**. The
`Punkto image` workflow that does run them is triggered only on `v*` tags and
`workflow_dispatch` — never on a pull request. `pwa/test-ai-coldstart.mjs` and
`pwa/test-ai-hostile.mjs` are therefore unvalidated on every pull request.

**Gap 2 — the AI harnesses are not a merge gate.**
`.github/workflows/pilot-ci.yml` (job `PWA validation`) does not run any of the three
`/ai` harnesses.

---

## 1. Fix the broken literal in `pwa/test-ai-hostile.mjs`

The **page is the E0-approved artifact**; the test literal is the defect. Fix the *test*,
not the page.

* Replace the failing literal `'not a complete view'` with a literal that is actually
  present in the approved page and still asserts the same meaning — the bootstrap list is
  neither a trust authority nor a completeness claim. Use the exact substring
  `'not a trust authority or a complete view of Punkto'` (it is present verbatim in
  `pwa/ai.html`).
* Keep the separate existing literal `'not a trust authority'` as it is.
* Do **not** change any other assertion in the file, and do **not** change `pwa/ai.html` to
  satisfy the test. The page wording is founder-approved; the test was wrong.

Then verify the whole harness passes on the current working tree.

## 2. Gate the `/ai` harnesses in Pilot CI

In `.github/workflows/pilot-ci.yml`, in the existing `PWA validation` job, add a step that
runs all three `/ai` harnesses, in the same style as the existing steps:

```yaml
      - name: Punkti /ai machine entrance harnesses
        run: |
          node pwa/test-ai-coldstart.mjs
          node pwa/test-ai-hostile.mjs
          node pwa/test-ai-cli.mjs
```

Place it after the existing `Punkti 0.6 protocol/vector suites` step.

`pwa/test-ai-coldstart.mjs` and `pwa/test-ai-hostile.mjs` already exist on `main`.
`pwa/test-ai-cli.mjs` is created by Task 24B (it is currently in the working tree as an
untracked file) — include it in the step, since Task 24B's brief already requires the same
file to be added to `.github/workflows/punkto-image.yml` next to the two existing
harnesses.

Do **not** change any other job, step, trigger or permission in `pilot-ci.yml`.
Do **not** touch `.github/workflows/punkto-image.yml` — Task 24B already handled it.

**Important:** the harnesses must pass with the Node version CI uses (Node 22) as well as
locally. Do not introduce anything that depends on a newer Node feature. `pwa/test-ai-cli.mjs`
must not require network access.

## 3. Required checks (all must pass; report each result)

```bash
node pwa/test-ai-coldstart.mjs
node pwa/test-ai-hostile.mjs
node pwa/test-ai-cli.mjs
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-slice5.mjs
for module in pwa/*.js pwa/*/*.js; do node --check "$module"; done
node --input-type=module --check < pwa/app.js
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m punkti_node --check-config --config node-config.example.yml
PUNKTO_WEB_ROOT="$PWD/pwa" python3 -m punkti_node --check-config --config punkto-config.example.yml
```

Also confirm the Pilot CI YAML is still valid YAML (for example with
`python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/pilot-ci.yml'))"`).

## 4. Report

Report: files changed, each check with pass/fail, the exact replacement literal you used,
and confirmation that the three harnesses now run in the `PWA validation` job. Do not commit
or push.
