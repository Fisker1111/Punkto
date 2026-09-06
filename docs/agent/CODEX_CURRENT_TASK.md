# Codex Current Task

Status: **HOLD — Slice 5 implemented, awaiting CI/review and test1 deployment**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Mission

Implement the **one large final product-development slice on test1** before production release.

There are no more 4.5 micro-slices. The height-placement interaction is human-accepted and closed for now.

Slice 5 must turn the current Pilot_1 into a coherent, field-ready Punkto product in one coordinated implementation pass:

1. finish Punkto's visual identity;
2. make identity/key creation understandable and persistent for ordinary users;
3. add exact stable atom deep links;
4. add **Print this Punkti** as a downloadable A4 PDF with QR back to the exact atom;
5. harden field/PWA/offline/error/accessibility behavior;
6. preserve all accepted spatial, signing, storage, relay, federation, board, and creation behavior.

This is deliberately a **big slice with one final acceptance gate**. You may use multiple focused commits internally if useful, but the final pushed `pilot-1` HEAD must contain the complete Slice 5 implementation, the task must be returned to HOLD, the worktree must be clean, and the final exact SHA is the only deployment candidate.

## Starting point / locks

Latest accepted application behavior includes the deck-overlay CSS fix from:

`71053f1743c9982f0ce1420ae99beedc0bdb440a`

Current coordination baseline after closing Slice 4.5:

`2015833cdaa98d0aece647a3d3403ca088a932e9`

The accepted creation interaction is locked:

> **Aim with center sight → `+` locks x/y → choose physical height → Done → Write → Publish.**

Permanent product invariants:

- message is the primary social object; author is secondary;
- public signed atoms, not encrypted/private messages;
- exact real-world geographic anchoring;
- Z-axis means **physical altitude only**;
- replies remain flat board/thread UI, never vertical ordering;
- independent atoms remain independent;
- no likes, follower counts, engagement ranking, or synthetic story merging;
- every visible beacon resolves to a real atom;
- MapLibre remains the authoritative world/camera;
- do not replace the MapLibre/deck.gl architecture;
- signing proves authorship/integrity, not secrecy.

Do not redesign the accepted height-placement philosophy. Fix obvious visual duplication/clutter only.

---

# A. Visual identity — make Punkto recognizable

The app should no longer read as generic "MapLibre + controls + dots".

Apply a coherent lightweight Punkto design language across map, beacons, selected state, board, composer, identity, settings, and print actions while staying fast on ordinary phones.

Target feeling:

**warm · spatial · calm · public · curious · useful · slightly alive**

Requirements:

- preserve the warm recognizable basemap and readable roads/water/buildings;
- beacons/atoms should have one consistent proprietary Punkto visual grammar across normal, selected, elevated, urgent, and draft states;
- exact ground anchor + thin vertical relation + top atom remain the altitude signature;
- selected atom remains unmistakably selected without becoming loud/cyberpunk;
- use restrained glow/motion only; no black void, neon overload, heavy assets, character art, or game UI;
- typography, surfaces, spacing, buttons, board, composer, settings and new identity/print surfaces should feel like one product;
- mobile first, but desktop must remain coherent;
- respect `prefers-reduced-motion`;
- preserve the lower-left/hero `+` contribution affordance;
- remove obvious duplicate placement information. In particular, the accepted mobile screenshot currently shows the `+64 m · ~Floor 21` information twice. Keep one clear UI readout plus the world geometry rather than duplicate floating labels;
- do not sacrifice map/world readability for visual branding.

Brutal screenshot test:

> If the Punkto word/logo were hidden, the combination of beacon/anchor/stem, surfaces and interaction should still look intentionally like Punkto rather than a stock map demo.

Keep this lightweight: CSS/procedural deck.gl treatment is preferred over images/heavy assets.

---

# B. Your Punkto Identity — normal-user key UX

Do not present ordinary users with a crypto tool. Build a simple user-facing identity experience, preferably integrated into Settings or a dedicated panel reachable from Settings.

Primary title:

**Your Punkto Identity**

Primary first-use action:

**Create my identity**

After creation show, in human language:

- Punkto ID / author ID;
- status such as **Saved on this device**;
- **Download backup**;
- **Show recovery words**;
- **Import existing identity**.

Use the existing cryptographic primitives in `pwa/key-management.js`. Existing code already provides BIP39 mnemonic generation, PBKDF2 seed derivation, Ed25519 key creation, author ID generation, signing/verification, JSON export/import. **Do not invent a new key format, signature system, cipher, KDF, or identity protocol.**

Persistence requirements:

- active identity must survive browser/app restart on the same device;
- use existing IndexedDB/Dexie infrastructure (`storage/db.js`; `meta` may be used if appropriate) or an equally local existing persistence mechanism;
- private signing/recovery material stays local to the device and is never uploaded as part of identity setup;
- do not falsely claim browser storage is hardware-secure;
- clearly tell the user that clearing browser/app data can erase the local identity unless they keep a backup/recovery words;
- never silently replace an existing identity;
- importing/replacing/forgetting an identity must be deliberate and guarded by a clear confirmation;
- safely detect/reuse any identity already used by the current PWA if one exists; do not strand or overwrite an existing user identity during migration;
- backup JSON should remain compatible with the existing Punkto key export semantics; a filename such as `punkto-identity-<author>.punkto-key.json` is appropriate;
- support import from that JSON backup;
- support recovery/import from the 12-word mnemonic using the existing derivation path;
- after import/recovery, verify that derived public key/author ID are internally consistent before activating;
- signing of new atoms must use the active persisted identity without forcing the user through key setup on every publish.

Security/product rule:

> Easy first use, explicit backup, no fake security claims.

Do not add mandatory passwords, cloud accounts, WebAuthn, native keychain, or server-side key escrow in Slice 5.

---

# C. Exact atom identity + stable deep links

The current spatial/deep-link behavior is insufficient when multiple independent atoms occupy the same place. Implement a canonical public link that resolves to **one exact atom**.

Preferred public shape:

`/p/<exact-atom-id>`

Requirements:

- inspect the existing relay/client atom model and use the existing stable/canonical protocol atom identity (`atom_id` or equivalent) when available;
- **do not use Dexie auto-increment row IDs** or any device-local identifier in public URLs;
- if the client must derive an atom ID, it must match the relay's existing canonical atom identity algorithm exactly; do not create a second identity scheme or protocol extension;
- opening an exact link must load/focus/select that exact atom and open its board/root context even if other atoms share its coordinates;
- copy/share actions from an atom should emit the exact canonical link;
- preserve old spatial/query links as backward-compatible fallbacks where practical; do not break existing QR/links unnecessarily;
- Caddy/server routing assumptions must remain compatible with SPA fallback. If a deployment/Caddy change is genuinely required, document it for AZ but do not edit production server state;
- canonical public origin must be configurable/current-origin for test1, but production links must naturally resolve on `https://punkto.xyz` after Slice 6 without hardcoding test1.

Add deterministic tests/helpers where practical for exact-ID lookup and same-location ambiguity.

---

# D. Print this Punkti — A4 PDF + QR

From a public atom/board provide an obvious action:

**Print this Punkti**

Generate a downloadable **A4 PDF client-side** suitable for an ordinary black/white office/home printer.

The paper is a physical bridge back to the exact public atom:

> **digital atom → paper → scan → exact digital atom**

A4 layout requirements:

- use the A4 sheet generously; do not leave most of the page empty;
- black/white or grayscale first; it must print cleanly on almost any printer;
- the atom/message text is the strongest object on the page;
- large, high-contrast, robust QR code;
- QR resolves to the **exact canonical atom deep link**, never only the geographic position;
- minimal supporting metadata only when useful (for example date/place/author ID in subdued small type);
- tiny footer around 8 pt:

`punkto.xyz · leave a message here`

- do **not** use abstract slogans on the A4;
- generated file name should be sensible and deterministic enough for users to find;
- support long messages gracefully: wrap/truncate only with a clear indication if unavoidable; QR must remain large enough to scan;
- PDF generation must work fully in the browser; no server PDF service and no upload of private material;
- do not place recovery words/private keys in the PDF.

Dependency rule:

- first inspect existing vendored libraries;
- if QR/PDF generation needs a small library, prefer a well-scoped vendored client-side dependency under `pwa/lib` with license preserved/documented;
- do not introduce runtime CDN dependencies or require network access to a third-party QR/PDF service;
- keep payload/performance reasonable.

The output must be an actual downloadable PDF, not merely a print-dialog-only HTML page.

---

# E. Field hardening / PWA completion

Finish the flows required for a real Pilot_1 field deployment without broadening the protocol.

## Network / publish behavior

- relay/network failure during publish must be visible and understandable; never silently pretend a publish succeeded;
- a failed publish must not destroy the user's written message/draft;
- prevent accidental duplicate publish from repeated taps/retries where feasible;
- interrupted/reconnected use must return to a coherent state;
- existing signing, relay-first publish semantics, peer/federation behavior and human-created data must remain intact;
- do not redesign relay protocol or federation.

## Offline / local behavior

- app should remain comprehensible when relay/network is unavailable;
- locally cached/stored atoms may remain readable when available;
- creation can be composed offline, but if current protocol requires server acceptance before persistence, clearly represent it as unsent/not published rather than forging success;
- no fabricated activity.

## PWA/cache sanity

Inspect the manifest/service-worker situation and make it production-safe.

- avoid stale-code traps after deployment;
- installability/app-shell behavior should work where supported;
- choose conservative cache semantics: HTML/JS deployment freshness is more important than clever offline caching;
- if enabling/reworking the service worker, include a clear version/update strategy and do not cache relay API writes/responses in a way that changes semantics;
- map tile/provider caching must respect browser/provider behavior; do not start a self-hosted tile project;
- `reset.html`/fresh-state developer behavior must remain usable if present.

## Accessibility / reduced motion / weak devices

- keyboard/focus behavior for board, composer, identity, dialogs and print actions;
- readable contrast and meaningful labels/ARIA on important controls;
- no color-only meaning for urgent/selected states;
- reduced-motion mode preserves meaning without pulses/large transitions;
- avoid expensive animation loops or excessive deck layers on weak phones;
- touch targets remain practical on mobile.

## Required product states to re-check

- nearby opening;
- honest empty neighborhood;
- one atom and several atoms;
- selected atom + board;
- root/replies;
- fast create;
- Ground and elevated placement;
- urgent atom treatment;
- Text equivalent view;
- Settings;
- identity create/import/backup/recovery;
- exact deep link;
- print PDF + scan destination;
- network failure/offline recovery;
- mobile and desktop.

---

# F. Preserve the kernel — explicit exclusions

Do **not** add or redesign:

- encryption/private messaging;
- likes/followers/popularity/trending;
- profiles/social graph;
- automatic merging of atoms/events;
- confirmation/dispute/resolution protocol;
- expiration protocol;
- new media/attachment system;
- native app/Capacitor;
- self-hosted global basemap;
- semantic-zoom world architecture beyond current lightweight clustering;
- custom Three.js second camera/world;
- moderation federation redesign;
- new altitude datum/protocol semantics;
- production/main deployment.

If you discover an issue that would require one of those, document it as a post-Pilot/RFC note and keep Slice 5 moving.

---

# Acceptance gate — one finished-product test

Slice 5 is complete only when this end-to-end story is technically supported:

> **A stranger opens Punkto, understands that public messages are attached to places, creates or imports a Punkto identity, aims and places a Punkti at Ground or physical height, writes and publishes it, opens the exact atom board, downloads an A4 PDF, scans/opens the QR deep link, and returns to that exact public atom.**

Also verify:

1. accepted height placement still works; yellow draft + anchor/stem visible, right-side lever usable, no height-driven zoom regression;
2. no duplicated height readout clutter;
3. existing human atoms still render/read;
4. exact link distinguishes independent same-location atoms;
5. identity persists across reload and backup/recovery round-trip restores the same author ID;
6. secrets are not sent to relay/network during identity setup/backup generation;
7. PDF is valid A4, opens in a normal PDF viewer, QR encodes exact public link, and B/W layout is readable;
8. failed network publish is honest and preserves user text;
9. Text/Map/Settings/board/reply flows still work;
10. fresh/private browser has no uncaught module/runtime errors;
11. mobile layout has no blocking overlap at common narrow viewport;
12. desktop remains usable;
13. reduced motion works;
14. no relay/protocol/federation regression.

Human visual/product verification on test1 remains mandatory after AZ deployment.

---

# Version marker

Set a clear Slice 5 runtime marker exactly:

`pilot1-slice5-finish-punkto-2026-09-06-1`

The marker must be visible through the existing app version mechanism used by deployment verification.

---

# Expected code areas

Inspect before editing. Expected legitimate scope may include:

- `pwa/index.html`
- `pwa/app.js`
- `pwa/ui-shell.js`
- `pwa/ui-map.js`
- `pwa/ui-board.js`
- `pwa/ui-create.js`
- `pwa/ui-settings.js`
- `pwa/ui-text.js` if needed for equivalent actions/state
- `pwa/key-management.js`
- `pwa/storage/db.js`
- `pwa/sw.js`
- `pwa/manifest.json` or equivalent manifest if present
- small new PWA modules for identity, exact-link, QR/PDF generation if that produces cleaner ownership
- small vendored `pwa/lib` dependency only if required for local QR/PDF generation, with license preserved
- focused tests/docs needed to make behavior reviewable
- this task file

Do not edit relay/protocol/server/node configuration unless a test fixture or documentation-only note is unavoidable. No deployment files should be changed to perform the live release.

---

# Required checks before final push

Run all existing Pilot CI-compatible checks plus any new tests you add.

At minimum:

```bash
node --check pwa/app.js
node --check pwa/ui-shell.js
node --check pwa/ui-text.js
node --check pwa/ui-map.js
node --check pwa/ui-board.js
node --check pwa/ui-create.js
node --check pwa/ui-settings.js
node --check pwa/key-management.js
node --check pwa/sw.js
node --input-type=module --check < pwa/app.js
node --input-type=module --check < pwa/ui-map.js
node --input-type=module --check < pwa/ui-board.js
python3 relay/test_relay.py
git diff --check
```

Add deterministic local tests where practical for:

- identity backup/recovery same-author round trip;
- canonical exact-link generation/parsing/lookup;
- PDF generation produces `%PDF` bytes / valid page geometry and expected canonical URL payload;
- QR payload helper exactly equals canonical exact atom URL;
- no secrets included in share/print payload.

If browser automation is available, smoke-test the major flows. Do not fabricate public atoms against production nodes.

---

# Completion contract

Before the final push:

1. set this task status to:

`Status: **HOLD — Slice 5 implemented, awaiting CI/review and test1 deployment**`

2. ensure the final `pilot-1` worktree is clean;
3. push all Slice 5 commits to `origin/pilot-1`;
4. report the final exact SHA and concise check results;
5. stop. **Do not deploy. Do not merge to main. Do not start Slice 6.**

Suggested final commit message if using a single squashed implementation commit:

`feat(pilot1): finish Punkto for field release`

If using several focused commits, keep them all inside this one Slice 5 and make the final HEAD the complete deployable candidate.
