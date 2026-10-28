# CODEX_TASK_22 — STAGE 6 (stale deployment documentation + CI coverage of the new E2E)

Read `docs/CODEX_TASK_22.md` first (full contract), then the Stage 3/4/5 briefs.
Stages 3, 4 and 5 MUST keep passing.

**Do not commit. Do not push. Do not deploy. Do not build or push any Docker image. Do not
touch any server.**

---

## Stage 6 goal

Close the **documentation and CI-coverage gaps** left by retiring the legacy
two-container Docker architecture. The code and the canonical workflow are already
migrated; some *documentation* still describes the retired world as if it were current,
and the canonical workflow does not yet run the new browser E2E.

---

## S6.1 — `deploy/README.md` is stale (must be corrected)

Independent review found that `deploy/README.md` still describes the **retired**
architecture as if it were current truth. Stage 3 deleted the legacy workflows
(`.github/workflows/docker.yml` and `.github/workflows/node-image.yml`), retired the
`punkto-web` / `punkto-relay` images, and rewrote `deploy/docker-compose.yml` to the
single digest-pinned combined image. But `deploy/README.md` still says, verbatim:

* "Each node runs two containers managed by Docker Compose."
* A "How it works" table listing `web` → `ghcr.io/fisker1111/punkto-web` (Caddy) and
  `relay` → `ghcr.io/fisker1111/punkto-relay` (Python relay).
* "Building images locally" with `docker build -t punkto-web ./pwa` and
  `docker build -t punkto-relay ./relay`.
* "GitHub Actions — automated builds" claiming `.github/workflows/docker.yml` builds and
  pushes `:latest` on push to `main`, publishing `punkto-web` and `punkto-relay`.

**Every one of those statements is now false.** A file that tells an operator to build
images from a workflow that no longer exists is a real deployment hazard, and it
directly contradicts CEO-OS Issue #22 Phase 8 ("retire/quarantine legacy automatic
`punkto-web` + `punkto-relay` builds from the old architecture").

Required:

1. Rewrite the affected sections of `deploy/README.md` to describe the **current**
   single-image deployment:
   * one combined image (`ghcr.io/fisker1111/punkto`) hosting the PWA + the
     validator/submitter + the generated static publication;
   * the **one canonical workflow** is `.github/workflows/punkto-image.yml`;
   * **digest-pinned** deployment only — never a floating `:latest`;
   * the publication is served under `/publication` on the same origin as the PWA, so
     the PWA reads it statically with **no** dynamic read API;
   * the persistent `/data` volume holds the store **and** the publication, and
     survives restart.
2. Keep any still-true operational content (secrets handling, `.env` guidance, the
   `/config` + `/data` model, live-node tables, useful commands). Do not delete useful
   operator knowledge in the name of "the architecture changed" — **rewrite** it.
3. Where the legacy two-container setup genuinely still exists in the deployed fleet
   (e.g. historical `deploy/node1`, `deploy/node2` reference material), either update
   it to the single-image shape or clearly mark it as **historical / not the reference
   product**. Do not leave a reader guessing which is current.
4. State the rollback procedure in terms of **digest** pinning (an operator pins back
   to a previous reviewed digest), not a floating tag.

### Sweep the whole repo for the same class of staleness

Run a repo-wide search for the retired names and fix every *operative* (not historical)
occurrence:

```bash
grep -rn "punkto-web\|punkto-relay" --include='*.md' --include='*.yml' --include='*.yaml' \
  --include='*.sh' --include='*.ps1' . | grep -v '^./docs/CODEX_TASK_22'
```

For each hit, decide deliberately:
* **operative** (a live instruction telling an operator what to do) → update it;
* **historical** (a changelog entry, a past incident record, a retired-workflow
  statement) → leave it, but ensure it reads as history.

List every hit and the decision you made for it in the report. Do not silently delete
history.

---

## S6.2 — CI must run the new browser E2E

The canonical workflow `.github/workflows/punkto-image.yml` now runs the protocol
vector suites before publishing (Stage 3) — good — but it does **not** run
`pwa/test-punkti-static-e2e.mjs`, which is the test that actually proves the static-first
browser path. The Issue's Phase 8 says "syntax/unit/vector tests before image publish"
and Phase 9 requires the browser flows to be proven.

Add a **separate CI job** to `.github/workflows/punkto-image.yml` (a separate job, so a
browser-availability problem cannot silently become a publish blocker *or* be silently
skipped — decide and justify which, and make the choice explicit):

* install Playwright and its Chromium,
* run `node pwa/test-punkti-static-e2e.mjs`,
* and make the **publish** job depend on it appropriately.

Two acceptable designs — pick one and justify it:

1. **Hard gate**: the browser E2E job is a `needs:` dependency of the publish job, so a
   failing browser test blocks the image publish. Strongest conformance, but the publish
   now depends on Playwright browser download working in CI.
2. **Reported gate**: the browser E2E runs as its own job and the publish job depends on
   it only for the *protocol/vector* job; the browser job's result is surfaced in the
   workflow summary. Weaker, but browser availability cannot block a release.

Whatever you choose:

* the workflow MUST NOT publish `latest` from a prerelease/draft tag (already true —
  keep it);
* the workflow MUST record the published image **digest** (already added by Stage 3 —
  keep it);
* the job MUST be explicit in the workflow summary about whether it gated the publish.
* Playwright in CI: `npm install --no-save playwright@<version>` in the job, then
  `npx playwright install --with-deps chromium`, then run the test with
  `PLAYWRIGHT_MODULE` pointing at the installed package. Pin the Playwright version
  explicitly (do not use a floating `latest`). Note the host here proved
  **Playwright 1.63.0 ↔ Chromium revision 1243** and **1.64.1 ↔ 1248** must match —
  pick a version and let the workflow install the matching browser, so the mismatch
  failure mode cannot recur.
* Do **not** add a committed `node_modules`, a `package.json`, or a bundler to the
  repo.

Also make sure `pwa/test-punkti-static-e2e.mjs` degrades **honestly** in CI: if
Playwright or the browser is genuinely unavailable, the test must exit **non-zero** with
a clear message (so CI reports a failure), not exit 0 with a "skipped" message that
would read as a pass. State the behaviour you implemented.

---

## S6.3 — `pilot-ci.yml` and `deployment-verify.yml` still work

Stage 3 deleted two workflow files. Confirm the remaining workflows do not reference
removed files and do not fail because of the deletions:

* `pilot-ci.yml` checks a list of required Pilot files — confirm every entry still
  exists and that the list does not reference anything deleted by Stage 3/5.
* `deployment-verify.yml` — confirm it still validates what it should.
* Add the new Punkto 0.6 protocol suites to `pilot-ci.yml` so the PR gate covers the
  frozen contract, not just the legacy slice-5 helpers. The vector suites are pure Node
  and cheap — they belong in the PR gate.

Verify every command in these workflows by actually running the equivalent locally
(the YAML itself you can only lint — see §S6.5).

---

## S6.4 — Update the integration report

Update `docs/INTEGRATION_22.md`:

* §1 (legacy code removed / retained) — add the `deploy/README.md` correction and the
  repo-wide stale-reference sweep results.
* §4 — describe the CI changes: the new browser E2E job, the gating decision and its
  justification, and the Playwright/browser-revision pinning.
* §5 acceptance table — update the CI/cleanup rows to reflect reality.
* §6 — add the new evidence files.
* §7 — refresh the cutover recommendation and open gates.

---

## S6.5 — Checks that must pass before you report done

```bash
cd /home/hermes/.hermes/kanban/workspaces/t_3d146aba/punkto

for f in pwa/*.js pwa/*/*.js; do node --check "$f" || exit 1; done
node --input-type=module --check < pwa/app.js

node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-slice5.mjs
[ -f pwa/test-exact-identity.mjs ] && node pwa/test-exact-identity.mjs

PLAYWRIGHT_MODULE="file:///home/hermes/.npm/_npx/420ff84f11983ee5/node_modules/playwright/index.mjs" \
  node pwa/test-punkti-static-e2e.mjs

python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests

bash -n scripts/acceptance_static_first.sh

# YAML lint every workflow and example config
for f in .github/workflows/*.yml *.yml; do
  python3 -c "import yaml,sys;yaml.safe_load(open(sys.argv[1]))" "$f" || exit 1
done

# No operative reference to the retired images/workflows may remain
grep -rn "punkto-web\|punkto-relay" --include='*.md' --include='*.yml' --include='*.yaml' \
  --include='*.sh' --include='*.ps1' . | grep -v '^./docs/CODEX_TASK_22'
```

(The last grep is expected to still print **historical** hits — those must be reviewed
and justified in your report, not silenced.)

All must exit 0, except the final grep which is a review list, not a pass/fail gate.

---

## S6.6 — Report

1. Files changed/added/deleted.
2. The full stale-reference sweep: every hit and the decision made for it.
3. The CI design choice you made (hard gate vs reported gate) and why.
4. Real output of every command in §S6.5.
5. The updated acceptance table.
6. Confirmation: nothing committed, nothing pushed, no image built or pushed, no
   deployment, no server touched.

## S6.7 — Spec-first rule

If you find a genuine contradiction in the frozen normative contracts, **STOP and report
it with a concrete counterexample** instead of guessing.
