# CODEX TASK 24D — `/ai`: reproducible staging-page renderer for E3

**Status:** ACTIVE
**Base branch:** `origin/main` (merge commit `e4a37b1`, contains PR #119).
**Work branch:** `fix/ai-e3-followup` (already checked out in this directory; the Task 24B
and 24C changes are present as uncommitted working-tree changes — keep them).

Do **not** commit and do **not** push. Hermes commits and pushes from its own shell.

Read `AGENTS.md` first. Do **not** modify the frozen modules `pwa/punkti/carrier.js`,
`pwa/punkti/spatial.js`, `pwa/punkti/reader.js`, `pwa/punkti/submit.js`, or any frozen
vector file. **Do not modify `pwa/ai.html` at all** — it is the E0-approved, founder-reviewed
production artifact and must stay byte-identical to `origin/main`.

---

## 0. Why this exists

`pwa/ai.html` is founder-approved and its commands are deliberately **literal against
production** (`https://punkto.xyz/nodes.json`, `ORIGIN='https://punkto.xyz'`). The founder
has stated:

> a staging deployment of this exact production page would still point at `punkto.xyz`;
> E3 must use a staging-specific page/config so autonomous agents do not accidentally
> write production.

The E3 cold-start test therefore needs a **staging-specific copy of the same page** that
points only at the isolated test node (for example `https://test2.punkto.xyz`). Today that
copy can only be made by hand, which is not reproducible and not auditable.

This task adds a small, deterministic renderer so a staging copy is a one-command,
reviewable deployment step. It must not change the production page.

---

## 1. Add `tools/render_ai_page.py`

A small, dependency-free Python 3 script (standard library only — the repo already has
`tools/dmi_station_atom.py` and `tools/punkto-keygen-v0.1.py` in a similar style).

Usage:

```bash
python3 tools/render_ai_page.py --source pwa/ai.html --origin https://test2.punkto.xyz --output /path/to/ai.html
```

Behaviour:

* `--source` (default `pwa/ai.html`), `--origin` (required), `--output` (required) are the
  only arguments. Also support `--check` mode: render in memory, compare against `--output`
  if it exists, and exit non-zero with a clear message when the file on disk differs.
* The renderer replaces **every** occurrence of the production origin literal
  `https://punkto.xyz` in the source with the `--origin` value. The production origin
  literal is a single constant in the script (e.g. `PRODUCTION_ORIGIN = "https://punkto.xyz"`).
* `--origin` must be an absolute `http://` or `https://` URL with **no trailing slash** and
  no path component. Reject anything else with a clear error and a non-zero exit code.
* After rendering, the script must verify that the output contains **no** occurrence of
  `https://punkto.xyz` and at least one occurrence of the target origin. If either check
  fails, exit non-zero and do not write the output file.
* Write the output file atomically (write to a temporary file in the same directory, then
  `os.replace`).
* Print a one-line summary to stdout, for example:
  `rendered 8 origin replacements from pwa/ai.html to https://test2.punkto.xyz -> /path/to/ai.html`
* Exit code 0 on success, non-zero on any error. Errors go to stderr.

**Do not** add HTML templating, placeholders, JS, or any transformation other than the
origin substitution. The rendered page must be byte-identical to the source except for the
origin literal.

**Do not** hardcode a second origin, a node name, or a hostname. The only configured value
is the origin passed on the command line.

## 2. Add `tools/test_render_ai_page.py`

A unit test for the renderer, in the style of the existing `tools/test_dmi_station_atom.py`
(unittest). It must cover:

* a successful render replaces every production-origin occurrence and leaves no production
  origin in the output;
* the output is byte-identical to the source except for the substituted origin;
* a non-absolute origin is rejected; an origin with a trailing slash is rejected; an origin
  with a path is rejected;
* an output path in a non-existent directory fails cleanly (non-zero exit) instead of
  raising an unhandled traceback;
* `--check` succeeds when the on-disk file matches and fails when it does not.

Run it with `python3 -m unittest tools.test_render_ai_page` (or `python3 tools/test_render_ai_page.py`
if that is the style that works from the repo root — check the existing test file first and
match it).

## 3. Wire the new test into CI

`.github/workflows/punkto-image.yml` already runs the Python test files in a loop. Check the
exact glob it uses and make sure `tools/test_render_ai_page.py` is picked up by it. If the
existing glob does not cover `tools/test_*.py`, extend the glob minimally so it does — do not
restructure the step. Report exactly what you changed and why.

Do **not** touch `.github/workflows/pilot-ci.yml` — Task 24C already added the `/ai` harness
step there.

## 4. Documentation

Add a short section to `docs/AI_ENTRANCE.md` (it exists on `main` and documents the `/ai`
entrance) describing the staging-page procedure in two or three sentences plus the command.
State plainly that the production page is unchanged and that the renderer only substitutes
the origin so a staging deployment cannot write to production. Do not rewrite the rest of
that document.

## 5. Required checks (all must pass; report each result)

```bash
python3 -m unittest tools.test_render_ai_page
python3 tools/render_ai_page.py --source pwa/ai.html --origin https://test2.punkto.xyz --output /tmp/render-ai-check.html
grep -c "punkto.xyz" /tmp/render-ai-check.html; echo "exit=$?"
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
node pwa/test-ai-coldstart.mjs
node pwa/test-ai-hostile.mjs
node pwa/test-ai-cli.mjs
```

The `grep -c` command must report **0** occurrences of `punkto.xyz` in the rendered file
(note: `grep -c` exits 1 when the count is 0, so report the printed count, not the exit
status). If the count is not 0, the renderer is wrong — fix it.

## 6. Report

Report: files added/changed, each check with pass/fail, the exact command line an operator
uses to produce a staging `/ai` page, and confirmation that `pwa/ai.html` is byte-identical
to `origin/main` (`git diff --stat origin/main -- pwa/ai.html` must be empty). Do not commit
or push.
