# CEO-OS Issue #60 — Phase A UX audit (Hermes, punkto-worker)

Source of truth: https://github.com/Fisker1111/CEO-OS/issues/60
Audit performed against **live `https://punkto.xyz/`** (node build revision
`dd2f8b2a66b432e00b5a879f1e55c856e980edb5`, publication head
`c77ba862be21e00d37bdc62f35bac7359d09698d19cd4ef8b2ce5be33ff0a9e5`, seq 14).

Verified that the served PWA is byte-identical to `origin/main` `pwa/**`
(sha256 of `index.html`, `app.js`, `ui-text.js`, `ui-map.js`, `ui-board.js`,
`ui-shell.js`, `ui-create.js` all match), so live findings map 1:1 onto the
source tree the PR will change.

## Method

- Browser (Chromium via Browser Use CLI) at 390×844 (mobile portrait, DPR 2),
  360×640 (small Android) and 1440×900 (desktop).
- Read the live static publication directly
  (`/publication/root.json` → `/publication/manifests/<head>.json` →
  `/publication/h/<prefix>/<sha>.json` → `/publication/records/<sha>`) and
  decoded the raw Punkti 0.6 carrier records byte-by-byte.
- Cross-read source: `pwa/index.html`, `pwa/app.js`, `pwa/ui-shell.js`,
  `pwa/ui-text.js`, `pwa/ui-board.js`, `pwa/ui-map.js`, `pwa/sync/punkti-client.js`,
  `pwa/punkti/reader.js`, `pwa/punkti/carrier.js`, `pwa/punkti/spatial.js`,
  `pwa/core/display.js`, `pwa/core/atoms.js`, `pwa/storage/*`.

## Phase A.2 — Does the PWA show real v0.6 published atoms?

**Yes.** Not stale, not demo data.

- `GET /node/info` → `store: {log_lines: 15, valid: 15, candidates: 0}`,
  `peers: ["https://test2.punkto.xyz"]`, `protocol: punkti-mesh/0.6-draft`.
- `GET /publication/root.json` → `{"head":"c77ba862…","seq":14,"v":"punkti/pub/0.6"}`.
- Manifest `record_count: 15`, `pack_count: 0`; walking the sharded tree yields
  **15 records**, all with real `h` spatial addresses, e.g.
  `u3butz7k9q_23`, `u4xsudvxb2_1`, `dqgpuws6qw_1`, `0n5bvnczym_1`,
  `u3butzxby9_23`, `5j529q5e4f_3`, `948w1py22c_1`, `e735djv689_23`,
  `s00000000000_0`, `yspj9wt9u6_17`.
- The live PWA renders exactly those: top bar reads **"15 visible"** after
  sync; the Text feed and the nearby panel show the real titles
  ("Punkto production cutover evidence — CEO-OS #33 node A publish", …).

### `h` semantics — confirmed correct, including ellipsoidal height

`h` is `xy_key` + `_` + `format_z(height)`. Decoding the raw carrier bytes for
`21cbb254…` (record `punkti/0.6:e1865d1e…`, `h = u3butz7k9q_23`):

```
0000 000d 7533 6275 747a 376b 3971 5f32 33   →  "u3butz7k9q_23"
```

So `h` carries **both** the XY geohash-ish key *and* the absolute WGS84
ellipsoidal Z (`23` m), separated by `_`. `parse_h()` in
`pwa/punkti/spatial.js` enforces exactly two parts; `parse_z` rejects
`+23`, `2.3e1`, `023`, `23.`, `−0`, `٢٣`, `23\n`. Z levels are therefore
**not** silently merged: `u3butz7k9q_23` and `u3butzxby9_23` are different
addresses (different XY and different Z suffix semantics are preserved).

### One board = one exact address + one thread — partially true, with a real defect

The reply relation is carried in the carrier's `refs` array
(`{target, rel}`), decoded at `pwa/punkti/carrier.js:337-343`. The live
"node B reply at the same h" record carries exactly one ref:

```
0000 0032 7075 6e6b 7469 2f30 2e36 3a31 3963 6661 6261 3831 3766 6163 6362 6232 3131 6166 3939 6537 6366 4566 3800 0e23 2a94 3231 3461 6337 3865 3262 3332 6239 3761 214a c78e 2b32 b97a 6400 0000 0572 656c 7900 0000 0000 00
   → target "punkti/0.6:19cf1ba8…"   rel "reply"
```

**Defect (F1).** `pwa/sync/punkti-client.js:mapRecordToAtom()` (lines 60-100)
never reads `record.atom.refs`. It builds the UI atom purely from
`payload.meta` (`text`, `author`, `category`, …) plus `record.h`. The reply
relation therefore never reaches the UI layer. Consequences on live data:

- The board sheet for `u3butz7k9q_23` shows **"Replies · 0"** while a reply to
  that exact `h` exists in the same publication.
- The reply appears in the Text feed as an ordinary independent card
  ("…node B reply at the same h" rendered as its own board), not as a reply
  inside its parent's thread.
- `pwa/ui-text.js` already implements thread resolution
  (`isReplyAtom` / `_replyBelongsToRoot` / `_boardReplies` / `resolveBoardAtom`,
  lines 76-118) and `pwa/ui-board.js` renders `Replies · N` + reply composer —
  but it keys off `atom.relation` / `atom.parent_id` / `atom.root_id`, which
  `mapRecordToAtom` never populates for publication-read atoms.

Note `x` payload meta *does* carry `relation: 'reply'` for atoms published
through the current PWA submit path (`pwa/app.js:641-648` writes
`meta.relation`), and `mapRecordToAtom` does read `payload.meta`, but it only
copies `meta.category` and `meta.author` — not `meta.relation`. The live
CEO-OS #33 records were published before that meta existed, so for them the
**carrier `refs`** are the only source of truth.

## Phase A.1 — Observed friction (reproduced, with evidence)

### F1 — Reply threads are not reconstructed from the publication (highest impact)

Evidence: live board sheet for `u3butz7k9q_23` shows `Replies · 0` and
`No public replies yet.`; the same publication contains a signed reply to
that exact `h` (`refs: [{target: punkti/0.6:19cf1ba8…, rel: "reply"}]`).
The Text feed lists that reply as a separate top-level card.
Impact: the "same-place conversation" the Issue asks for is invisible; users
see a board and cannot tell a place has replies.

### F2 — Text view is empty on first visit even though 15 real atoms are published

Reproduction (mobile 390×844, fresh load, no user interaction):
- Top bar shows `15 visible`.
- Switching to **Text** shows `VISIBLE HERE`, `0 visible`, zero cards, and the
  **"Location needed → Enable location"** panel — while the Map view at the
  same moment lists 4 real nearby atoms.
- Desktop 1440×900 reproduces the same: `statusCount = "0 visible"`,
  `main-feed-list` has 0 children.

Root cause (`pwa/app.js:428-476` `refreshUI()`): the feed is scoped to the
**map viewport bounds**, not to the published scope:

```js
const bounds = map.getBounds();
recent = enriched.filter(a => bounds.contains([a.lon, a.lat]))…
```

On a fresh load the map is centred on the default geolocation (or Copenhagen)
at a zoom where none of the 15 published atoms fall inside the viewport, so
`recent` is empty and the Text tab renders the location prompt. The header
count (`elCountNum`, 15) is computed from the *unfiltered* `visibleAtoms`, so
the two numbers disagree — **"15 visible" in the top bar and "0 visible" on
the Text page at the same time**. This is a trust-breaking contradiction for
a first-time visitor.

Also note `pwa/ui-text.js:479` shows the location prompt whenever
`locationDenied || !navigator.geolocation`, even though **location is not
required** to read published atoms — the location prompt is offered in place
of the actual published content.

### F3 — The nearby panel is unreachable on mobile; "Open board on map" is the only path

`#fab-panel` is `display: none !important` (`pwa/index.html:475`, hamburger
removed per `PUNKTO_UI_PRINCIPLES.md`), and the `#panel` bottom sheet is only
reachable via that hidden button or via `setPanelOpen(true)`. On mobile the
panel is therefore effectively dead UI. Consequence: on mobile the only route
to a board is tapping a map bubble, and the panel's per-item button is
mis-labelled **"Open board on map"** (`pwa/app.js:518`) even though it only
*focuses* the map (`focusPunkto(id)` → `focusPunktoOnMap`) and does **not**
open the board sheet. Reproduced: clicking that button moves the map but
leaves the user with no thread.

### F4 — Bottom nav overlaps the nearby panel / onboarding hint on mobile

Measured at 390×844: `#bottom-nav` rect = `[14, 710, 306, 120]`,
`#panel` rect = `[0, 784, 390, 280]` → **46 px vertical overlap**, with
`#bottom-nav` z-index 200 over `#panel` z-index 100. The `#onboarding-hint`
(`.hint-text`, "Move the map, choose a place, then tap + to write a Punkti.")
sits at `bottom: calc(var(--nav-h) + var(--safe-b) + 72px)` and visually
collides with the nav row in the live screenshot (the hint box and the
`+`/2D/+/- controls overlap the Map/Settings buttons region).
There is also **no light/dark switch anywhere** — `grep` for
`prefers-color-scheme` / `data-theme` / `theme` in `pwa/index.html`,
`pwa/ui-settings.js`, `pwa/app.js` returns nothing. The issue lists a
selectable light/dark UI as prior direction; it is absent.

### F5 — "Distance not available" / missing spatial context in the board sheet

Live board sheet meta line reads `10/30/2026 · Floor 8 · Distance not available`.
The floor label is derived from ellipsoidal height via
`fmtAltitudeLabel` (`pwa/core/display.js:43` → `Math.round(alt / 3)`), i.e.
**"Floor 8" is a guess derived from ellipsoidal Z**, not a real floor
attribute, while `meta.floor` exists separately in the payload. The board
sheet shows no coordinate / no `h` / no address at all, so a reader cannot
tell *where* the place is; the trust row says "Verified public post", which
is `isVerifiedAtom` = `Boolean(sig && pubkey)` (`pwa/core/atoms.js:13`) — a
signature+key presence check, **not** a verified-author claim, and not the
`verification_state` from the reader's own `validate()` (which is
`VALID`/`INVALID-provenance`/…).

### F6 — First-run requires GeoHash-ish knowledge; no Explore/Read entry

There is no entry point that explains *Addressability · Distribution ·
Persistence*, and no "Explore" affordance. The only spatial concept exposed
to a first-time user in the Text view is the **"World view filters (static
publication)"** panel with fields literally labelled **"XY prefix (e.g. u3b)"**
and **"Z min"** — raw protocol internals as the first-run UI. The issue
explicitly says "First-run must not require learning GeoHash, MIDs or
cryptography."

### F7 — Trust/QA labelling of demo records

The 15 published atoms are CEO-OS acceptance-evidence records
("Punkto production cutover evidence — CEO-OS #33 …",
"CEO-OS #33 safety-probe acceptance"). They are rendered as ordinary
"Verified public post" boards with no QA/demo marker, and `isHiddenAtom`
(`pwa/core/atoms.js:6-11`) only hides handles `test`, `sync-test`,
`cors-test`, `browser-test` — these atoms carry no such handle, so they are
not filtered. The issue asks to "Mark QA/demo records honestly."

## Chosen THREE improvements (lowest risk, highest user-visible impact)

Per the Issue's prioritisation (a) first-visit Explore/Read entry,
(b) mobile spatial-to-board navigation + contextual place header/back
handling, (c) honest, legible thread/read/reply state + recoverable
loading/error — and the "smallest THREE" constraint:

**I1 — Honest thread/read/reply state (fixes F1, F5).**
Carry the carrier `refs` reply relation through `mapRecordToAtom` into the UI
atom (`relation`, `parent_id`, `root_id`) and read `meta.relation` /
`meta.parent_id` / `meta.root_id` from the payload meta, so a real
same-place reply is reconstructed as a reply in its parent's thread. Show the
board's exact spatial address and coordinates, and state the address/height
honestly (absolute WGS84 ellipsoidal Z, with `meta.floor` used for the floor
label rather than a floor guessed from Z).

**I2 — First-visit Explore/Read entry (fixes F2, F6).**
Make the Text tab show the real published atoms that the header count
already claims (scope-consistent, not viewport-only), and give a first-visit
user a plain-language way in that does not require the "XY prefix" jargon:
a short "Addressability · Distribution · Persistence" explainer plus an
Explore action, with the raw scope filters demoted behind a disclosure. Do
not show a "Location needed" wall in place of published content that is
already available.

**I3 — Mobile spatial→board navigation + contextual place header / back
handling (fixes F3, F4, F7).**
Give mobile a working route from a place to its board and thread (and stop
the mis-labelled "Open board on map" button from silently only focusing the
map); make the board sheet's back action return to the place it came from;
stop the bottom nav / onboarding hint from overlapping on small viewports;
and mark QA/demo records honestly instead of presenting them as ordinary
"Verified public post" boards.

Explicitly **out of scope** (per the Issue): no signer/crypto protocol
changes, no DB schema migration, no worker, no Caddy/GoDaddy/backend service
change, no public write-default change, no test-key writes, no deployment,
no `/ai` breakage. Light/dark switch is not required for the three chosen
improvements and is left out to keep the PR small (F4's overlap fix is
included; the theme switch is not).
