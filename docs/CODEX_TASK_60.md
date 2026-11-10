# CODEX TASK — CEO-OS Issue #60: Punkto PWA M8 (first-visit, spatial browsing, conversation UX)

Repository: `Fisker1111/Punkto`
Base branch: `main`
Work branch: `feat/issue60-pwa-m8-ux`
Issue: https://github.com/Fisker1111/CEO-OS/issues/60

**Read first:** `AGENTS.md`, `PUNKTO_UI_PRINCIPLES.md`, and the audit at
`docs/UX_AUDIT_60.md` in this branch. The audit contains the reproduced
evidence, the live publication dump and the exact source locations.

This document is normative. If you believe any rule below is contradictory or
impossible, **stop and report** instead of silently choosing a different
design.

---

## 0. Goal

Deliver ONE review-only PR that makes three user-visible improvements to the
browser PWA in `pwa/**`:

- **I1** — honest, legible thread / read / reply state
- **I2** — a first-visit Explore/Read entry
- **I3** — mobile spatial→board navigation + contextual place header / back handling

Scope is deliberately small. This is **not** a redesign.

---

## 1. Hard boundaries (do not violate)

**Forbidden:**

- No change to the core signer, key management, or any crypto/verification
  primitive (`pwa/key-management.js`, `pwa/punkti/carrier.js` signature
  logic, `pwa/core/` crypto helpers).
- No change to the Punkti L3/L4 protocol semantics, `parse_h`/`encode_h`,
  `format_z`, `parse_z`, the carrier wire format, or the `refs` encoding.
- No IndexedDB schema migration (`pwa/storage/db.js` `db.version(...)` must
  stay exactly as-is).
- No worker / node / relay / backend service change. No Caddy, GoDaddy, DNS,
  deployment, or infra change of any kind. This PR is **review-only**: it must
  NOT deploy anything and must NOT merge itself.
- No change to public write defaults, no test key usage, no real write to any
  node. Do not POST to `/submit` or any node.
- Do not touch `pwa/ai.html`, `pwa/ai-first/`, `pwa/print-pdf.js`,
  `pwa/protocol/`, or the `/ai` entrance behaviour.
- Do not add a new dependency, a bundler, a build step, or a package manager
  file. `pwa/` is plain static ES modules.
- Do not change the `Text | Map | + | Settings` navigation model, the
  bottom-dock/rail structure, or the "+"-in-nav placement.
- Do not implement a light/dark theme switch (deliberately out of scope this
  round).

**Required:**

- Keep `node --check` green for every file you touch, plus
  `node --input-type=module --check < pwa/app.js` and the same for
  `pwa/ui-map.js` and `pwa/ui-board.js`.
- Keep every existing test green: `pwa/test-slice5.mjs`,
  `pwa/test-punkti-vectors.mjs`, `pwa/test-punkti-publication.mjs`,
  `pwa/test-spatial-xy-z.mjs`, `pwa/test-ai-coldstart.mjs`,
  `pwa/test-ai-hostile.mjs`, `pwa/test-ai-cli.mjs`,
  `pwa/test-exact-identity.mjs`, `pwa/test-punkto-static-e2e.mjs`,
  `pwa/test-punkto-reply.mjs`.
  Run them all and paste the real output in your final report.
  (Note the exact filenames: `test-punkti-*` for the punkti protocol suites,
  `test-punkto-*` for the punkto product suites. `pwa/test-punkto-reply.mjs`
  is an isolated-fixture suite that starts a real local `punkti_node`; it must
  still pass, and it is your isolated end-to-end proof surface for any reply
  behaviour — see §5.)
- Add **new focused tests** for the logic you add (see §5).
- No `console.log` left behind in production code paths (existing `console.warn`
  / `console.error` style is fine).
- Match the surrounding code style: 2-space indent, single quotes, semicolons,
  ES modules with explicit `.js` extensions in import specifiers.

---

## 2. I1 — Honest thread / read / reply state

### 2.1 Carry the reply relation from the publication into the UI atom

**Problem.** `pwa/sync/punkti-client.js` `mapRecordToAtom()` (lines ~60-100)
does not read `record.atom.refs`, and only copies `payload.meta.category` and
`payload.meta.author` from the payload meta. The reply relation therefore
never reaches the UI, so `pwa/ui-text.js` (`isReplyAtom`, `_replyBelongsToRoot`,
`_boardReplies`) and `pwa/ui-board.js` (`Replies · N`) can never group a
published reply under its parent.

Live proof: the board for `h = u3butz7k9q_23` renders `Replies · 0` while the
same publication contains a signed reply to that exact `h` whose carrier
`refs` array holds `{target: "punkti/0.6:19cf1ba8…", rel: "reply"}`.

**Ground truth you can rely on** (decoded from the live publication with the
repo's own `pwa/punkti/carrier.js`; see `pwa/tests/publication-live-60.json`,
regenerate with `node scripts/decode-live-publication.mjs`):

- Exactly 2 of the 15 live records carry a `reply` ref:
  - `punkti/0.6:e1865d1e…` — `h = u3butz7k9q_23`, refs
    `[{target: "punkti/0.6:19cf1ba8…", rel: "reply"}]`
  - `punkti/0.6:70e0da2f…` — `h = s00000000000_0`, refs
    `[{target: "punkti/0.6:fc188702…", rel: "reply"}]`
  Both targets exist in the same publication and share the reply's exact `h`.
- **The ref target is a full `punkti/0.6:<64-hex>` MID, not a bare id.**
  `pwa/protocol/punkto-id.js` `stripPunktoPrefix()` only strips a leading `p:`;
  it does **not** strip `punkti/0.6:`. Verified:
  `stripPunktoPrefix('punkti/0.6:19cf1ba8…') === 'punkti/0.6:19cf1ba8…'`.
- `pwa/ui-text.js` `_normalizedAtomIds(atom)` collects
  `[atom.atom_id, atom.id, atom.punkto, stripPunktoPrefix(atom.punkto)]`, and
  `mapRecordToAtom()` sets `atom.atom_id = record.mid` — which **is** the full
  `punkti/0.6:<64-hex>` form. So the parent's `atom_id` and the reply's
  `parent_id` match **only if both use the full MID form**. Do not strip
  `punkti/0.6:` from the ref target.
- `pwa/ui-text.js` `_replyBelongsToRoot()` compares
  `_replyParentIds(reply)` (`parent_id`, `root_id`) against the root's
  normalized ids, additionally trying `stripPunktoPrefix(id)` — which is a
  no-op for MID-shaped ids. Keep the full MID form.

**Required change.** In `mapRecordToAtom()`, derive the reply relation and
expose it on the returned UI atom:

- From `record.atom.refs`: take entries whose `rel` trimmed and
  lower-cased is exactly `'reply'`. For the **first** such entry, set
  - `relation: 'reply'`
  - `parent_id` = the ref `target` **verbatim** (keep the `punkti/0.6:`
    prefix — see the ground truth above)
  - `root_id` = `parent_id` (the publication carries no separate root id; the
    reply's root is its parent for our purposes)
- From `payload.meta` (the parsed JSON inside `x`), when present and
  non-empty, set the same three fields:
  - `meta.relation` → `relation` (only when it is the string `'reply'`)
  - `meta.parent_id` → `parent_id`
  - `meta.root_id` → `root_id`
  The meta path already exists for atoms published through the current PWA
  submit flow (`pwa/app.js` writes `meta.relation = 'reply'`), so support both.
  When meta carries a **bare** id (no `punkti/0.6:` prefix) while the
  parent's `atom_id` is the MID form, normalise both sides to a comparable
  form so the grouping still works — but prefer the `refs` (MID) form when
  both are present.
- When the `refs` path and the `meta` path disagree, **prefer `refs`** (it is
  the signed, canonical source; meta is unsigned payload content).
- When there is no reply relation, leave `relation`/`parent_id`/`root_id`
  unset — an atom with no relation is a root, and `pwa/ui-text.js`
  `isRootAtom()` already treats that correctly.

Do **not** change `pwa/punkti/carrier.js` or `pwa/punkti/reader.js`. The
`refs` array is already decoded and available on `record.atom.refs`.

### 2.2 Make the reply composer honest about the identity gate

**Problem.** `pwa/ui-text.js` `renderBoardDetail()` always renders the
"Public reply" composer. Submitting without an identity fails inside
`signAtomForSubmit()` (`pwa/app.js`) with
"Create or import an identity in Settings before publishing." — a raw
failure after the user typed their message.

**Required change.** The composer must state the gate *before* the user
types, and must not silently swallow a failed post.

- When no identity is available, render the composer as a disabled/locked
  state with a clear, non-technical message and a link/button that takes the
  user to Settings ("Set up your identity in Settings to reply"). The
  disabled state must be visibly disabled (not merely inert), and must
  explain the reason.
- When an identity exists, keep the current enabled composer exactly as-is.
- On a failed post, keep the user's draft text in the textarea and show the
  error message next to the composer (this behaviour exists in
  `submitBoardReply()` in `pwa/ui-text.js` and `handleBoardSubmit()` in
  `pwa/ui-board.js` — preserve it; do not regress it).
- Do not add a second reply form. There must be exactly **one** reply
  composer per board surface.

To know whether an identity exists, expose a small async/sync-capable
predicate from `pwa/app.js` (for example `hasIdentity()` returning whether
`currentIdentity` or a persisted identity is present) and pass it into
`initTextView()` / `initBoardView()` as an option. Keep the existing
`helpers` plumbing pattern.

### 2.3 Show the place's exact spatial address honestly

**Problem.** The board sheet shows `10/30/2026 · Floor 8 · Distance not
available` and **no address at all** — the reader cannot tell where the place
is. Worse, `Floor 8` is derived by `fmtAltitudeLabel()`
(`pwa/core/display.js:43`, `Math.round(alt / 3)`) from the **absolute WGS84
ellipsoidal height**, which is a guess, not a floor attribute.

**Required change.**

- In the board detail (both the Text-page board and the map board sheet),
  show the place's exact spatial address so the reader knows *where* it is.
  Use the values already available on the UI atom: `h` (the exact address
  string), `lat`, `lon`, and `ellipsoidal_z` / `alt`. Render them with the
  existing helpers (`fmtCoords` in `pwa/core/display.js` formats
  `lat, lon · altm`).
- Fix the floor label: when the atom carries a real `meta.floor`
  (surfaced as `atom.floor` by `mapRecordToAtom`), label the floor from that
  value. Only fall back to `fmtAltitudeLabel()`'s height-derived guess when
  no real floor attribute exists — and in that fallback case the label must
  be honest about being an elevation, not a floor number.
- Height must be labelled as **absolute WGS84 ellipsoidal height**, because
  `h`'s Z component is exactly that. Do not present ellipsoidal Z as
  "above ground" or as a floor.
- Keep "Distance not available" honest: if the distance is genuinely
  unavailable, keep saying so; do not fabricate a distance.

### 2.4 Keep trust labels honest

`isVerifiedAtom()` (`pwa/core/atoms.js:13`) is `Boolean(sig && pubkey)` —
the presence of a signature and a key, nothing more. The UI currently renders
that as the badge **"Verified"** and the trust line **"Verified public post"**.

**Required change.** The badge/label must not claim more than was checked.

- The reader's own `validate()` (`pwa/punkti/carrier.js`) already computes a
  real per-record state (`VALID`, `INVALID-provenance`,
  `INVALID-structural`, `UNVERIFIABLE-alg`, …) and `mapRecordToAtom()`
  already surfaces it as `verification_state`.
- Use `verification_state` when it is available and `VALID` → keep a
  "Verified" style label (signature + provenance actually checked). When the
  state is present but not `VALID`, render a distinct, honest label (e.g.
  "Unverified signature" / "Signature not verified") instead of "Verified".
- When `verification_state` is absent (locally created atoms that were never
  round-tripped through the reader), do **not** claim "Verified". Use an
  honest label such as "Signed" or "Not independently verified".
- Do not claim author *identity* is verified anywhere. A valid signature
  proves the bytes were signed by the holder of a key; it does not prove who
  that human is. Keep the wording at that level of truth.

---

## 3. I2 — First-visit Explore/Read entry

### 3.1 Make the Text view agree with the count in the top bar

**Problem.** Live at 390×844 and at 1440×900, a fresh load shows **"15
visible"** in the top bar and **"0 visible"** on the Text tab at the same
time, with the Text tab rendering the "Location needed → Enable location"
wall instead of the published content.

Root cause: `pwa/app.js` `refreshUI()` (~lines 428-476) builds the feed from
atoms inside the **map viewport bounds**:

```js
const bounds = map.getBounds();
recent = enriched.filter(a => Number.isFinite(a.lat) && … && bounds.contains([a.lon, a.lat]))…
```

while `elCountNum` is set from the *unfiltered* `visibleAtoms`. The two
numbers are computed from different sets.

**Required change.**

- The Text feed and the count shown to the user must be derived from the
  **same** atom set. Pick one definition and use it for both the top-bar
  count and the Text page count/subtitle.
- The Text view must show the real published atoms that the header count
  already claims. A visitor must not see "15 visible" in one place and an
  empty list in another.
- Do not remove the map viewport scoping concept entirely if it is still
  meaningful — but it must not silently hide published content while the
  count implies otherwise. If you keep a viewport-scoped notion, label it
  explicitly and make the unfiltered count label match what is listed (for
  example a distinct "in this map view" sub-count vs the total), so the two
  numbers can never contradict.
- The location prompt must **not** replace published content that is already
  available. Show the "Enable location" affordance as an *additional*
  enhancement (it only adds "distance from me"), never as a wall in front of
  content the client already has. Only show a location-only empty state when
  there is genuinely nothing else to show.

### 3.2 Give a first-visit user a plain-language way in

**Problem.** The first-run UI exposes raw protocol internals: the Text view's
"World view filters (static publication)" panel has fields labelled
**"XY prefix (e.g. u3b)"** and **"Z min"**. The issue states first-run must
not require learning GeoHash, MIDs or cryptography. There is also no
explainer for the product's own three ideas.

**Required change.**

- Add a compact, plain-language explainer for first-time users covering
  **Addressability · Distribution · Persistence**, in normal language (no
  "GeoHash", no "MID", no "XY prefix", no "ellipsoidal"). It must be short —
  one line per idea — and must not block the UI.
- Add an explicit **Explore** affordance on first visit that takes the user
  to real published content (the same content the count claims exists),
  reachable without granting location and without typing an address.
- Demote the raw scope inputs ("XY prefix", "Z min", "Z max", "Apply world
  scope", "Clear scope") behind a disclosure (e.g. `<details>`) with a
  non-jargon label such as "Advanced filters". **Keep the functionality
  intact** — the same inputs, the same IDs, the same behaviour — just not as
  the default first-run surface. Do not remove the ability to scope by
  address.
- The explainer/explore surface must be dismissible and must not re-appear
  on every visit once dismissed (use the existing `localStorage` pattern
  already used for the onboarding hint — see `ONBOARDING_KEY` in
  `pwa/app.js`).
- Do not break the existing onboarding hint (`#onboarding-hint`); if you
  change how it is shown, keep it dismissible the same way.

### 3.3 Recoverable loading / error state

**Problem.** `pwa/ui-text.js` `renderTextFeed()` has a `loadingVisibleAtoms`
flag, and the sync status is only a coloured dot
(`#main-sync-indicator`). A failed or stalled publication read leaves the
Text view empty with no explanation and no way to retry.

**Required change.**

- Distinguish, in the Text view, **loading** / **empty** / **error**, and
  give the error state a **retry** action that re-triggers the read.
- The error message must be plain-language and must not leak protocol
  internals.
- Do not present an error as an empty state, and do not present an empty
  state as an error.

---

## 4. I3 — Mobile spatial→board navigation + place header / back handling

### 4.1 A working route from a place to its board on mobile

**Problem.** `#fab-panel` is `display: none !important`
(`pwa/index.html:475`), so on mobile the nearby-text panel is unreachable and
the only route to a board is tapping a map bubble. Worse, the per-item button
in that panel is labelled **"Open board on map"** (`pwa/app.js:518`) but only
calls `focusPunkto(id)` → `focusPunktoOnMap()`, which *moves the map* and
does **not** open the board sheet. Clicking it leaves the user on a map with
no thread — reproduced live.

**Required change.**

- On mobile, a user must be able to go from a place to its board and read the
  thread. The nearby-text surface must be reachable on mobile, or the map
  must open the board sheet directly when a place is activated.
- Fix the mis-labelled button so its label matches what it does. If it opens
  the board sheet, label it accordingly ("Open board" / "Read this place").
  If it only focuses the map, label it for that ("Show on map") — but then a
  separate, reachable "Open board" action must exist.
- Keep the existing `Text | Map | + | Settings` navigation model and the
  "no hamburger" rule from `PUNKTO_UI_PRINCIPLES.md` (do not reintroduce a
  ☰ button). Find another reachable affordance consistent with the
  principles document — read `PUNKTO_UI_PRINCIPLES.md` before choosing.
- The whole path must work on **both** 390×844 and 360×640, and on desktop
  1440×900, and it must not require granting location.

### 4.2 Contextual place header and back handling

**Problem.** The map board sheet's back action is a bare **"Close board"**
button (`pwa/ui-board.js` `renderMapBoardSheet()` passes
`backLabel: 'Close board'`), and closing it clears the selection entirely, so
the user loses their place in the map.

**Required change.**

- The board surface must show a contextual place header: the place's
  identity (exact `h` address and/or coordinates) so the user can tell which
  place the thread belongs to. Reuse the exact same address rendering as
  §2.3 — do not implement two different address formats.
- The back action must be contextual: it must return the user to where they
  came from (the map with that place still in view, or the list/feed they
  opened it from), not discard the context. Label it for where it goes.
- The Text-page board (`pwa/ui-text.js` `renderBoardDetail()`) already has a
  "← Visible here" / "← Back to Activity" back button — keep that behaviour
  consistent with the new map-sheet back handling.

### 4.3 No overlap of bottom nav / onboarding hint on small viewports

**Problem.** Measured at 390×844: `#bottom-nav` rect `[14, 710, 306, 120]`
vs `#panel` rect `[0, 784, 390, 280]` → **46 px overlap** (nav z-index 200
over panel z-index 100). The `#onboarding-hint` also collides visually with
the nav row in the live screenshot.

**Required change.**

- On small viewports the bottom nav, the nearby-text surface and the
  onboarding hint must not overlap each other.
- Touch targets must remain usable: keep interactive controls at a
  comfortable touch size (do not shrink existing buttons below ~44 px to
  fix the overlap — fix the layout instead).
- Verify at 360×640 as well as 390×844.

### 4.4 Mark QA/demo records honestly

**Problem.** The 15 published atoms are CEO-OS acceptance-evidence records
("Punkto production cutover evidence — CEO-OS #33 …", "CEO-OS #33
safety-probe acceptance"). They render as ordinary "Verified public post"
boards with no marker. `isHiddenAtom()` only hides handles `test`,
`sync-test`, `cors-test`, `browser-test`, which these atoms do not carry.

**Required change.**

- QA/demo/acceptance-evidence records must be labelled as such in the UI
  (a visible, honest badge such as "QA record" / "Acceptance test record"),
  so a visitor is not misled into thinking they are ordinary public posts.
- The detection must be conservative and deterministic — do not hide real
  user content, and do not use fuzzy heuristics that could label a genuine
  user post as a test record.
- **Use the signal that is actually present in the data.** The live records
  (see `pwa/tests/publication-live-60.json`) fall into two clear groups:
  - Acceptance/canary evidence records. Their payload is either a JSON object
    carrying a `run` / `case_record` key (e.g.
    `{"text":"CEO-OS#35 canary","run":"fdac221e…","case_record":1}`) or plain
    text naming the acceptance run (e.g. `"CEO-OS #33 safety-probe
    acceptance"`, `"Punkto production cutover evidence — CEO-OS #33 node A
    publish"`, `"CEO-OS issue 35 controlled public write acceptance test atom
    (Punkto operator)"`).
  - Genuine public posts: `"Welcome to Null Island — …"` and
    `"Hello from a new AI"` (the latter is a real reply to the former).

  A narrow, explainable rule is therefore: mark a record as a QA/acceptance
  record when its payload carries a `run` or `case_record` key, **or** its
  text names an acceptance/canary marker such as `CEO-OS`. Implement it as a
  small pure helper (so it can be unit-tested) with a comment explaining the
  rule, and make sure the two genuine posts above are **not** marked.
  State in your report exactly which signal you used and show the marked vs
  unmarked split over the 15 live records.
- Do not *hide* QA records — the issue asks for honest marking, not removal.
  (The existing `isHiddenAtom()` behaviour in `pwa/core/atoms.js` is
  unchanged and out of scope.)

---

## 5. Tests you must add

### 5.0 Use the live-record fixture

`pwa/tests/publication-live-60.json` is already in the branch: a snapshot of
the live `punkto.xyz` publication (15 records, publication head
`c77ba862…`, seq 14) decoded with the repo's own `pwa/punkti/carrier.js`.
Each record carries `mid`, `sha256`, `h`, `xy`, `z`, `lat`, `lon`, `t`, `x`
(the raw payload string), `x_json` (the parsed payload when it is JSON),
`refs`, `pk` and `sig`.

Regenerate it with `node scripts/decode-live-publication.mjs` (needs network;
already committed, so you do not need network to work).

Use this fixture as the ground truth for your tests — it contains the two
real reply relations, the QA/acceptance records and the two genuine public
posts. Do not hand-write fake records when real ones are available.

### 5.1 Required test coverage

Add focused, deterministic tests (new file(s) under `pwa/`, following the
existing `pwa/test-*.mjs` style — plain Node, `node:assert/strict`, no
framework, no new dependency) covering at minimum:

1. **Reply relation mapping** — a carrier record with
   `refs: [{target, rel: 'reply'}]` maps to a UI atom with
   `relation/parent_id/root_id` set, and the `parent_id` **keeps the full
   `punkti/0.6:` MID prefix verbatim** (it is NOT stripped — see §2.1 ground
   truth); a record with no refs maps to a root with those fields unset; the
   `refs` source wins over a conflicting `meta.relation`. Assert this against
   the real fixture records `punkti/0.6:e1865d1e…` (reply) and
   `punkti/0.6:19cf1ba8…` (its parent) in `pwa/tests/publication-live-60.json`.
2. **Trust label honesty** — a `VALID` verification state renders a verified
   label; a non-`VALID` state does not; an atom with a signature but no
   verification state does not render "Verified".
3. **Floor vs ellipsoidal height** — an atom with `meta.floor` renders the
   real floor; an atom without it does not present a height-derived guess as
   a floor.
4. **Text feed vs count consistency** — the number rendered as visible and
   the list of rendered cards are derived from the same atom set (e.g. a
   published atom outside the map viewport is still listed, and the count
   matches the list length).
5. **Reply grouping** — two atoms with the same `h`, one carrying a reply
   relation to the other, group as one board with one reply; the reply is
   not rendered as an independent top-level card.
6. **Error / loading states** — a failed read renders an error state with a
   retry affordance, not an empty state.

Keep the tests pure and DOM-light. If a behaviour is only reachable through
DOM wiring, extract the pure decision into a small exported helper (for
example in `pwa/core/` or `pwa/ui-text.js`) and unit-test that helper — do
not build a DOM test harness.

**End-to-end proof of the reply behaviour.** The Issue forbids claiming
successful end-to-end publishing without an independently exercised isolated
fixture. `pwa/test-punkto-reply.mjs` is exactly that surface: it starts a
real local `punkti_node` on 127.0.0.1 with an isolated publication, submits a
signed reply, and re-reads it. Extend it (or add a sibling suite) so the
reply is published and then **read back through the PWA client path** and
asserted to be grouped under its parent — proving the fix end to end
without touching production. If you extend it, keep its loopback-only
network guard intact.

---

## 6. Verification you must perform (and report with real output)

1. `node --check` on every changed `.js` file, plus
   `node --input-type=module --check < pwa/app.js` (and the same for
   `pwa/ui-map.js` and `pwa/ui-board.js` if you change them).
2. All existing `pwa/test-*.mjs` suites, as listed in §1 — paste real output.
3. Your new test file(s) — paste real output.
4. Serve `pwa/` locally (e.g. `python3 -m http.server` from `pwa/`) and
   confirm the app boots with no uncaught console errors and no syntax
   errors. Note that against a plain static server the create flow has no
   `/atom` endpoint — that is expected and is not a regression.
5. Report exactly which files you changed and why, with a `git diff --stat`.

## 7. Commit and push

- One focused commit on branch `feat/issue60-pwa-m8-ux`, based on `main`.
  Message subject: `feat(pwa): M8 first-visit explore, spatial board navigation and honest thread state (CEO-OS #60)`.
- Commit these deliverables in the branch:
  - the code changes under `pwa/`
  - the new tests under `pwa/`
  - `docs/UX_AUDIT_60.md` (the Phase A audit, already written — keep it
    byte-identical unless you find a factual error, in which case report the
    correction instead of silently editing it)
  - a short `docs/CODEX_TASK_60.md`-style note is NOT required; the audit
    plus the PR body carry the story.
- Push the branch to origin.

## 8. Stop condition

Stop after the scoped commit is pushed and you report:
files changed · tests run with real output · verification results · anything
you deliberately did not do and why.

Do **not** open a PR, do **not** merge, do **not** deploy, do **not** touch
node1/node2. The Hermes orchestrator opens the PR and posts the GitHub
write-back.
