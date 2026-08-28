# Codex Current Task

Status: **HOLD — Slice 4.5C implemented, awaiting CI/review**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`

## Why this task exists

Human testing of deployed Slice 4.5B2 (`d6541b9f3cc67bcc7e302cc68201c52ba1b054ce`) accepted the core spatial creation philosophy:

> **The sight chooses place. The lever chooses height. The world shows both.**

The interaction works. Do **not** redesign it.

The remaining problem is visual hierarchy and finish. On the normal 3D world view, the most important action — creating a Punkti — is still not visually dominant enough. The current shell gives Text / Map / + / Settings too much equal weight, and the world graphics can be improved one notch without becoming heavy or decorative.

The next product decision is locked:

> **`+` is the hero action. Everything else is supporting navigation.**

The user specifically expects the primary `+` action to live at the **bottom-left**, remain obvious on the main 3D view, and be substantially larger / stronger than Text, Map, and Settings, which should remain nearby but smaller and quieter.

This task is polish, hierarchy, and graphics only. Preserve all proven behavior.

## Starting state

1. Start from current `pilot-1` HEAD.
2. Read `AGENTS.md`, `pwa/ARCHITECTURE.md`, current `pwa/ui-shell.js`, `pwa/ui-map.js`, `pwa/ui-create.js`, `pwa/app.js`, and `pwa/index.html` before editing.
3. Preserve the deployed Slice 4.5B2 creation workflow exactly:
   - aim with center sight;
   - `+` locks x/y;
   - height lever controls physical height;
   - world renders anchor + stem + beacon;
   - buildings ghost during height placement;
   - `Done` then opens the writing composer;
   - Publish uses the existing signed/public atom path.
4. Preserve MapLibre as the authoritative spatial camera and deck.gl as the Punkto spatial overlay.
5. Preserve protocol/storage/signing/relay/federation behavior exactly.
6. Preserve selected-atom board, Text view, Settings behavior, deep-link behavior, and existing Pilot height semantics.

## Product hierarchy

The main world should visually communicate, without explanation:

1. **Look around the world.**
2. **Press `+` to leave something here.**
3. Text / Map / Settings are available, but secondary.

The create action is not one nav tab among equals. It is the primary action of Punkto.

## Required change A — make `+` the hero action

### Placement

On the normal Map / 3D world view:

- place the persistent create button at the **bottom-left**;
- it must be easy to find immediately on both desktop and mobile;
- it must not collide with MapLibre controls, map attribution, browser safe areas, board UI, or the height-placement controls;
- during the dedicated height-placement stage, the existing focused placement UI may still suppress the shell as it does today.

### Visual weight

The `+` button must be unmistakably more important than other shell controls.

Target character:

- large circular or softly rounded control;
- roughly 60–72 px visual diameter on desktop, with a touch target at least 56 px; mobile must remain thumb-friendly;
- strong Punkto blue/cyan identity with restrained depth/glow;
- large, crisp plus glyph;
- clear hover/focus/pressed states;
- no constant distracting pulsing animation;
- a subtle one-time / onboarding emphasis is acceptable if already compatible with current onboarding behavior.

The button should feel like **“leave a Punkti here”**, not “open generic menu”.

Do not add a long permanent text label that clutters the map. A very compact supporting hint may be used if it materially improves first-use comprehension, but the symbol/button itself must carry the action.

### Interaction

Do not change what `+` does. It must invoke the current accepted B2 flow unchanged.

## Required change B — supporting controls live nearby but become quieter

Text, Map, and Settings should remain accessible near the same bottom-left shell area, but should be clearly subordinate.

Desired relationship:

```text
small supporting controls
[Text] [Map] [Settings]

[      +      ]   ← hero
```

or an equally compact vertical / clustered treatment that works better responsively.

Requirements:

- support controls must be visibly smaller and lower contrast than `+`;
- active Map/Text state must remain clear but calm;
- Settings remains reachable without competing for attention;
- preserve existing `data-nav-action` / shell behavior where practical;
- do not introduce a hamburger/menu layer just to hide these three actions;
- minimum touch target about 44 px even if visual chrome is smaller;
- the group should feel like one purposeful bottom-left instrument cluster, not a large opaque navigation panel;
- reduce the current feeling of a tall/heavy side rail on desktop and an equally weighted bottom dock on mobile;
- map should remain visually dominant.

If a shared responsive shell can replace duplicated desktop rail / mobile dock styling without risky JS changes, prefer that. Do not perform an unrelated shell rewrite.

## Required change C — improve world graphics one notch

This is **not** a redesign and not a new art system. Refine the current MapLibre/deck.gl presentation so the 3D world looks more deliberate and easier to read.

### Buildings

Current extrusions are functional but read as heavy gray blocks. Improve them modestly:

- use a lighter / warmer neutral building treatment that sits naturally over the current OpenFreeMap basemap;
- improve contrast between roofs/faces/world without making buildings visually dominant;
- preserve useful 3D depth;
- keep normal building opacity high enough to read solidly;
- preserve the existing ghost/transparency behavior during height placement and restore behavior afterwards;
- do not add textures, custom meshes, architectural detail, shadows requiring a new renderer, or provider changes.

### Atom spatial grammar

Polish the existing **ground anchor → stem → beacon** treatment:

- beacon head should read more crisply against both pale basemap and gray buildings;
- selected/draft beacon may have a slightly stronger ring/halo and cleaner edge;
- stems should remain thin but clearly legible through/against buildings;
- ground anchor must be visible enough to prove the Earth relationship, but visually subordinate to the beacon head;
- elevated atoms must still clearly show both top and bottom when building ghosting is active;
- do not increase sizes so much that sparse Pilot atoms feel cartoonishly large;
- do not encode popularity, age, reply count, or any non-spatial semantic in size/height.

### Center sight / aiming

Refine the existing center sight only enough to make its purpose clear before `+`:

- crisp and visible over varied backgrounds;
- compact, not weapon-like / tactical;
- should read as a placement target;
- it must remain at the exact MapLibre visual center used for x/y capture;
- do not add verbose developer/GIS coordinates around it by default.

### Height lever

Keep the accepted lever interaction and mapping exactly. Small visual refinements are allowed:

- cleaner track/handle/readout hierarchy;
- ordinary 0–30 m range remains visually easy to manipulate;
- labels remain readable over the map;
- do not alter the height mapping, range, stored value, or `Done → Write` sequence unless a tiny bug fix is required to preserve existing behavior.

## Required change D — reduce visual clutter

Where safe, remove or soften shell chrome that competes with the world.

Examples of acceptable refinement:

- make the top `Punkto · N visible` status chip slightly calmer/smaller if it currently dominates;
- reduce oversized opaque backgrounds around navigation;
- use consistent blur/translucency sparingly;
- tighten spacing and corner radii so the interface feels intentional rather than assembled from panels.

Do not hide useful status information or create an invisible/minimalist UI that becomes hard to operate.

## Visual character

Target:

**warm · spatial · calm · public · curious · useful · slightly alive**

Avoid:

- cyberpunk neon excess;
- gaming HUD / military reticle look;
- generic admin dashboard styling;
- giant glass panels;
- deep black voids;
- excessive gradients/glow;
- skeuomorphic 3D controls;
- decorative animation unrelated to state.

The map and real place remain the canvas. Punkto UI should feel like a small, confident instrument over it.

## Responsive behavior

Test at minimum:

- desktop wide landscape similar to the recent human screenshots;
- laptop width around 1280–1600 px;
- mobile portrait around 390×844;
- narrow mobile around 360 px.

Requirements:

- hero `+` remains bottom-left and reachable;
- support controls remain nearby and do not cover significant map area;
- safe-area insets respected;
- board sidecar / mobile board sheet still works;
- Settings opens correctly;
- create height stage still suppresses unrelated shell controls cleanly;
- write composer still fits and restores shell/map context correctly after close/publish.

## Accessibility / interaction quality

- keep keyboard focus visible;
- maintain semantic buttons and aria labels;
- hero `+` should have an accessible label equivalent to `Leave a Punkti` / `Create Punkti` while visible text may remain only `+`;
- support controls retain readable labels or accessible names;
- no hover-only affordances;
- respect reduced motion;
- avoid tiny hit targets.

## Architecture

Preferred ownership:

- `pwa/ui-shell.js`: only shell behavior/state if needed;
- `pwa/index.html`: shell markup/CSS and focused visual polish;
- `pwa/ui-map.js`: only map/building/beacon/sight visual refinements;
- `pwa/ui-create.js`: only height-lever visual refinement if necessary;
- `pwa/app.js`: version marker only unless narrow coordination is genuinely required.

Do not move product logic into CSS/markup hacks. Do not duplicate shell event behavior unnecessarily.

## Version marker

Update both console marker and `window.PUNKTO_APP_VERSION` to exactly:

`pilot1-slice45c-hero-shell-polish-2026-08-28-1`

## Expected scope

Prefer only:

- `pwa/index.html`
- `pwa/ui-shell.js` if shell behavior/markup synchronization requires it
- `pwa/ui-map.js`
- `pwa/ui-create.js` only for narrow lever polish
- `pwa/app.js` for version marker
- `docs/agent/CODEX_CURRENT_TASK.md`

Touch `pwa/ARCHITECTURE.md` only if module ownership meaningfully changes.

Do **not** edit relay/protocol/storage/signing/sync/deployment/node configuration.

## Acceptance criteria

All must be true before committing:

1. On normal Map view, the `+` button is immediately obvious as the primary action.
2. `+` is positioned bottom-left on desktop and mobile, with safe-area handling.
3. Text / Map / Settings remain near the same control cluster but are visibly smaller/quieter.
4. The supporting controls remain usable with ~44 px minimum hit targets and clear active/focus states.
5. Pressing `+` still opens the accepted B2 sight-lock + height-lever flow with no behavioral regression.
6. The existing center sight remains the x/y aiming truth and is visually clearer but not tactical/heavy.
7. Buildings look one notch more refined/lighter while preserving 3D readability.
8. Height-placement building ghosting still makes ground anchor + stem + elevated beacon readable through buildings and restores afterwards.
9. Beacon head, stem, and ground anchor are clearer against both basemap and building backgrounds without becoming oversized/noisy.
10. Height lever behavior/range/mapping and `Done → Write` sequence are unchanged.
11. Board sidecar/mobile sheet, Text view, Settings, deep links, create write/publish flow, relay/sync/storage/signing remain unchanged.
12. No semantic is encoded into Z except physical height.
13. No new heavy graphics engine/assets/provider introduced.
14. Version marker is exactly `pilot1-slice45c-hero-shell-polish-2026-08-28-1`.

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

## Focused browser checks

Where practical without publishing another public atom:

- normal desktop Map: verify hero `+` is unmistakable bottom-left and support controls are quieter;
- mobile portrait: same, including safe-area and thumb reach;
- Text ↔ Map works from new control cluster;
- Settings opens/closes correctly;
- press `+`: verify B2 height stage opens, not write composer;
- lever still works Ground → ~3 m → ~10 m → Ground;
- building ghosting still works;
- Done opens write composer only afterwards;
- cancel returns to normal shell with correct building opacity and no stuck hidden controls;
- board open/close does not collide with bottom-left cluster;
- inspect atoms against pale ground and gray building backgrounds;
- no uncaught MapLibre/deck.gl/module errors.

Human visual acceptance on test1 remains required before proceeding to Slice 5.

## Commit / push contract

Before committing, change the first status line to exactly:

`Status: **HOLD — Slice 4.5C implemented, awaiting CI/review**`

Make one focused implementation commit with exactly:

`feat(pilot1): make create the hero action`

Then:

1. commit only this task's implementation + task status change;
2. push to `origin/pilot-1`;
3. report exact SHA, changed files, automated checks, focused browser checks, and remaining visual uncertainty;
4. stop.

Do **not** deploy. Do **not** start Slice 5. ChatGPT will review the exact pushed SHA and Pilot CI first.
