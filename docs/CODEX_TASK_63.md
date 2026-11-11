# CODEX TASK 63 — M8B: restore the approved map-first (Radio Garden-like) direction in PR #154

Repository: `Fisker1111/Punkto`
Branch: `feat/issue60-pwa-m8-ux` (already contains M8; HEAD is `dfa29f1cbe753988300056ded01f7970cd400b22`)
PR: https://github.com/Fisker1111/Punkto/pull/154 (review-only, must NOT be merged or deployed by you)
Issue: https://github.com/Fisker1111/CEO-OS/issues/63

**Read first:** `AGENTS.md`, `PUNKTO_UI_PRINCIPLES.md`, `docs/CODEX_TASK_60.md` (the
normative M8 spec, already implemented on this branch), `docs/UX_AUDIT_60.md`
(the Phase A audit with the live publication dump).

This document is normative. If you believe any rule below is contradictory or
impossible, **stop and report** instead of silently choosing a different
design. Do not invent requirements that are not written here.

---

## 0. Goal

M8 (PR #154) changed the **default opening surface** of the PWA from the 3D
Map to the text feed (`pwa/app.js` boot: `showPage(deepLinkPunkto ? 'map' : 'text')`).
The Founder has since confirmed a **map-first** direction: the Map is the
primary experience; text/feed is a secondary navigation mode.

**Keep every real fix already in PR #154** (canonical reply mapping, QA labels,
absolute-Z truth, 44px touch buttons, fixed Visible/Activity tabs, 13/15 record
population, contextual board sheet). Change **only** what this task describes.

Deliverables:

- **D1** — Map is the initial surface for ordinary visitors **and** for deep links.
- **D2** — A calm, unobtrusive, map-surface nudge ("Explore a real place") that
  offers **1–2 genuine published places**, derived from the **actual records the
  PWA itself fetched**, and lets a visitor open one of them **without typing
  coordinates and without granting geolocation**.
- **D3** — Selecting a place flies the camera to that place and opens the
  **existing** board sheet (the one PR #154 repaired). No new conversation store.
- **D4** — A focused regression suite covering the initial Map and the
  map → board path, wired into CI.
- **D5** — Nothing else changes: no protocol/crypto/identity/storage migration,
  no node config, no Caddy/DNS, no Worker/MCP, no web publish API, no live
  signed object modification.

---

## 1. Hard boundaries (do not violate)

**Forbidden:**

- No change to the signer, key management, or any crypto/verification
  primitive. No change to `parse_h`/`encode_h`/`format_z`/`parse_z`, the carrier
  wire format, or `refs` encoding.
- No IndexedDB schema migration (`pwa/storage/db.js` `db.version(...)` stays
  exactly as-is).
- No change to `pwa/protocol/`, `pwa/punkti/`, `pwa/ai.html`, `pwa/ai-first/`,
  `pwa/print-pdf.js`.
- No node / relay / Worker / MCP / backend change. No Caddy, DNS, deploy, or
  infra change. **No deployment, no merge, no new PR, no commit to any other
  branch.** Work only on `feat/issue60-pwa-m8-ux`.
- **No remote network write of any kind**: do not POST to `/submit` or to any
  remote node; do not create, publish, or mutate any signed object on
  punkto.xyz or any other live node. The PWA must keep working against
  read-only publication data only.
  **Explicitly permitted exception:** `node --test pwa/test-punkto-reply.mjs`
  is required by §1 and by CI. It spawns its own throwaway node on 127.0.0.1
  and performs loopback writes against **that isolated local instance only**
  (this is exactly what the existing CI job `ai-single-action` already does).
  That suite is allowed. Any write to a non-loopback host is not.
- No new dependency, bundler, build step, or package-manager file. `pwa/` is
  plain static ES modules.
- No change to the `Text | Map | + | Settings` navigation model, the
  bottom-dock/rail structure, or the "+"-in-nav placement.
- No new "verified people", social likes, AI replies, cell/hex overlay, or
  decorative fantasy map. Do **not** add a geohash cell overlay in this task.
- No visual/brand rethink, no light/dark overhaul, no model bake-off, no
  paid map service, no global directory.
- Do not change `pwa/sync/punkti-client.js`, `pwa/core/read-state.js`,
  `pwa/ui-text.js`, `pwa/ui-board.js` **unless** §5 requires it (it should not).

**Required:**

- `node --check` stays green for every **JavaScript file** (`.js` / `.mjs`) you
  touch, plus
  `node --input-type=module --check < pwa/app.js`, `pwa/ui-map.js`,
  `pwa/ui-board.js`, and every new module you add.
  (`node --check` cannot parse `.html` or `.yml` — for those files use:
  HTML → a markup sanity check of the edited regions (e.g. `grep` for the new
  ids/classes/data-actions you added, and confirm the edited tag nesting is
  balanced); Hermes performs the real browser QA, not you. YAML → `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))"`
  on `.github/workflows/pilot-ci.yml`.)
- All existing suites stay green and unchanged in behaviour:
  `node pwa/test-slice5.mjs`, `node pwa/test-punkti-vectors.mjs`,
  `node pwa/test-punkti-publication.mjs`, `node pwa/test-spatial-xy-z.mjs`,
  `node pwa/test-ai-coldstart.mjs`, `node pwa/test-ai-hostile.mjs`,
  `node pwa/test-ai-cli.mjs`, `node pwa/test-punkto-m8-ux.mjs`,
  `node --test pwa/test-punkto-reply.mjs`.
- 44px minimum touch targets, no mobile bottom-sheet overlap, keyboard
  accessibility, correct header `h` / absolute-Z wording, honest trust labels.
- One minimal follow-up commit on this branch. Do not rewrite prior history.

---

## 2. D1 — Map is the initial surface

In `pwa/app.js` (`boot()`), the initial page becomes the Map unconditionally:

- Ordinary visitor (no deep link): initial page = `map`.
- Deep link `/p/<id>`: initial page = `map` (unchanged behaviour).

Make the decision testable: put the rule in a tiny pure module and import it,
e.g. `pwa/core/explore.js` exporting

```js
export function initialPageForBoot() { /* always 'map' */ }
```

and have `pwa/app.js` call it. Do not leave the decision as an inline ternary
that a test cannot reach.

The Map's existing behaviour must not regress:

- `ensureMapInitialized()` must still run on boot (it is currently reachable
  through `showPage('map')` → `onShowMap`; verify this and keep it true).
- The existing 2D/3D toggle, pan/tilt, zoom, and the existing geolocation
  "jump to my position" behaviour stay as they are.

---

## 3. D2 — The map-surface "Explore a real place" nudge

Create `pwa/core/explore.js` (new module, no dependencies beyond
`./read-state.js`). It must export at least:

```js
export const EXPLORE_PLACE_LIMIT = 2;
export function selectExplorePlaces(atoms, { limit = EXPLORE_PLACE_LIMIT } = {}) { /* -> Place[] */ }
export function primaryExplorePlace(places) { /* -> Place | null */ }
export function explorePlacesHtml(places) { /* -> string */ }
```

`Place` shape: `{ atomId, h, lat, lon, title, kind }` where `kind` is
`'public'` or `'qa'`.

### Selection rules (must be exact)

1. Input `atoms` is the PWA's loaded atom list (`_mainFeedAtoms`).
2. Ignore reply atoms (an atom with `relation === 'reply'` or a truthy
   `parent_id`). Only boards/roots can be a "place".
3. Ignore atoms without an exact spatial address (`h`) or without finite
   `lat`/`lon`.
4. **Group by the exact address `h`.** One `h` = one place. A place's `atomId`
   is the canonical id of one representative root atom of that group (use the
   first such atom in input order).
5. A group's `kind` is `'public'` if **any** record in the group is **not** a
   QA record (`isQaRecord` from `./read-state.js`), else `'qa'`.
6. **Only groups whose kind is `'public'` are returned.** If there is no public
   group at all, fall back to `'qa'` groups (there is then nothing genuine to
   show), and every such place must be labelled `QA record` in the UI.
7. Sort: public groups first; then by number of records in the group
   descending; then by `h` ascending (stable, deterministic).
8. Truncate to `limit` (2).

This yields, for the current live publication, the **genuine** Null Island
place (`h = s00000000000_0`) and nothing else — the operator acceptance
records are QA records and must never be presented as outside participants.
**Do not hardcode** Null Island, coordinates, titles, or counts: everything must
come from the fetched atoms. Do not invent a landmark that is not in the data.

### UI

- Add one map-surface overlay element in `pwa/index.html`, id
  `map-explore-nudge`, `aria-label="Explore a real place"`, containing:
  - the three honest explainer lines that the M8 first-visit card already used
    (Addressability / Distribution / Persistence) — reuse the same wording,
  - a heading like "Explore a real place",
  - one **real `<button>`** per place from `explorePlacesHtml()`, each with
    `data-action="explore-place"` and `data-atom-id="<atomId>"`,
    `type="button"`, a visible label (the place title + the exact `h`), and
    `min-height: 44px` (mobile-safe),
  - a "Dismiss" button with `data-action="dismiss-explore"`.
- The overlay is visible only on the **map** surface (hide it in the text
  page exactly the way `#onboarding-hint` / `#map-empty-hint` are hidden), and
  it must not overlap the mobile bottom nav or the map board sheet. Respect
  `--nav-h` / `--safe-b` and the existing 44px rules already in
  `pwa/index.html`.
- Keyboard accessibility: real buttons, focusable, reachable by Tab; the
  overlay is `aria-live="polite"` or contains a `role="status"` line if it
  updates. Dismiss hides it.
- Dismissal persists in `localStorage` under the existing key
  `punkto.explored` (same key the M8 first-visit card already used).
- The **text page's** M8 first-visit card (`#first-visit-explore`) and its
  "Explore published text" button must be **removed** — the text page is now a
  secondary mode and must not push itself as the entrance. Keep the three
  explainer lines (they move into the map overlay). Removing the card must not
  break the `punkto.explored` persistence semantics.
- The overlay content is rendered from the loaded atoms. While the publication
  is still loading or if it failed, show an honest short state
  (e.g. "Loading published places…") and never a fake place.

### Where it is wired

- `pwa/app.js`: render/refresh the overlay whenever the loaded atom list
  changes and the current page is `map`; hide it when the current page is
  `text`; handle `data-action="explore-place"` and `data-action="dismiss-explore"`
  clicks (the existing global `click` listener in `boot()` already dispatches
  `data-action`; extend it, and make sure the existing
  `reply-settings` / `retry-read` handling keeps working).
- The overlay must reappear for a visitor who has not dismissed it, on every
  fresh load, and must not reappear after dismissal.

---

## 4. D3 — Map → board path for a chosen place

Clicking a place button must:

1. switch to the map surface,
2. **fly the camera** to that place's exact coordinates at a street-ish zoom
   (`zoom: 16`, matching the existing `focusPunktoOnMap` behaviour in
   `pwa/ui-map.js`), and
3. open the **existing** board sheet for that board — the same code path the
   M8 text feed already uses when you press "Open board", i.e.
   `openMapBoardForAtom(atom, atoms)` in `pwa/ui-board.js`.

Prefer reusing the existing `focusPunkto(id)` / `focusPunktoOnMap(id)` path in
`pwa/app.js` / `pwa/ui-map.js` if it already does flyTo + open the map board
sheet — do not duplicate camera logic. Keep the board sheet's existing
"← Back to map" behaviour (PR #154) and its exact-address header wording.

Respect the exact `XY_Z` address: derive the camera position from the record's
own exact `h`/coordinates. **Never** estimate an ellipsoidal Z, never re-derive
a height, never bypass publish validation.

### First-visit framing (part of D2/D3)

When the map opens and **no user location is known** (geolocation denied or
unavailable — the fresh-profile case), the camera should frame the
**primary explore place** (`primaryExplorePlace(selectExplorePlaces(atoms))`)
so a real published place is visible immediately, instead of an arbitrary
default centre. Implement this as a camera-only move (no board sheet, no
selection) once the atoms are first available.

- If geolocation succeeds, keep the existing "jump to my position" behaviour
  (the user's own location wins over the explore place).
- If there is no explore place, keep the existing default centre — do not
  invent one.
- Do not open a board automatically on first load; the visitor chooses.

---

## 5. D4 — Focused regression suite

Add `pwa/test-punkto-m8b-map-first.mjs` (plain `node` script, same style as
`pwa/test-punkto-m8-ux.mjs`; no test framework, no new dependency) that asserts
at least:

1. **Initial Map** — `initialPageForBoot()` is `'map'` for an ordinary visitor
   and for the deep-link case (if you expose a deep-link argument, it must also
   be `'map'`).
2. **The nudge is data-driven** — running `selectExplorePlaces` over the atoms
   decoded from the existing fixture `pwa/tests/publication-live-60.json`
   (use `mapRecordToAtom` from `pwa/sync/punkti-client.js` exactly like
   `pwa/test-punkto-m8-ux.mjs` does) yields:
   - exactly one place, the genuine Null Island place, `h === 's00000000000_0'`,
     `kind === 'public'`,
   - **no** QA/operator record is offered as a place (assert no returned place
     has `kind === 'qa'` in this dataset, and assert every offered place's `h`
     belongs to a genuine non-QA record),
   - the returned place count never exceeds `EXPLORE_PLACE_LIMIT`,
   - every returned place has a finite `lat`/`lon` and a non-empty exact `h`,
   - the selection is deterministic (same input → same output) and does not
     mutate its input array.
3. **map → board path** — using the same fixture, the representative board of
   the offered place resolves through the **existing** repaired board code
   (`resolveBoardAtom` / `boardReplies` from `pwa/ui-text.js`): the two real
   same-address replies in the dataset group under their parent root, and the
   offered place's own board shows that grouping — i.e. opening a place shows a
   true exact-address thread, not a flat card.
4. **No fake participation** — the rendered nudge HTML (`explorePlacesHtml`)
   contains no `Verified` claim about people, no like/follower counts, and no
   invented name; and it renders one `<button>` per offered place with a
   `data-atom-id` matching the offered place's `atomId`.
5. **Accessibility floor** — every button in the rendered nudge HTML carries
   `type="button"`; the nudge markup declares a 44px minimum touch height via a
   class you also style in `pwa/index.html` (assert the CSS rule exists in
   `pwa/index.html` by reading the file and matching the min-height rule for
   the nudge's button class).

Then wire it into CI: add a step to `.github/workflows/pilot-ci.yml` in the
`pwa-validation` job, next to the existing M8 UX suite step, named
`M8B map-first regression suite (initial Map, explore places, map to board)`,
running `node pwa/test-punkto-m8b-map-first.mjs`. The job must stay green.

Also add `node --check pwa/core/explore.js` and
`node --input-type=module --check < pwa/core/explore.js` to the CI syntax
checks step (the ES-module check is required for every new module).

---

## 6. Files you may touch

- `pwa/app.js`
- `pwa/index.html`
- `pwa/ui-map.js` (only if needed for the camera-only framing move; keep the
  change minimal and reuse the existing flyTo helpers)
- `pwa/core/explore.js` (new)
- `pwa/test-punkto-m8b-map-first.mjs` (new)
- `.github/workflows/pilot-ci.yml`
- `docs/evidence/issue-63/` (screenshots and notes only — you cannot produce
  browser screenshots; leave the directory out unless you have real files)

Do not touch anything else. If you believe another file must change, **stop
and report** why instead of editing it.

---

## 7. Definition of done (report these, do not just assert them)

- `git status` clean except your intended changes; exactly one new commit on
  `feat/issue60-pwa-m8-ux`; **no push** (Hermes pushes and commits if the
  sandbox cannot write the git dir).
- Paste the **actual output** of every command you ran:
  - `node --check` for each touched **JavaScript** file,
  - the ES-module parse check for each new/touched module,
  - a YAML parse check for `.github/workflows/pilot-ci.yml`,
  - all eight pre-existing suites listed in §1 (exact pass/fail lines),
  - `node pwa/test-punkto-m8b-map-first.mjs` (exact pass count and the final
    summary line),
  - `git diff --stat main...HEAD` (or `origin/main...HEAD`).
- List every file you changed and, for each, one sentence on what changed and
  why.
- State explicitly that you did **not** merge, deploy, push, create a PR, or
  perform any write to a remote host. The only writes performed were the
  isolated 127.0.0.1 loopback writes performed by `pwa/test-punkto-reply.mjs`
  against its own throwaway node (permitted, see §1).
