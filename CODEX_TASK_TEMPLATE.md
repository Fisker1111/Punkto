# Codex Task Template

Use this template when implementing a PR from a ChatGPT spec or a human task description.
Copy, fill in, and include the completed version in your PR description.

---

## Task receipt

```
Task title:      <short title>
Spec source:     ChatGPT / Human / AZ
Spec date:       YYYY-MM-DD
Target version:  v<N>
Branch:          main (direct) or feature/<name>
```

---

## Pre-flight — inspect before editing

- [ ] Read `AGENTS.md` — confirm task is in scope
- [ ] Read `PUNKTO_UI_PRINCIPLES.md` if task touches UI
- [ ] Read `DEPLOYMENT_CHECKLIST.md` if task touches infra
- [ ] Inspect each file you will edit before touching it
- [ ] Confirm the hard marker version in `pwa/app.js`
- [ ] List any IDs in `index.html` that your change depends on

---

## Scope confirmation

Answer before coding:

| Question | Answer |
|---|---|
| Does this task change protocol/sync/storage? | Yes / No |
| Does this task change backend/relay/Docker? | Yes / No |
| Does this task change bottom nav layout? | Yes / No |
| Does this task change MapLibre/deck.gl engine? | Yes / No |
| Does this task add social features? | Yes / No |

If any **Yes** is not explicitly requested by the spec, stop and confirm.

---

## Files changed

List every file you will touch:

```
pwa/app.js              — <what changes>
pwa/ui-shell.js         — <what changes>
pwa/ui-text.js          — <what changes>
pwa/ui-map.js           — <what changes>
pwa/index.html          — <what changes>
pwa/style.css           — <what changes>
<other>                 — <what changes>
```

Files NOT touched (confirm unchanged):

```
relay/relay.py          — unchanged
deploy/                 — unchanged
.github/                — unchanged
core/                   — unchanged
```

---

## Implementation notes

Brief description of what you implemented and key decisions made:

```
<notes>
```

---

## Hard marker bump

Every commit touching `pwa/` must bump the hard marker in `pwa/app.js`:

```js
// Before
const HARD_MARKER = 'v53-hard-marker-2026-05-16-2';

// After
const HARD_MARKER = 'v54-hard-marker-2026-05-17-1';
```

Format: `v<N>-hard-marker-<YYYY-MM-DD>-<seq>`

---

## Syntax checks

Run before committing. All must exit 0:

```bash
node --check pwa/app.js
node --check pwa/ui-shell.js
node --check pwa/ui-text.js
node --check pwa/ui-map.js
node --check pwa/key-management.js
node --check pwa/sw.js
```

Results:

```
app.js:        exit 0 ✅ / FAIL ❌
ui-shell.js:   exit 0 ✅ / FAIL ❌
ui-text.js:    exit 0 ✅ / FAIL ❌
ui-map.js:     exit 0 ✅ / FAIL ❌
key-management.js: exit 0 ✅ / FAIL ❌
sw.js:         exit 0 ✅ / FAIL ❌
```

---

## Acceptance criteria — from spec

Copy acceptance criteria from the ChatGPT spec and check each:

- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] <criterion 3>

---

## Manual browser check

Run after deploy (AZ role — but Codex should at minimum verify syntax and logic):

- [ ] Hard marker in console matches commit
- [ ] Text page opens by default
- [ ] Nav: `Text | Map | + | Settings`
- [ ] Settings closed on first load
- [ ] Map tap → tiles load
- [ ] Text tap → feed or empty state
- [ ] + tap → create modal opens
- [ ] Settings tap → panel opens and highlights button
- [ ] Show on map → switches to Map, focuses atom
- [ ] `/p/<id>` deep link → opens Map, focuses atom

---

## Commit message format

```
<type>(<scope>): <short description> v<N>

<body: what changed and why>

Files:
- pwa/app.js: <change>
- pwa/ui-shell.js: <change>

Acceptance:
- <criterion>: ✅
- <criterion>: ✅

Hard marker: v<N>-hard-marker-<YYYY-MM-DD>-<seq>
```

Commit types:
- `feat`: new feature
- `fix`: bug fix
- `refactor`: restructure without behaviour change
- `docs`: documentation only
- `chore`: build/infra/config only

---

## Handoff to AZ

After committing and pushing:

1. Confirm GitHub Actions build succeeds (Actions tab)
2. Tag the commit if it is a version release
3. Tell AZ: **"v<N> is ready to deploy"**
4. AZ will pull, force-recreate, verify hard marker, and report back

> Do NOT deploy to production yourself unless the team has agreed to self-deploy.
