# AZ Current Task

Status: **ACTIVE — deploy reviewed Slice 5 release candidate to test1**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Mission

Deploy the complete reviewed **Slice 5 — Finish Punkto** application to **test1 only** for final human product acceptance.

Deploy exactly this application SHA:

`cbdf113359443e293f1d478396becc0ed0ca40cc`

Commit:

`fix(pilot1): harden Punkti PDF and Slice 5 CI`

This SHA contains the full Slice 5 implementation plus the reviewed PDF/QR/CI correction.

Pilot CI:

- Run: `34055957982`
- Number: `#163`
- Result: **green**
- PWA validation: PASS
- Slice 5 deterministic helper tests: PASS
- Relay regression suite: PASS

Expected runtime marker:

`pilot1-slice5-finish-punkto-2026-09-06-1`

## Critical deployment rule

**Do not deploy the moving `pilot-1` branch tip.** The branch will advance when this AZ task file is committed. Export/deploy only `pwa/` from exact application SHA `cbdf113359443e293f1d478396becc0ed0ca40cc` using Git-object based deployment such as `git archive`.

## Before deploy

1. Confirm test1 currently serves the accepted Slice 4.5 build and relay is healthy.
2. Back up the currently served test1 PWA to a clearly timestamped rollback directory.
3. Record test1 relay/container/volume health and current human atom count/buffer state.
4. Do not modify relay data, node identity, federation configuration, Caddy relay proxy behavior, node1, or node2.

## Deploy

Replace only the test1 static PWA with `pwa/` from exact SHA `cbdf113359443e293f1d478396becc0ed0ca40cc`.

No product-code edits. No relay/protocol edits. No production/main deployment.

## Required served-file proof

After deployment, compare SHA-256 of served bytes against Git-object bytes from exact application SHA for at least:

- `app.js`
- `index.html`
- `ui-map.js`
- `ui-board.js`
- `ui-text.js`
- `key-management.js`
- `print-pdf.js`
- `protocol/exact-link.js`
- `lib/qrcode-generator.js`

Curl-confirm the runtime marker:

`pilot1-slice5-finish-punkto-2026-09-06-1`

## Browser / runtime verification

Use a fresh/private browser where possible. Verify without fabricating production/public data:

1. PWA boots with no uncaught module/runtime errors.
2. Map renders and existing human-created atoms remain visible/readable.
3. Accepted height placement still works structurally: yellow draft canvas remains visible, right-side lever present, no height-driven zoom behavior introduced.
4. Settings exposes **Your Punkto Identity** with:
   - Create my identity
   - Import existing identity
   - Download backup
   - Show recovery words
5. If safely automatable using isolated browser-local state, create a temporary local identity and verify persistence across reload, backup generation, and mnemonic/import round trip. Do not expose recovery words/private material in GitHub comments or durable logs.
6. An exact atom board exposes **Copy exact link** and **Print this Punkti**.
7. Exact links use `/p/<64-hex-atom-id>` and resolve to the exact atom when the atom exists locally/synced.
8. Generate an A4 PDF from an existing legitimate public atom if browser tooling allows this without posting anything. Verify:
   - valid downloadable PDF;
   - A4 geometry;
   - QR payload points to exact test1 `/p/<atom_id>` URL;
   - four-module QR quiet zone is present by code/test evidence;
   - footer text is exactly `punkto.xyz · leave a message here`;
   - Danish/WinAnsi sample text support is present; do not create a public test atom merely to verify characters.
9. Existing board/reply/Text/Settings/create/cancel flows still load coherently.
10. If network-failure behavior can be inspected non-destructively, confirm publish errors preserve draft text; do not intentionally corrupt relay state.

If the browser environment lacks WebGL or other capabilities, state the limitation clearly and do not claim visual acceptance that was not actually observed.

## Data / federation safety

After deployment confirm:

- test1 relay health is OK;
- persistent test1 relay volume remains attached and unchanged;
- existing human-created atoms are still present;
- node1 and node2 are untouched and still serve their prior marker/configuration;
- no AZ-fabricated public atom was created.

## Human acceptance remains mandatory

AZ may verify deployment and technical runtime behavior, but the user is the final product gate for Slice 5. Do not claim the visual design, identity UX, print layout, or end-to-end field experience is accepted until the human tests it.

## Report

Report:

- exact deployed application SHA;
- backup/rollback path;
- served-file hash proof;
- runtime marker;
- browser/runtime result and limitations;
- identity UX/persistence checks performed;
- exact-link checks;
- PDF/QR checks;
- relay/data/federation health;
- node1/node2 untouched;
- blockers/unexpected behavior.

If direct PR posting is unavailable, save a DEPLOY block locally for ChatGPT to post.

## Stop rule

After test1 verification, stop.

- Do not deploy to node1/node2.
- Do not merge PR #110.
- Do not deploy `main` or `punkto.xyz`.
- Do not retire test1.
- Do not begin Slice 6 until explicit ChatGPT/product authorization after human Slice 5 acceptance.
