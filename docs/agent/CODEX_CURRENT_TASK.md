# Codex Current Task

Status: **HOLD — Slice 4 implemented, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Goal

Implement Pilot_1 **Slice 4 — Fast create**.

The product path to optimize is:

> **Tap `+` → type → publish → return to the world**

This slice should make the ordinary public-post path feel immediate and obvious on mobile while preserving all existing signing, public-data acknowledgement, category, location, altitude, storage, relay, and federation semantics.

Pilot_1 target:

> An urgent post should be accepted as a signed atom in under 20 seconds p95 on the named reference device/network.

Do not redesign the rest of Punkto. This is a focused create-flow slice.

## Starting state

Before editing:

1. Read `AGENTS.md`, `docs/PILOT_1_IMPLEMENTATION.md`, and `pwa/ARCHITECTURE.md`.
2. Confirm branch is `pilot-1` and working tree is clean.
3. Inspect the current create path in `pwa/ui-create.js`, create markup/CSS in `pwa/index.html`, and the narrow create orchestration/submission path in `pwa/app.js`.
4. Preserve the Slice 3.6 module boundaries: create UI belongs in `ui-create.js`; do not move Map/board implementation back into `app.js`.
5. Do not change test1/node1/node2 operations. A real human-created atom has already proven test1 write + federation through the ordinary relay path.

## Product contract

### Primary simple path

For a returning/acknowledged user, opening `+` should immediately present a calm, obvious composer with:

- message field as the dominant control;
- current anchor/location understandable at a glance;
- category/type accessible without turning the sheet into a settings form;
- one obvious primary **Publish** action;
- Cancel/close secondary;
- text focus quickly after opening.

Normal posting should not require interacting with altitude, floor, author, device-altitude, or other advanced controls.

### Progressive disclosure

Keep advanced location/altitude/author controls available, but collapse them behind one clear secondary disclosure such as **Location & options** / **More options**.

The default simple path should not visually expose the full altitude/floor control stack.

Preserve the existing capabilities when expanded:

- author/display-name editing;
- ground/floor/manual altitude behavior;
- roof/building behavior when available;
- device-altitude option;
- placement preview/location behavior;
- category behavior and emergency hint.

Category may remain visible in the primary composer if that is the clearest way to keep urgent posting fast. Do not hide Emergency behind several taps.

### Public-data acknowledgement

Preserve first-use acknowledgement as a real gate.

- It must clearly communicate that the post is public.
- A first-use user must not accidentally publish before acknowledging.
- After acknowledgement, focus should move naturally into the message field.
- Returning users must not be forced through the acknowledgement again.

Do not add legalistic copy or a multi-step onboarding flow.

### Fast-open discipline

Opening the create sheet must not wait for optional device-altitude/geolocation work.

In particular, the current `requestDeviceAltitude()` behavior must not create friction or a permission prompt on every ordinary `+` open. Defer optional high-accuracy/device-altitude work until the user explicitly opens/uses the relevant advanced control.

Composition must remain available even while optional spatial enhancement is unresolved.

### Publish behavior

Preserve the existing write path:

- canonical Punkto location encoding;
- existing signing behavior;
- normal `postAtomToNetwork(...)` path;
- local `upsertAtom(...)` after accepted post;
- normal sync/federation behavior;
- return to the Map/world after success;
- no special test-only write endpoint.

Make the UI robust against accidental duplicate submits:

- Publish disabled while submitting;
- empty/whitespace-only text must not publish;
- first-use acknowledgement must still gate Publish;
- Ctrl/Cmd+Enter may remain a shortcut only when the form is eligible to publish.

On failure, keep the user's composed text/options in place and show the existing inline error rather than discarding the draft.

### Spatial context

Successful publish should return to the same spatial context and show the newly posted atom through the normal refresh path.

Do not introduce a camera jump unrelated to the chosen anchor.

The create flow must not invent a separate map/camera or encode reply/order semantics into altitude.

## Visual direction

This is not a full visual redesign. Keep the established Candidate 4 / Candidate 5 language:

- warm, calm, public, mobile-first;
- message first;
- simple primary action;
- advanced controls secondary;
- no cyberpunk/debug-console feel;
- no fake activity or gamification.

A modest create-sheet CSS/markup cleanup is expected if necessary to make the fast path clear.

## Version marker

This is new visible product behavior. Update the PWA marker from the Slice 3 marker to:

`pilot1-slice4-fast-create-2026-08-20-1`

Update both the console marker and `window.PUNKTO_APP_VERSION` consistently.

## Expected scope

Prefer the smallest coherent set:

- `pwa/ui-create.js`
- `pwa/index.html`
- `pwa/app.js` only for narrow create orchestration/version marker changes if needed
- `pwa/ARCHITECTURE.md` only if the actual module API/ownership changes materially
- `docs/agent/CODEX_CURRENT_TASK.md`

Touch another PWA file only if required for a small mechanical integration change.

Do **not** edit:

- relay/protocol formats;
- signing/identity semantics;
- storage schema;
- peer discovery/sync cadence;
- deployment/Caddy/Docker configuration;
- node1/node2 production code/config;
- Map/board product behavior unrelated to create.

## Acceptance criteria

The slice is acceptable when all are true:

1. `+` opens a create sheet where the message field is the obvious first action.
2. Returning acknowledged users can type and publish without opening advanced controls.
3. Text is focused promptly on ordinary open.
4. First-use public acknowledgement remains a blocking one-time gate and hands focus to the composer after acceptance.
5. Full altitude/floor/author controls are hidden by default but still available and functional through one clear disclosure.
6. Optional device-altitude/geolocation work does not run/prompt merely because the create sheet opened.
7. Category selection remains easy enough for a fast Emergency/Warning post; Emergency hint still works.
8. Empty text cannot be published.
9. Double-submit is prevented while a post is in flight.
10. Failed submission preserves the draft and shows inline error.
11. Successful submission still signs/posts/stores through the existing normal path and returns to the same world context.
12. Placement preview, ground level, floor/manual altitude, roof/building behavior, and altitude-only Z semantics remain intact.
13. `Text | Map | + | Settings`, board behavior, map selection, sync, settings and identity/key behavior are unchanged outside the create flow.
14. Version marker is exactly `pilot1-slice4-fast-create-2026-08-20-1`.
15. No deployment or ops files are changed.

## Automated checks

Run at minimum:

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
node --input-type=module --check < pwa/ui-create.js
python3 relay/test_relay.py
git diff --check
```

Do not modify relay files to influence relay results.

## Focused create-flow checks

Where practical with a local/static browser session, verify without creating public test network activity:

- acknowledged user: `+` → composer ready/focused, advanced section closed;
- Publish disabled for empty text and enabled for valid text;
- category can be changed to WARN/EMGC quickly and emergency hint remains correct;
- first-use acknowledgement blocks Publish, then acknowledgement focuses message field;
- open/close advanced options and exercise ground/floor/manual/roof controls without console/deck.gl errors;
- confirm opening create does **not** request optional device altitude automatically;
- close/reopen resets the draft as before while persisted acknowledgement/author remain preserved;
- Cancel and Escape still close safely;
- no uncaught module/runtime errors.

Do not fabricate additional public atoms merely to satisfy Codex testing. Live write-path verification will happen on test1 after review/deploy.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4 implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`feat(pilot1): streamline fast create flow`

Then:

1. commit only the Slice 4 implementation + task-status/doc changes;
2. push to `origin/pilot-1`;
3. report exact SHA, files changed, automated checks, focused create-flow checks, and any uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 5. ChatGPT will inspect the pushed exact SHA and Pilot CI before any test1 deployment authorization.
