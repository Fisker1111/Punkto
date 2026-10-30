> Historical pre-correction draft, superseded by the 2026-10-29 spatial-only correction: every v0.6 record requires canonical XY_Z; empty h and publication key `~` are invalid. Signed historical evidence remains frozen in `legacy-unanchored/`.

# CODEX TASK 24 — Punkto `/ai` minimal machine entrance + `nodes.json` bootstrap

**Status:** ACTIVE
**Base branch:** `feat/punkti-0.6-static-first-pwa` (head `61f168c`) — the frozen Punkti v0.6
building blocks from CEO-OS #22 / PR #118. **Do not re-implement any Punkti v0.6 protocol
logic.** Reuse `pwa/punkti/*.js` and `punkti_node/*.py` exactly as they are.
**Work branch:** `feat/punkti-0.6-ai-entrance` (already created from the base branch).

---

## 0. Goal

Give a machine an immediately usable entrance to Punkto:

1. `GET /nodes.json` on a Punkti node — a tiny, machine-readable **bootstrap/discovery**
   list of Punkti nodes.
2. `GET /ai` on a Punkti node — a deliberately sparse page whose *own body* explains
   everything a machine needs to **read, verify, write and reply** to Punkti, with exact
   executable examples.
3. A small unobtrusive `AI` / machine-entry link in the existing human Punkto UI that
   opens `/ai`.

Punkti does not distinguish humans and machines. There is **no** separate AI network, AI
protocol, AI database, AI atom type, ETUR branding, room/channel concept, feed API,
server-side `wander` endpoint, reputation model or mandatory identity on this page.

---

## 1. Decisions already made (do not re-litigate)

These are fixed by the task owner. Implement them exactly.

### 1.1 `nodes.json` is configuration-driven and served by the node

The node serves `GET /nodes.json`. The content is derived from the node configuration,
so an operator can add their own node without touching code, and so a deployment can
publish a different list than production.

New configuration section (`punkti_node/config.py`), strict like every other section:

```yaml
bootstrap:
  nodes:
    - id: punkto-xyz
      base: https://punkto.xyz
      publication: https://punkto.xyz/publication
      submit: https://punkto.xyz/submit
```

Rules:

* `nodes` is a list; each entry is a mapping with exactly the keys `id`, `base`,
  `publication` and (optional) `submit`.
* `id` — non-empty string.
* `base` — absolute `http(s)` URL of the node, no trailing slash.
* `publication` — absolute `http(s)` URL of that node's **static Punkti publication**
  (the directory that serves `root.json`, `manifests/`, `h/`, `records/`).
* `submit` — absolute `http(s)` URL of that node's signed-record submission endpoint.
  **Optional**: omit it when the node does not accept writes (read-only node).
* Unknown keys, wrong types, non-absolute URLs and trailing slashes are configuration
  errors and must be rejected at load time (same style as the rest of `config.py`).
* Default: `bootstrap.nodes` is an empty list.

The served document is **deterministic**: the same configuration MUST produce byte-identical
output on every node (sorted by `id`, fixed member order, no timestamps, no random ids, no
host-specific values). Two nodes that serve the same bootstrap set therefore serve the
same file, which is what the bootstrap list is for.

Served shape (`GET /nodes.json`, `Content-Type: application/json`):

```json
{
  "v": "punkti/bootstrap/1",
  "nodes": [
    {"id": "punkto-xyz", "base": "https://punkto.xyz", "publication": "https://punkto.xyz/publication", "submit": "https://punkto.xyz/submit"}
  ],
  "notice": "Recommended bootstrap list. Not a trust authority and not a completeness claim: one node's publication is one published view, not all of Punkto."
}
```

* `v` is the literal string `punkti/bootstrap/1`.
* `nodes` is sorted by `id` (ascending, byte order).
* An entry without `submit` omits the key entirely (no `null`).
* `notice` is a fixed constant string (exact text above).
* The document MUST state in the notice that the list is recommendation-only and that one
  node is not the whole network.

Implementation notes:

* Serve it from the node's `special_route` (`punkti_node/store.py`) so it is available on
  every node deployment, next to `/submit`, `/health` and `/node/info`.
* The node MUST NOT add itself automatically and MUST NOT invent URLs from its own
  configuration: the operator's list is the list.
* `punkti_node/config.py` must also expose an environment override if that matches the
  file's existing style; otherwise YAML only is acceptable. Document which you chose in
  the report.

### 1.2 `/ai` is served by the node from a static file in the PWA bundle

* The page lives at `pwa/ai.html` in the PWA bundle (so it ships in the Docker image at
  `/srv/pwa/ai.html` next to the rest of the PWA).
* The node serves it at the exact path `/ai` (no trailing slash, no extension).
* Implement it as a path→file alias in the static web layer
  (`punkti_node/web.py`, `StaticWeb`), configured from `web.pages`:

  ```yaml
  web:
    pages:
      /ai: ai.html
  ```

  Defaults: `web.pages` = `{"/ai": "ai.html"}`.
  `pages` maps an exact request path to a file relative to the web root. Only exact
  matches (no prefix matching, no directory traversal). The alias must be served with
  `Content-Type: text/html; charset=utf-8`, `X-Content-Type-Options: nosniff` and the
  same `Cache-Control: no-cache, no-store, must-revalidate` policy as other `.html`.
* `/ai.html` may also be reachable directly through the ordinary static path; that is
  acceptable. `/ai` MUST work.

### 1.3 The human UI gets one small machine-entry link

* Add exactly one small, unobtrusive machine-entry link to the existing PWA UI. It opens
  `/ai` in a new tab (`target="_blank" rel="noopener noreferrer"`).
* Put it in the Settings panel, in the existing `App` section, next to the version row:
  a small link labelled `AI` with a short hint that it is the machine entrance. Give it
  `id="ai-entry-link"` and `data-testid="ai-entry-link"`.
* Additionally add one small `AI` text link in the map top bar (next to the sync
  indicator) with the same `id`/`data-testid` convention — use a distinct id
  `ai-entry-link-topbar` / `data-testid="ai-entry-link-topbar"` so tests can target
  both. The top bar container has `pointer-events: none`; the link itself must set
  `pointer-events: auto`.
* Do not add a new navigation bubble, dashboard, panel or any AI-specific UI surface.
  Follow `PUNKTO_UI_PRINCIPLES.md` (dark/glass, restrained typography).

### 1.4 One command-line helper that calls the frozen implementation

Agents are not browsers: they need HTTP plus a way to hash/sign/submit. Add the smallest
helper that calls the **existing frozen modules** — do not fork the protocol logic.

* New file `pwa/punkti/cli.mjs` (ES module, Node 20+). It imports the sibling frozen
  modules (`./carrier.js`, `./spatial.js`, `./reader.js`, `./submit.js`) and nothing else
  from the protocol.
* It must supply TweetNaCl the same way the existing tests do
  (`globalThis.nacl = createRequire(import.meta.url)('./nacl.min.js')`), but it must find
  `nacl.min.js` next to itself **or** one directory up (the repo layout has it at
  `pwa/nacl.min.js`, the downloaded-flat layout at `./nacl.min.js`). Try both.
* Subcommands (all output a single JSON object on stdout, errors as JSON with an `error`
  key and a non-zero exit code):

  * `read --nodes <url> [--publication <url>] [--xy <prefix>] [--z-min <z>] [--z-max <z>] [--limit <n>]`
    — fetch the bootstrap list (default `<nodes-url>`), pick the first node, read its
    static publication with the frozen reader, verify each record locally, and print
    `{"publication": {...}, "records": [{"mid","h","state","text"}...]}`.
  * `write --nodes <url> --text <text> [--lat <n> --lon <n> [--height <n>]] [--h <xy_z>]`
    — create an **ephemeral** Ed25519 key, build a frozen v0.6 atom
    (`v: "punkti/0.6"`, `t: <now ms>`, `h: <xy_z>`, `x: JSON.stringify({text})`,
    `alg: "ed25519"`, `refs: []`, `ext: ""`), sign it with the frozen carrier, submit it
    to the node's `submit` endpoint with the frozen submit client, and print
    `{"mid": "...", "sha256": "...", "duplicate": false}`.
    * If neither `--lat/--lon` nor `--h` is given, the atom is **unanchored**
      (`h: ""`).
    * `--lat/--lon` without `--height` means height `0`.
    * `h` is built with the frozen `spatial.js` `encode_h(lat, lon, height)`.
  * `reply --nodes <url> --ref <MID> --text <text> [--lat/--lon/--height/--h as above]`
    — same as `write`, but the atom carries `refs: [{"target": "<MID>", "rel": "reply"}]`.
    Print `{"mid": "...", "ref": "<MID>"}`.

* `--nodes <url>` may point at any `nodes.json` URL. `--publication`/`--submit` override
  the selected node's endpoints.
* The helper must work when the files are downloaded flat into one directory (that is how
  an agent will use it) and when it is run from the repo.
* No new dependency: standard library plus the vendored `nacl.min.js` only.

### 1.5 `/ai` page content — mandatory sections

The body of `/ai` must itself contain the complete essential instructions. It must be
readable by a text-only agent (`curl`) and by a browser. Plain HTML, one file, inline
minimal styling, no JavaScript, no external requests, no tracking, no framework.

Required sections, in this order, each with an explicit heading a machine can grep:

1. **What Punkto is** — signed atoms anchored to real-world coordinates; a spatial
   network; static publication + signed-record submission; no account, no API key, no
   OAuth, no onboarding, no proprietary SDK.
2. **BOOT** — `GET /nodes.json` on this same origin, the exact response shape, and the
   statement that the list is a *recommendation*, not a trust authority, and that one
   node is one published view (broader discovery may read several bootstrap nodes and
   deduplicate by MID).
3. **READ** — how to read the static publication: `root.json` → `manifests/<sha>.json` →
   `h/<prefix path>/<sha>.json` → `records/<sha2>/<sha>`, the reader module path, and one
   exact read example.
4. **VERIFY** — records are verified **locally** by the client: the SHA-256 content
   address of every published object, the Ed25519 signature over
   `ASCII("PUNKTI-L3-SIGN") || 0x00 || canonical body`, and
   `mid = SHA-256(ASCII("PUNKTI-L3-MID") || 0x00 || canonical body)`; invalid records
   are quarantined, not served as valid.
5. **SPACE** — the spatial address format `h=<xy>_<z>`; `xy` is a geohash-style prefix of
   the coordinates, `z` is an ellipsoidal height in metres; an agent can reason
   symbolically about space with **no map and no graphical UI**; an agent may inspect a
   known location, inspect nearby/populated regions, follow references, choose another
   location, and place an atom somewhere meaningful. There is **no central place
   registry**: places emerge from use.
6. **WRITE** — create an ephemeral key, build/sign a frozen v0.6 atom, submit it with
   `POST <submit>` and the exact JSON body shape; then read it back **only through the
   static publication**.
7. **REPLY** — one exact example of replying to an existing MID with a frozen reference
   (`refs: [{"target": "<MID>", "rel": "reply"}]`).
8. **IDENTITY** — an ephemeral key is legitimate and sufficient; keep the key only if you
   want continuity of authorship; no account, no registration, no recovery requirement.
9. **Limits** — one node failing does not mean Punkto is unavailable; try another
   bootstrap node; a node that does not accept writes simply has no `submit` entry.

The page MUST also contain:

* the **exact** commands for the helper (§1.4) — including the exact `curl`/`node`
  invocations an agent can copy verbatim, using placeholders that are obvious (`<ORIGIN>`,
  `<TEXT>`), and one fully worked concrete example with a real value;
* the exact spatial example `h=u3butz7k9q7v_0` (lat `55.675398`, lon `12.561895`,
  height `0`) so an agent can see the format without inventing it;
* the exact frozen payload conventions: envelope members
  `v, t, h, x, alg, pk, refs, ext, sig`; `v` is `punkti/0.6`; `t` is Unix milliseconds;
  `x` is a JSON string such as `{"text":"..."}`; `alg` is `ed25519`; `pk`/`sig`/`ext` are
  base64; `refs` entries are exactly `{target, rel}`; a MID is
  `punkti/0.6:<64 lowercase hex>`; a record is `body || signature`, both length-prefixed;
* the **exact** verification conventions, which include domain-separation prefixes and
  MUST be stated exactly as the frozen implementation has them
  (`pwa/punkti/carrier.js`, `punkti_node/carrier.py`, and
  `docs/proposals/PUNKTI_0_6_LAYER3_RESET.md` §"Proposed signing input"):
  * the canonical body `C` is the length-prefixed encoding of the envelope members;
  * the signing input is `ASCII("PUNKTI-L3-SIGN") || 0x00 || C` — i.e. the signature
    covers the domain prefix **plus** the body, not the bare body;
  * `mid = lowercase_hex(SHA256(ASCII("PUNKTI-L3-MID") || 0x00 || C))` — the MID digest
    also covers a domain prefix, not the bare body;
  * the Ed25519 public key is `pk`; the signature is `sig` over that signing input;
* an explicit statement that this page describes **one** protocol (Punkti v0.6) and that
  the page is served by an ordinary node, with no machine-only protocol.

Do **not** expose implementation history, internal terminology, ETUR, rooms, channels,
place names, likes, reputation, follower graphs, economics, or any "AI" concept beyond
the fact that the entrance exists for machines.

### 1.6 The human UI link text must not promise AI-specific behaviour

The link is a *machine entrance*. Label it `AI` plus a short neutral hint such as
"machine entrance". Never label it "ETUR".

---

## 2. What to implement (files)

| File | Change |
|---|---|
| `punkti_node/config.py` | `bootstrap.nodes` section, strict validation, defaults, env override if it fits the file's style. |
| `punkti_node/config.py` | `web.pages` section (path→file map), default `{"/ai": "ai.html"}`, strict validation (paths start with `/`, values are safe relative paths, no `..`). |
| `punkti_node/store.py` | `special_route`: serve `GET /nodes.json` deterministically from `config['bootstrap']['nodes']`. |
| `punkti_node/web.py` | `StaticWeb`: exact-path page aliases from `web.pages`. |
| `punkti_node/runtime.py` | wire `web.pages` into `StaticWeb`. |
| `punkti_node/test_node.py`, `punkti_node/test_web.py`, `punkti_node/test_publication.py` | cover the new behaviour (see §3). |
| `punkti_node/config.py` example files (`node-config.example.yml`, `node-config.punkto-xyz.example.yml`, `punkto-config.example.yml`) | show the new sections. |
| `pwa/ai.html` | the `/ai` page (§1.5). |
| `pwa/index.html` | the two machine-entry links (§1.3). |
| `pwa/punkti/cli.mjs` | the helper (§1.4). |
| `pwa/test-ai-coldstart.mjs` | **E1** deterministic local harness (§3). |
| `pwa/test-ai-hostile.mjs` | **E2** hostile/minimality harness (§3). |
| `docs/AI_ENTRANCE.md` | short operator/founder-facing doc: what `/ai` and `/nodes.json` are, how to configure `bootstrap.nodes`, how to run the E1/E2 harnesses. |
| `.github/workflows/punkto-image.yml` | run the two new Node harnesses in CI (same style as the existing Node test invocations). |

Do not modify `pwa/punkti/carrier.js`, `pwa/punkti/spatial.js`, `pwa/punkti/reader.js`,
`pwa/punkti/submit.js` or any frozen vector file. If you believe one of them is wrong,
**stop and report** instead of changing it.

---

## 3. Tests to write (and they must actually run)

### E1 — deterministic local cold-start harness (`pwa/test-ai-coldstart.mjs`)

A fresh ephemeral actor must, against a **locally spawned node** (spawn
`python3 -m punkti_node` with a temporary config and temporary data dir, exactly like
`pwa/test-punkti-static-e2e.mjs` does):

1. fetch `nodes.json`;
2. select a node from it;
3. read the static publication;
4. locally verify the records (the reader validates; assert on the reported states);
5. understand at least one XY_Z address with no graphical map (assert
   `parse_h`/`encode_h` round-trip for `u3butz7k9q7v_0` and assert the CLI can address a
   location by lat/lon);
6. create an ephemeral key;
7. create a small atom;
8. submit it (`POST /submit`);
9. read it back **only through the static publication** (re-read the publication and
   find the submitted MID — not from the submit response);
10. reply to an existing MID (the atom it just wrote, or another record in the
    publication);
11. restart/disappear while the memory remains: stop the node process, start a new one
    against the same data directory, and assert the record is still present in the static
    publication.

Assert every step. No step may be a no-op.

### E2 — hostile / minimality harness (`pwa/test-ai-hostile.mjs`)

Cover, with assertions:

1. malformed bootstrap entry (missing `base`, wrong type, non-absolute URL, trailing
   slash, unknown key) → rejected at config load;
2. unreachable node → the helper fails cleanly with a JSON error, not a crash or a hang;
3. corrupt static object (flip a byte in a published object) → the reader refuses it
   (`corrupt object`), and the valid records are not silently accepted;
4. invalid signature → the record is not reported as `VALID`;
5. stale publication (serve an older `root.json` seq after a newer one was seen) → the
   reader reports a stale/equivocal root instead of silently downgrading;
6. duplicate atom (submit the same atom twice) → the second submit is reported as a
   duplicate, and the publication does not contain two copies;
7. invalid MID / invalid ref (a reply whose `target` is not a valid MID) → rejected;
8. a node that does not accept writes (bootstrap entry without `submit`) → the helper
   says so clearly and does not attempt a write;
9. the `/ai` page and `nodes.json` must not imply that one failing node means Punkto is
   unavailable (assert the page contains the required statements and that `nodes.json`
   carries the `notice`).

### E0 — cold-start ambiguity review

E0 is a **human/model review of the finished `/ai` page**, not a unit test. It is run
by the task owner against the deployed test endpoint. Your job is to make the page
reviewable: it must be self-contained, and `docs/AI_ENTRANCE.md` must contain the exact
URL a reviewer should visit.

---

## 4. Definition of done

* `python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication` → all pass.
* `node pwa/test-punkti-vectors.mjs`, `node pwa/test-punkti-publication.mjs`,
  `node pwa/test-spatial-xy-z.mjs`, `node pwa/test-slice5.mjs` → still pass (frozen
  behaviour unchanged).
* `node pwa/test-ai-coldstart.mjs` → passes, exercising all eleven E1 steps.
* `node pwa/test-ai-hostile.mjs` → passes, exercising all nine E2 cases.
* `node --check pwa/ai.html` is not applicable; instead ensure the page is valid HTML by
  inspection and that it contains every required section heading and every required
  literal string listed in §1.5 (assert these in `pwa/test-ai-hostile.mjs` case 9 or a
  sibling check so CI guards the page).
* `node --check` on every changed/added `.js`/`.mjs` file, and
  `node --input-type=module --check < pwa/app.js` for `pwa/app.js` if you touch it.
* `python3 -m punkti_node --check-config --config node-config.example.yml` and
  `PUNKTO_WEB_ROOT="$PWD/pwa" python3 -m punkti_node --check-config --config punkto-config.example.yml` → exit 0.
* `for module in pwa/*.js pwa/*/*.js; do node --check "$module"; done` → exit 0.

## 5. Required checks you must run before reporting

```bash
python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-slice5.mjs
node pwa/test-ai-coldstart.mjs
node pwa/test-ai-hostile.mjs
for module in pwa/*.js pwa/*/*.js; do node --check "$module"; done
node --input-type=module --check < pwa/app.js
python3 -m punkti_node --check-config --config node-config.example.yml
PUNKTO_WEB_ROOT="$PWD/pwa" python3 -m punkti_node --check-config --config punkto-config.example.yml
```

If any pre-existing check fails for a reason unrelated to your change, report it as a
pre-existing failure and prove it (e.g. `git stash` and re-run) — do not "fix" unrelated
code.

## 6. Commit and report

* Commit locally on `feat/punkti-0.6-ai-entrance` with a focused message. Do **not**
  push and do **not** open a PR (the task owner pushes).
* Commit message subject: `feat(ai): add /ai machine entrance, nodes.json bootstrap and cold-start harnesses`.
* Report exactly: files changed, the checks you ran with their pass/fail result, the
  final `nodes.json` example output, the `/ai` section list, and anything you could not
  implement (with the reason). If a requirement in this brief is contradictory with the
  frozen implementation, **stop and report** — do not silently change the protocol.
