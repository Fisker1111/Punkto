# CODEX TASK 24B — `/ai` E3 follow-up: helper flag parsing + explicit participation

**Status:** ACTIVE
**Base branch:** `origin/main` (merge commit `e4a37b1`, which contains PR #119 / CEO-OS #24).
**Work branch:** `fix/ai-e3-followup` (already created and checked out in this directory).

Do **not** commit and do **not** push. Hermes commits and pushes from its own shell.

Read `AGENTS.md` first for the project rules and the frozen-module rules.
Do **not** modify the frozen modules `pwa/punkti/carrier.js`, `pwa/punkti/spatial.js`,
`pwa/punkti/reader.js`, `pwa/punkti/submit.js`, or any frozen vector file. If you believe one
of them is wrong, **stop and report**.

Note: `pwa/ai.html` was rewritten in PR #119 and reviewed (E0 PASS). Its current structure is:

```
1. BOOT / 2. GET THE HELPER / 3. READ / 4. SPACE / 5. WRITE / 6. REPLY /
7. IDENTITY AND TRUST / Optional protocol details
```

with an intro paragraph
`Punkto is public shared spatial memory made of small signed atoms. You can read, write and reply. No account, API key or registration is required.`

Keep that structure and the existing E0-approved wording. Only make the two changes below.

---

## 0. Why this follow-up exists

The first E3 heterogeneous cold-start round against the test deployment
`https://test2.punkto.xyz/ai` produced two concrete, reproducible defects that a cold-start
agent hit with no private explanation.

**Defect A (helper):** the CLI rejects the `--flag=value` form and mis-parses negative
numbers, so a documented coordinate write can silently fail or be pushed to the wrong place.

**Defect B (page):** the page documents WRITE, but most cold-start agents finished after
reading and explicitly reported that they had **not** published anything — the page never
says that publishing an atom of your own is how you take part in the network.

---

## 1. Defect A — the helper must accept `--flag=value` and negative values

`pwa/punkti/cli.mjs` currently parses options with a fixed pair loop:

```js
const options = {};
for (let i = 0; i < flags.length; i += 2) {
  const key = flags[i].slice(2);
  if (!flags[i].startsWith('--') || !allowed.has(key) || flags[i + 1] === undefined || Object.hasOwn(options, key)) throw new Error('invalid or repeated option');
  options[key] = flags[i + 1];
}
```

Observed in E3 (model `gpt-5.6-sol`, run `r02`):

* `node cli.mjs write --nodes <url> --text '...' --lat 51.4779 --lon=-0.0015 --height 45`
  → `{"error":"invalid or repeated option"}`.
  The `=` form is not supported at all, and a negative value that follows a separate
  `--lon` token is read as another option.
* The agent worked around it by writing to a **different** location (`--lon 0.0005`), i.e. the
  documented coordinate syntax silently pushed the agent off its chosen place.

Required behaviour after the fix:

* Both `--flag value` and `--flag=value` are accepted for every documented option
  (`--nodes`, `--publication`, `--submit`, `--xy`, `--z-min`, `--z-max`, `--limit`,
  `--text`, `--lat`, `--lon`, `--height`, `--h`, `--ref`).
* A value that starts with `-` is accepted as a value (it is not an option) — in particular
  negative `--lat` / `--lon` / `--height` must work.
* Unknown option names, missing values and repeated options still fail with a clear JSON
  error (`{"error":"..."}`) and a non-zero exit code.
* A repeated option is an **error** (deterministic, documented in a code comment, and
  covered by a test). Do not implement "last one wins".
* `--` (end of options) is not required; do not add it.
* Do not change any documented option name, and do not change any frozen wire format.

Implementation notes:

* Keep the helper a single file with no new dependency.
* Parse the argument vector first (split `--flag=value` into key/value), then validate.
* Split on the **first** `=` only, so a value may contain further `=` characters.
* A bare `--flag` followed by a token that starts with `--` is a missing value.
* A bare `--flag` followed by a token that starts with a single `-` (e.g. `-0.0015`) is
  that flag's value.

**Do not regress the merged behaviour** in `cli.mjs`: when `--lat`/`--lon` are given,
`--height` is required as well and the error message must keep saying
`--lat, --lon and --height are required together; never invent ellipsoidal height`.
`--h` and coordinates are still mutually exclusive.

## 2. Defect B — the page must say that publishing is how you take part

Two small, explicit additions to `pwa/ai.html`. Nothing else changes.

1. In the **intro paragraph** (the one that starts
   `Punkto is public shared spatial memory made of small signed atoms.`), state in one
   sentence that reading is passive and that **publishing an atom of your own is the way to
   take part** in the same network, with the same protocol and no separate AI identity.
   Suggested wording (may be lightly reworded, but must keep the meaning):
   `Reading is passive; publishing an atom of your own is how you take part in the same network, with the same protocol and no separate AI identity.`

2. In the **5. WRITE** section, state that a write is permanent and public on that node,
   that it is the normal way to participate, and that an agent may write more than one atom
   and reply to any MID it read.
   Suggested wording (may be lightly reworded):
   `A write is permanent and public on that node. It is the normal way to participate; you may write more than one atom and reply to any MID you read.`

Hard constraints on the page:

* Keep the page minimal: it must stay a boot card, roughly 300–500 words plus commands.
  Do **not** grow it into a specification.
* Keep the existing concrete commands and the existing "Never guess z" warning verbatim.
* Do **not** add: ETUR branding, a separate AI atom type, a mandatory `app:"ai"` field,
  rooms/channels, a place registry, a feed, likes, reputation, follower graphs, economics,
  an onboarding wizard, accounts, API keys, `wander`, or any server-side endpoint.
* Do **not** add JavaScript. The page stays one static HTML file.
* Do **not** add any protocol-doc detail (no canonical-body description, no domain
  separation strings, no filesystem layout). `pwa/test-ai-hostile.mjs` actively fails on
  protocol-doc leakage; keep it that way.
* Do **not** change the `https://punkto.xyz` literals in the page. The production page must
  stay literal against production. (A staging-specific copy is produced at deploy time by
  the operator, not by this change.)

## 3. Tests

* Add a sibling harness `pwa/test-ai-cli.mjs` (the existing `pwa/test-ai-hostile.mjs` is
  the E2 harness; a sibling file is preferred) that asserts:
  * `--flag=value` parsing works for `--nodes`, `--text`, `--lat`, `--lon`, `--height`,
    `--h`, `--xy`, `--z-min`, `--z-max`, `--limit`, `--publication`, `--submit`, `--ref`;
  * `--flag value` still works;
  * a negative `--lon` and a negative `--lat` are accepted and produce the expected `h`
    (compare against `pwa/punkti/spatial.js` `encode_h` in the same process — do not
    hardcode a new frozen vector);
  * a value containing `=` survives (only the first `=` splits);
  * an unknown option still fails with `{"error": ...}` and exit code != 0;
  * a missing value still fails with `{"error": ...}` and exit code != 0;
  * a repeated option still fails with `{"error": ...}` and exit code != 0;
  * `--lat`/`--lon` without `--height` still fails with the "never invent ellipsoidal
    height" error.
* Extend `pwa/test-ai-hostile.mjs` so its required-page-text list also asserts the two
  new sentences from §2 exist in `pwa/ai.html`.
* Add `node pwa/test-ai-cli.mjs` to `.github/workflows/punkto-image.yml`, next to the two
  existing harnesses, in the same style.

## 4. Required checks (all must pass; report each result)

```bash
node pwa/test-ai-coldstart.mjs
node pwa/test-ai-hostile.mjs
node pwa/test-ai-cli.mjs
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-slice5.mjs
for module in pwa/*.js pwa/*/*.js; do node --check "$module"; done
node --input-type=module --check < pwa/app.js
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m punkti_node --check-config --config node-config.example.yml
PUNKTO_WEB_ROOT="$PWD/pwa" python3 -m punkti_node --check-config --config punkto-config.example.yml
```

If a check fails for a reason that is **not** caused by your change, report it and stop —
do not "fix" unrelated code.

## 5. Report

Report: files changed, each check with pass/fail, the exact option-parsing rules you
implemented (including the repeated-flag rule and how a negative value is distinguished from
an option), and the exact wording you added to `pwa/ai.html`. Do not commit or push.
