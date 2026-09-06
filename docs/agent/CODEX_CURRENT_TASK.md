# Codex Current Task

Status: **ACTIVE — Slice 5 review correction: print/PDF robustness + hard CI gate**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Context

Slice 5 implementation commit under review:

`d05c55ea0ae54b177ab69c008c7b14188fa763b6`

Commit:

`feat(pilot1): finish Punkto for field release`

Pilot CI run `34040922877` / #159 is green, but review found two concrete print/PDF issues and one validation-gap that must be corrected **before AZ deployment**.

Do not broaden Slice 5. Preserve the completed identity, exact-link, visual, placement, board, signing, storage, relay and federation work.

## 1. Preserve ordinary user text in the A4 PDF

Current `pwa/print-pdf.js` `pdfEscape()` replaces every non-ASCII character with `?`.

That is not acceptable for the Pilot_1 print loop: ordinary Danish text such as `æ ø å Æ Ø Å` and common Western-European punctuation must print correctly rather than being corrupted.

Implement the smallest lightweight fix appropriate for the current hand-built PDF approach.

Requirements:

- at minimum preserve common Western-European/WinAnsi text correctly, including Danish `æøåÆØÅ`, `é`, `ü`, `€`, curly quotes/dashes where representable, and the middle dot `·`;
- declare/use the correct PDF font encoding for the bytes emitted (e.g. WinAnsi if keeping standard Helvetica);
- do not silently corrupt those characters to `?`;
- unsupported characters outside the chosen lightweight Pilot_1 encoding may degrade visibly/fallback safely, but must not break PDF generation;
- keep the PDF client-side and lightweight; do not add a large font framework or remote dependency unless absolutely necessary;
- keep the message the strongest object on the page;
- keep long-message truncation notice behavior.

Also make the footer exactly:

`punkto.xyz · leave a message here`

not a hyphen substitute.

## 2. Give the QR a real quiet zone

The current PDF draws the QR matrix at 250 pt with only ~12 pt of white space before a black outline. For the exact atom URL this is generally less than the standard four-module quiet zone and is unnecessarily fragile for office/home printing.

Make the printed QR robust:

- provide a white quiet zone of at least **4 QR modules on every side**;
- do not place a black border inside that quiet zone;
- if a decorative border remains, place it outside the required quiet zone or remove it;
- keep QR high-contrast black/white and large;
- QR payload must remain the exact canonical atom URL.

## 3. Turn Slice 5 helper tests into a hard CI gate

`pwa/test-slice5.mjs` exists, but Pilot CI #159 did not execute it. The PWA validation job currently only syntax-checks modules.

Update `.github/workflows/pilot-ci.yml` so the hard PWA validation job runs the deterministic Slice 5 helper test:

```bash
node pwa/test-slice5.mjs
```

Extend `pwa/test-slice5.mjs` as needed to cover the corrected print behavior, including:

- valid `%PDF` / A4 geometry remains true;
- exact canonical URL remains in PDF / QR payload;
- secrets remain absent;
- Danish/WinAnsi sample text does not become corrupted question marks;
- footer uses the middle dot text;
- QR layout helper or deterministic geometry check proves >= 4-module quiet zone.

Keep tests deterministic and network-free.

## Scope lock

Prefer only:

- `pwa/print-pdf.js`
- `pwa/test-slice5.mjs`
- `.github/workflows/pilot-ci.yml`
- this task file

Do **not** modify:

- placement interaction;
- `ui-map.js` unless absolutely required (it should not be);
- identity/key protocol;
- signing;
- exact-link identity semantics;
- board/reply behavior;
- relay/federation;
- node/server/deployment config;
- production/main.

## Checks

Run:

```bash
node --check pwa/print-pdf.js
node pwa/test-slice5.mjs
node --check pwa/app.js
node --check pwa/ui-map.js
python3 relay/test_relay.py
git diff --check
```

The exact pushed correction SHA must then receive green Pilot CI with the Slice 5 helper test visible in the hard PWA validation job.

## Completion contract

Before commit, set status to:

`Status: **HOLD — Slice 5 print/CI correction implemented, awaiting review**`

Commit exactly:

`fix(pilot1): harden Punkti PDF and Slice 5 CI`

Push to `origin/pilot-1`, report exact SHA/checks, then stop.

Do not deploy. Do not merge to main. Do not start Slice 6.
