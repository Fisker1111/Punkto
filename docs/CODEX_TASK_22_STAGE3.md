> Historical pre-correction material. Spatial rules below are superseded by the
> [2026-10-29 v0.6 correction](https://github.com/punkti-org/punkti/blob/47537960166e33ed806a4349b81b6a54c5ab3e00/Punkti-v0.6.md):
> every record requires canonical XY_Z; empty/missing/null/malformed h is
> INVALID-structural, and the removed publication key `~` is invalid.
> Earlier permissions for empty addresses and reserved-key routing below are
> historical only, not the current contract. Original evidence is retained.

# CODEX_TASK_22 — STAGE 3 (PWA redesign, Docker conformance, CI rationalization)

Read `docs/CODEX_TASK_22.md` first (full contract + acceptance criteria), then this
file (Stage 3 scope). Stages 1 and 2 are already landed on this branch and MUST keep
passing.

**Do not commit. Do not push. Do not deploy. Do not touch any server. Do not build or
push any Docker image — Docker is not available on this machine.**

---

## Stage 3 goal

1. The PWA **reads** Punkti from the static publication (no `/pull`, no `/sync`), and
   **publishes** through the node's `/submit`.
2. The PWA is **redesigned** around that architecture — not merely re-skinned.
3. The **placement / Z UX** is corrected (Punkti Z = WGS84 ellipsoidal height; Punkto
   floor / height-above-ground = optional Layer-4 metadata).
4. The **one-image Docker** distribution serves PWA + node + publication from one
   origin, survives restart, and works under arbitrary branding.
5. **CI is rationalized** to one canonical combined-image workflow.

---

## S3.1 — PWA read path becomes static-first

The current PWA reads through `pwa/sync/punkti-client.js` (`/pull`) and writes
through `/push`. That is the legacy dynamic path and MUST be replaced for reads.

Required:

1. **Replace the read path.** `pwa/app.js` MUST obtain atoms from the static
   publication via `pwa/punkti/reader.js` (Stage 2). The reader's base URL is the
   publication's static path on the same origin (the node serves it under its
   configured `publication.serve_prefix`; default `/publication`).
2. **Remove the dynamic read dependency.** After this change the browser MUST NOT
   issue `/pull`, `/sync` or `/push` requests during a read. `pwa/sync/punkti-client.js`
   and `pwa/sync/sync-engine.js` are legacy: **delete them** if nothing else needs
   them, or reduce them to the minimal node-info/health helper the Settings panel
   actually uses. Do not leave a dead dynamic-read client in the tree.
   (`pwa/test-punkti-client.mjs` currently fails because that client emits the old
   12-char geohash `h` — after this change it should either be removed together with
   the client, or updated to the frozen carrier. State which you did.)
3. **Write path uses `/submit`** via `pwa/punkti/submit.js` (Stage 2). The create
   flow MUST publish through `/submit` and MUST surface the node's clear rejection
   reasons in the UI.
4. **Layer-4 opacity.** The Punkto payload `x` stays opaque Layer-4 content. The
   browser MUST NOT interpret `x` as protocol, and MUST NOT derive L3 spatial truth
   from it.
5. **MID as exact identity.** Where the UI needs an exact Punkti object/link
   identity, use the record's MID (`punkti/0.6:<64 hex>`). Do **not** keep
   `p:<12-char-3D-geohash>` as a second quasi-protocol spatial identity in the 0.6
   path. (The frozen v0.5.1 `p:` form stays in the legacy code as a frozen
   compatibility form; it must not be the 0.6 identity.)
6. Keep the existing IndexedDB store (`pwa/storage/`) as the **local cache** of
   what was read from the static publication. The static read is the source of
   truth; the cache is a cache.

---

## S3.2 — PWA redesign (Phase 6)

This is a **redesign**, not a skin change. The current UI is a Text/Map pair driven by
a dynamic sync feed.

Design goals (from the Issue):

* clean, fast **world/spatial browsing** — preserve the spatial direction, do not
  regress to a feed;
* an **obvious distinction** between "browse static Punkti" and "publish through a
  node";
* **minimal protocol jargon** in normal UX (MID, R digest, XY_Z, publication seq
  belong in a technical/debug view, not in the primary flow);
* a reusable Punkti client module independent of Punkto UI (already true —
  `pwa/punkti/` must stay UI-independent);
* a **technical/debug view** exposing MID, R digest, XY_Z, publication source and
  verification status;
* **mobile/browser first**;
* **no AI dependency**, **no mandatory account or central service**.

Required concrete outcomes:

1. A **World view** that browses the static publication spatially: XY-prefix
   navigation (drill down by geohash prefix) and exact-decimal Z filtering, driven
   by the reader's scope support.
2. A **Publish** flow that is clearly separate from browsing: it talks to a node via
   `/submit`, shows the resulting address/publication state, and reports rejections
   clearly.
3. A **technical view** (Settings → technical/debug) showing, per atom:
   MID, SHA256(R), `h` (XY_Z), the publication base URL it came from, its
   verification state, and the publication `seq`/`head`.
4. The primary UX MUST NOT show protocol jargon. Keep it in the technical view.
5. The UI MUST NOT introduce new Layer-3 semantics. Layer-4 additions (floor,
   height-above-ground, category, building/floor metadata) are allowed and MUST be
   visually and structurally separated from `h`.
6. Respect `PUNKTO_UI_PRINCIPLES.md` and `AGENTS.md` where they do not conflict with
   this brief. Do not replace MapLibre/deck.gl.

`pwa/index.html`, `pwa/ui-*.js`, `pwa/app.js`, `pwa/core/`, `pwa/storage/` are in
scope. Keep the module boundaries (`AGENTS.md` "Current UI module ownership").

---

## S3.3 — Placement / Z UX correction (Phase 5)

The current create flow conflates "metres above ground / floor" with Punkti Z.

Required:

1. **Punkti Z = WGS84 ellipsoidal height in metres** (canonical signed decimal).
   It is a Layer-3 spatial address component.
2. **Punkto floor / height-above-ground = optional Layer-4 UX metadata.** It is
   stored in the opaque `x` payload, never in `h`.
3. Define and implement **how the browser derives or requests an ellipsoidal Z**:
   * a device geolocation fix reports an **ellipsoidal** height in modern browser
     geolocation APIs (`altitude` is metres above the WGS84 ellipsoid);
   * when the fix reports **geoid-relative** height instead (older/other APIs), the
     UI MUST say so and let the user supply or confirm an ellipsoidal Z — it MUST
     NOT silently store a relative height as `h`'s Z;
   * when no height is available at all, the UI MUST let the user enter Z
     explicitly, or publish **unanchored** (`h = ""`) — and MUST NOT invent a Z.
4. Negative, decimal and high Z MUST be accepted where protocol-valid (no
   artificial `-500..8500 m` restriction, no fixed decimal-place cap beyond the
   canonical/length rules).
5. The create UI MUST show the resulting `h` (XY_Z) plainly, and MUST make clear
   that the Z shown is an ellipsoidal height and that floor/height-above-ground is
   separate metadata.
6. The map MUST render the atom at the correct 3D position derived from the decoded
   XY + Z (the existing deck.gl layers already take an altitude; adapt them to the
   XY_Z-derived value rather than the legacy interleaved geohash).

---

## S3.4 — One-image Docker distribution (Phase 7)

The repo already has a combined `Dockerfile` (PWA + Punkti node) used by
`.github/workflows/punkto-image.yml`. Extend it, do not add a second image.

Required:

1. The one image hosts: the **Punkto PWA** + the **validator/submitter** + the
   **generated static Punkti publication**.
2. The publication is served from the **same origin** as the PWA under ordinary
   static paths, so the PWA reads it through the same origin (no CORS, no second
   host, no CDN requirement).
3. **No dynamic read API is required for correctness.**
4. The publication/store data lives on a **persistent volume** and survives a
   container restart.
5. An operator can **disable the UI** and still serve/replicate Punkti (the `web.enabled`
   flag must not disable publication serving).
6. The same image works under **arbitrary node/domain branding and configuration**
   (no baked-in domain), and requires **no Cloudflare/CDN**.
7. The image MUST NOT contain secrets. Never bake keys or credentials into the image.

**Docker is not installed on this machine.** You therefore CANNOT build the image
here. Do:
* make the Dockerfile + compose changes correctly and reviewably;
* add a **runnable** conformance script that an operator with a docker daemon runs
  (`scripts/acceptance_static_first.py` or `.sh`) — the script must perform the
  Phase 9 Docker/E2E checks: build image, launch fresh node, browser smoke test,
  submit/read, restart container, data still present, second node static-replicates,
  application logic stopped while the static publication still serves, and
  amd64/arm64 build invocation;
* mark the Docker-daemon-dependent acceptance criteria as **NOT RUN (no docker
  daemon on the build host)** in the evidence report. **Never fabricate Docker
  output.**

---

## S3.5 — CI rationalization (Phase 8)

Current workflows: `docker.yml` (legacy `punkto-web` + `punkto-relay` — the OLD
architecture), `node-image.yml` (node-only image), `punkto-image.yml` (combined
single-image), `pilot-ci.yml`, `deployment-verify.yml`.

Required end state:

1. **Exactly one canonical combined-image workflow** for the reference product.
2. The legacy `punkto-web` / `punkto-relay` automatic builds are **retired or
   quarantined**: `docker.yml` MUST NOT keep publishing `latest` from an unrelated
   legacy path. Either delete it, or convert it to `workflow_dispatch`-only with a
   clear "LEGACY — not the reference product" banner and no automatic `latest`.
   Prefer a clear, deliberate choice and say which you made and why.
3. `node-image.yml`: keep only if it is still a supported artifact. If the node is
   now always shipped inside the combined image, retire it. If kept, it MUST NOT
   publish `latest` from a prerelease tag and MUST run the tests first.
4. **Digest pinning/review for deployment**: the workflow MUST record the image
   digest it published, and the deployment documentation MUST pin by digest, never
   by a floating tag. Update `DEPLOYMENT_*.md`, `docs/single-image*.md` and the
   compose examples accordingly.
5. **linux/amd64 AND linux/arm64** are both built.
6. **JS syntax + unit + vector tests MUST run before any image publish** — the
   workflow MUST run `node pwa/test-punkti-vectors.mjs`,
   `node pwa/test-punkti-publication.mjs`, the PWA syntax checks and the Python node
   suite **before** the build/push step. A failing test MUST block the publish.
7. The workflow MUST NOT publish `latest` from a prerelease/draft tag.
8. `pilot-ci.yml` and `deployment-verify.yml` must keep working; update any file
   lists they check so they do not fail on removed/renamed files.

---

## S3.6 — Browser E2E (Playwright)

Create `pwa/test-punkti-static-e2e.mjs` — a **real browser** test (Playwright) that
proves the acceptance criteria that only a browser can prove:

1. **Static-only acid test**: serve ONLY the publication directory with a dumb static
   server (`node`'s `http` module serving a directory — NOT the node daemon), with
   the source Punkti daemon **stopped**; load the PWA in Chromium; the browser reads,
   verifies and displays valid atoms; XY-prefix browsing works.
2. **No `/pull` and no `/sync`**: record every request the page makes; assert that
   **no** request path contains `/pull` or `/sync` (and none to `/push`).
3. **Write-to-static round trip**: browser creates a correct XY_Z record → `POST
   /submit` → the node validates and persists → the publication root advances only
   after the immutable objects exist → the browser sees the new atom through the
   static read path → a duplicate submit is harmless.

Implementation notes:

* Playwright is available via `npx playwright` (v1.64.1) and Chromium is already
  cached at `~/.cache/ms-playwright/chromium-1243`. If the `playwright` npm package
  is not importable, `npm install --no-save playwright@1.64.1` in a scratch dir and
  point `NODE_PATH` at it, or drive Chromium directly over CDP — but do NOT add a
  committed `node_modules` and do NOT add a bundler to the repo.
* If Playwright cannot run in this environment at all, write the test script so it
  is runnable, and report the browser criteria as **NOT RUN (playwright unavailable)**
  with the exact error. Do not fake a pass.

---

## S3.7 — Integration report and evidence

Write `docs/INTEGRATION_22.md` (see `docs/CODEX_TASK_22.md` §6 for the required
content) and put raw command output under `docs/evidence/issue-22/`.

The report MUST contain:

* **Legacy code removed / retained**, file by file, with the reason for each.
* The **PWA redesign** summary (what the user sees changed).
* The **placement/Z UX** explanation (see S3.3).
* An acceptance table for every criterion in `docs/CODEX_TASK_22.md` §4 with
  **PASS / FAIL / NOT RUN (reason)**.
* The **production cutover recommendation** and the explicit list of gates still
  open (founder approval of the design, Docker-daemon E2E on an operator host,
  amd64/arm64 build verification, rollback/volume verification, etc.).

---

## S3.8 — Checks that must pass before you report done

```bash
for f in pwa/*.js pwa/*/*.js; do node --check "$f" || exit 1; done
node --input-type=module --check < pwa/app.js
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-punkti-static-e2e.mjs      # or report the exact blocker
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests
python3 -m punkti_node --check-config --config node-config.example.yml
python3 -m punkti_node --check-config --config punkto-config.example.yml
```

Plus a **YAML lint** of every workflow and example config you touched
(`python3 -c "import yaml,sys;yaml.safe_load(open(sys.argv[1]))" <file>`).

All must exit 0, or the failing one must be reported with its exact output and an
explicit reason (e.g. "no docker daemon on this host").

---

## S3.9 — Report

1. Files changed/added/deleted.
2. Real output of every command in §S3.8.
3. The acceptance table from `docs/CODEX_TASK_22.md` §4 with PASS / FAIL / NOT RUN.
4. What a human must still decide (design acceptance, cutover).
5. Confirmation: nothing committed, nothing pushed, no image built or pushed, no
   deployment, no server touched.
