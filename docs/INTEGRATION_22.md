# INTEGRATION_22 — Stage 6 integration report

Status: implementation complete in working tree (no commit/push/deploy).

## 1) Legacy code removed / retained

### Removed
- `.github/workflows/docker.yml` — retired legacy dual-image (`punkto-web`/`punkto-relay`) publish path to enforce one canonical combined-image workflow.
- `.github/workflows/node-image.yml` — retired node-only image workflow; combined image is the reference artifact.
- `pwa/test-punkti-client.mjs` — removed with legacy `/pull`-style browser-client test coverage.

### Stage 6 stale-reference corrections
- `deploy/README.md` rewritten to current single-image truth: one combined `ghcr.io/fisker1111/punkto` image, digest-pinned deployment, `/publication` static read path, `/data` persistence model, and canonical workflow `.github/workflows/punkto-image.yml`.
- Operative stale reference fixed in `docs/fresh-install-ubuntu.md` (`docker compose ps` expected output now shows one combined image/container).
- Repo-wide `punkto-web|punkto-relay` sweep reviewed hit-by-hit; only historical evidence/changelog/legacy references were retained as historical records.

### Stage 6 stale-reference sweep (full decisions)
- `CHANGELOG.md` (2 hits): historical changelog entries; retained unchanged.
- `relay/README.md` (5 hits): legacy relay-v0.1 standalone documentation; retained as historical/legacy reference.
- `docs/launch-candidate-checklist.md` (2 hits): dated canary evidence section (`2026-06-22`); retained as historical snapshot.
- `docs/pre-release-step-plan.md` (7 hits): dated prerelease execution transcript for older architecture; retained as historical record.
- `docs/single-image-deployment.md` (3 hits): explicit rollback notes that reference legacy containers as rollback artifacts; retained because they are clearly labeled `Legacy containers`.
- `docs/INTEGRATION_22.md` (2 hits): explicit documentation of retired dual-image path and this sweep itself; retained as intentional historical/meta references.
- `punkto.identity.md` (1 hit): protocol-history note (`punkto-relay v0.2+`) in identity history context; retained as historical narrative.
- `deploy/README.md` (5 hits before Stage 6): operative/stale deployment guidance; rewritten to current single-image architecture.
- `docs/fresh-install-ubuntu.md` (2 hits before Stage 6): operative/stale expected container output; updated to single combined image/container output.

### Retained (with role)
- `pwa/sync/sync-engine.js` — retained as scheduling/orchestration only; no protocol semantics, no `/pull` dependency.
- `pwa/sync/punkti-client.js` — retained but rewritten as a static-publication read + `/submit` write adapter.
- Native node mesh endpoints (`/pull`, `/push`, `/sync`) — retained for node-to-node compatibility; browser read path no longer depends on them.
- Legacy `p:` helpers/paths (`pwa/protocol/punkto-id.js`, `/p/<p:...>` parsing, `decodeAtomLocation` fallback) — retained as frozen v0.5.1 compatibility input only; not used as 0.6 exact identity.

## 2) PWA redesign summary (user-visible)

- The real app shell (`index.html`) now boots from a plain static origin and pulls verified Punkti records from `/publication`.
- Text view shows publication-backed cards and the visible counter without requiring `/pull` or `/sync` browser reads.
- World scope controls (`XY prefix`, optional `Z min/max`) change visible results in the live UI: unmatched scope resolves to zero, clearing scope restores visible publication records.
- Publish behavior remains explicit `/submit` to node; technical/debug panels still surface publication `seq/head`, MID and SHA256(R).
- Primary UX remains protocol-light while technical/debug keeps protocol identifiers for auditability.

## 3) Placement / Z UX correction

- Punkti `h` now uses `h=<xy>_<z>` (required for every record) in the submit path.
- Create modal now has explicit **ellipsoidal Z (WGS84)** input; the historical unanchored toggle is removed.
- Publish blocks if a real ellipsoidal Z is missing (no invented Z).
- Floor/height-above-ground remain Layer-4 metadata inside payload `x` (`meta.floor`, `meta.height_above_ground_m`) and are not used as Layer-3 truth.
- Map altitude rendering now consumes decoded `h`-derived altitude from cached atom records (negative values accepted; no forced non-negative clamp).

## 3.5) Exact identity model (Stage 5)

- MID (`punkti/0.6:<64 lowercase hex>`) is now the canonical exact identity for deep links, QR/PDF URL payloads, and exact object references.
- `canonicalAtomId(atom)` now prioritizes a valid MID (`atom.mid` or MID-valued `atom.atom_id`) over legacy stable 64-hex IDs.
- `canonicalAtomPath`/`canonicalAtomUrl` now produce working `/p/<MID>` links (with URL encoding), and `parsePublicPPath` now round-trips MID links.
- Legacy `/p/<64-hex>` and `/p/<p:12char>` remain accepted as compatibility inputs.
- MID map-focus now resolves by exact identity and derives coordinates from `h` (Layer-3 truth), avoiding malformed `p:punkti/0.6:...` fallbacks.

## 4) CI / Docker / deployment conformance changes

- Canonical workflow updated: `.github/workflows/punkto-image.yml`
  - pre-publish checks now include:
    - JS syntax (`pwa/*.js`, `pwa/*/*.js`, `app.js` module parse)
    - `node pwa/test-punkti-vectors.mjs`
    - `node pwa/test-punkti-publication.mjs`
    - `node pwa/test-spatial-xy-z.mjs`
    - Python node suites including `punkti_node.test_publication`
  - new dedicated browser E2E job runs `node pwa/test-punkti-static-e2e.mjs` with pinned `playwright@1.64.1` plus `npx playwright install --with-deps chromium`.
  - **gating decision**: hard gate. Publish job now depends on browser E2E job (`needs: browser-e2e`), so browser-path regressions block publish.
  - justification: static-first browser behavior is part of the frozen acceptance contract, so publish must not bypass browser-path regressions.
  - image digest is emitted in workflow summary from build output digest.
  - workflow summary explicitly states browser E2E gate mode and digest details.
  - build remains `linux/amd64,linux/arm64`.
- `pwa/test-punkti-static-e2e.mjs` now fails explicitly and non-zero when Chromium is unavailable, with a clear install hint (`npx playwright install --with-deps chromium`).
- `pilot-ci.yml` now includes the Punkto 0.6 Node protocol/vector suites in the hard PR gate:
  - `pwa/test-punkti-vectors.mjs`
  - `pwa/test-punkti-publication.mjs`
  - `pwa/test-spatial-xy-z.mjs`
- `deployment-verify.yml` remains valid and does not reference removed Stage 3 workflows.
- Deployment/examples moved to digest-pinned single-image shape:
  - `deploy/docker-compose.yml`
  - `docs/single-image.md`
  - `docs/single-image-deployment.md`
  - `DEPLOYMENT_CHECKLIST.md`
  - `DEPLOYMENT_RUNBOOK.md`
  - `DEPLOYMENT_SMOKE_TESTS.md`
- Added operator-run Docker conformance script:
  - `scripts/acceptance_static_first.sh`

## 5) Acceptance criteria table (Task 22 §4)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | JS reproduces frozen carrier bytes | PASS | `docs/evidence/issue-22/check-03-punkti-vectors.txt` |
| 2 | XY_Z profile conformance | PASS | `docs/evidence/issue-22/check-05-spatial-xy-z.txt` |
| 3 | Browser-generated records match normative vectors | PASS | `docs/evidence/issue-22/check-03-punkti-vectors.txt` |
| 4 | Reader rejects hostile publication cases | PASS | `docs/evidence/issue-22/check-04-punkti-publication.txt` |
| 5 | Anti-poisoning same-MID invalid variant | PASS | `docs/evidence/issue-22/check-04-punkti-publication.txt` |
| 6 | Stale root / retry / equivocal handling | PASS | `docs/evidence/issue-22/check-04-punkti-publication.txt` |
| 7 | Exact MID/R verification (sig excluded from MID) | PASS | `docs/evidence/issue-22/check-03-punkti-vectors.txt` |
| 8 | Layer-4 opaque payload preserved publish→read | PASS | `docs/evidence/issue-22/check-04-punkti-publication.txt` + node publication tests |
| 9 | Static-only browser read (daemon stopped) | PASS | `docs/evidence/issue-22/check-06b-static-e2e-nodepath.txt` |
| 10 | No `/pull` and no `/sync` in browser read | PASS | `docs/evidence/issue-22/check-06b-static-e2e-nodepath.txt` |
| 11 | Browser write `/submit` round trip | PASS (module-level browser round trip in same E2E run); real create-sheet UI publish path remains unproven in headless Stage 4 | `docs/evidence/issue-22/check-06b-static-e2e-nodepath.txt` |
| 12 | Static publication node replication convergence | PASS | `docs/evidence/issue-22/check-07-python-node-suite.txt`, `check-09-python-publication-suite.txt` |
| 13 | Docker/E2E end-to-end (incl restart, arm64/amd64) | NOT RUN (no docker daemon on host) | `docs/evidence/issue-22/check-16-docker-daemon-availability.txt`; operator script: `scripts/acceptance_static_first.sh`; script syntax: `docs/evidence/issue-22/check-15-acceptance-script-syntax.txt` |
| 14 | MID exact-link identity (deep link + map-focus lookup + QR/PDF URL payload) | PASS | `docs/evidence/issue-22/check-17-stage5-mid-breakage-before.txt`, `check-19-stage5-mid-breakage-after.txt`, `check-20-stage5-exact-identity-after.txt`, `check-28-stage5-static-e2e.txt` |
| 15 | Canonical publish workflow runs browser static E2E with explicit gate semantics | PASS (hard gate) | `.github/workflows/punkto-image.yml`; `docs/evidence/issue-22/check-37-stage6-yaml-lint.txt` |
| 16 | Stale dual-image deployment instructions removed from operative docs | PASS | `deploy/README.md`; `docs/fresh-install-ubuntu.md`; `docs/evidence/issue-22/check-38-stage6-legacy-name-sweep.txt` |

## 6) Raw evidence bundle

Directory: `docs/evidence/issue-22/`

- `check-01-js-syntax.txt`
- `check-02-app-module-check.txt`
- `check-03-punkti-vectors.txt`
- `check-04-punkti-publication.txt`
- `check-05-spatial-xy-z.txt`
- `check-06-static-e2e.txt`
- `check-06a-playwright-install.txt`
- `check-06b-static-e2e-nodepath.txt`
- `check-06b-static-e2e-blocked-superseded.txt` (historical blocker snapshot)
- `check-07-python-node-suite.txt`
- `check-08-python-mesh-suite.txt`
- `check-09-python-publication-suite.txt`
- `check-10-config-node-example.txt`
- `check-11-config-punkto-example.txt`
- `check-11b-config-punkto-example-with-webroot.txt`
- `check-12-yaml-lint.txt`
- `check-13-slice5.txt`
- `check-14-relay-suite.txt`
- `check-15-acceptance-script-syntax.txt`
- `check-16-docker-daemon-availability.txt`
- `check-17-stage5-mid-breakage-before.txt`
- `check-18-stage5-exact-identity-before.txt`
- `check-19-stage5-mid-breakage-after.txt`
- `check-20-stage5-exact-identity-after.txt`
- `check-21-stage5-js-syntax.txt`
- `check-22-stage5-app-module-check.txt`
- `check-23-stage5-test-exact-identity.txt`
- `check-24-stage5-punkti-vectors.txt`
- `check-25-stage5-punkti-publication.txt`
- `check-26-stage5-spatial-xy-z.txt`
- `check-27-stage5-slice5.txt`
- `check-28-stage5-static-e2e.txt`
- `check-29-stage5-python-node-suite.txt`
- `check-30-stage5-python-mesh-suite.txt`
- `check-31-stage5-python-publication-suite.txt`
- `check-32-stage5-acceptance-script-syntax.txt`
- `check-33-stage5-yaml-lint.txt`
- `check-34-stage5-legacy-p-quarantine-grep.txt`
- `check-35-stage6-js-syntax.txt`
- `check-36-stage6-app-module-check.txt`
- `check-37-stage6-yaml-lint.txt`
- `check-38-stage6-legacy-name-sweep.txt`
- `check-39-stage6-punkti-vectors.txt`
- `check-40-stage6-punkti-publication.txt`
- `check-41-stage6-spatial-xy-z.txt`
- `check-42-stage6-slice5.txt`
- `check-43-stage6-exact-identity.txt`
- `check-44-stage6-static-e2e.txt`
- `check-45-stage6-python-node-suite.txt`
- `check-46-stage6-python-mesh-suite.txt`
- `check-47-stage6-python-publication-suite.txt`
- `check-48-stage6-acceptance-script-syntax.txt`

## 7) Production cutover recommendation / open gates

Recommended next gate sequence:
1. Founder/human product acceptance of the Stage 3/4 UX shape (world browsing + technical/debug framing).
2. Operator host run of `scripts/acceptance_static_first.sh` with a real docker daemon (image build, restart durability, second-node replication, UI-disabled/publication-served mode, amd64+arm64 invocation).
3. Confirm combined-image digest pin in deployment environment before cutover.

Open gates (explicit):
- Docker daemon acceptance (criterion 13).
- Final design acceptance by founder/human.
