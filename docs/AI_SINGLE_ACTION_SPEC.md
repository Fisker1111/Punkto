# A1 spec — Punkto `/ai` single-action reply proof (CEO-OS #36)

Normative specification for the branch `feat/ai-single-action-v2`, based on
`origin/main` (`5e164f8`). PR #140 is a **separate, parallel** change that this
branch does not contain or modify; see §0 for why the production path depends
on it.

Status: this document is the contract. If the implementation and this document
disagree, the implementation is wrong. Do not silently weaken any rule here.

## 0. Measured ground truth (do not re-derive, do not contradict)

Measured 2026-11-01 against live `https://punkto.xyz`:

* `GET /nodes.json` → two nodes: `punkto-test2` (base `https://test2.punkto.xyz`,
  publication `https://test2.punkto.xyz/publication`, **no** `submit`) and
  `punkto-xyz` (base `https://punkto.xyz`, publication `https://punkto.xyz/publication`,
  `submit` `https://punkto.xyz/submit`). **Neither node advertises an `index` URL.**
* `GET /publication/root.json` → `{"head":"<64 hex>","seq":12,"v":"punkti/pub/0.6"}`.
* `GET /publication/manifests/<head>.json` → `index` maps a **2-character** GeoHash
  prefix (`"0n","5j","94","dq","e7","u3","u4","ys"`) to a shard sha256; `record_count` 13.
* `GET /publication/h/<one path segment per prefix character>/<shard sha>.json`
  → `{"children":{...},"packs":[],"prefix":"u3","records":[],"v":"punkti/pub/0.6"}`.
  A shard's `children` map is keyed by the **full child prefix**, not by a single
  character: a shard with `"prefix":"u3"` has `children: {"u3b": "<sha>"}`, and a
  shard with `"prefix":"u3b"` has `children: {"u3bu": "<sha>"}` (the frozen reader
  enforces `childPrefix.length === expectedPrefix.length + 1` and
  `childPrefix.startsWith(expectedPrefix)`). Records live in the leaf shard at
  prefix depth 10.
* `GET /publication/records/<sha256[0:2]>/<sha256>` → the immutable record bytes.
* Production publication currently holds 13 records; their texts are CEO-OS #33/#35
  operator/canary evidence. **There is no production "welcome" thread yet** (see §7).
* The `main` reader (`pwa/punkti/reader.js` at `5e164f8`) **cannot parse the live
  production manifest**: `{"error":"invalid object"}`. Cause: integer-like manifest
  index key `"94"` is hoisted by `JSON.stringify` in `canonicalValue()`. PR #140
  (`69a9682`) fixes it. With PR #140's `reader.js`, the same read returns 13 VALID
  records. **PR #140 is a separate, parallel change: this branch is based on
  `origin/main` and neither contains nor modifies the reader fix.** The reader
  fix is a prerequisite for the *production* path only: the helper loads the
  reader module that the node it talks to publishes, so a node still serving the
  unfixed reader will fail its own publication read. The local fixture used for
  this proof serves this branch's own `pwa/` tree, whose fixture manifest has no
  integer-like key, so the suite is green either way.

Consequence: the live `https://punkto.xyz/ai` page still advertises the six-file
`curl` setup and an optional `node.index` that does not exist. This PR replaces
that copy with a truthful quickstart and adds the single-action helper.

## 1. Scope and non-goals

In scope:

1. A new top-of-page quickstart on `pwa/ai.html`: choose **READ / REPLY / NEW POST**,
   with **one** canonical working read path (root → manifest → shard → raw record)
   using the current reference resolver paths, and **no invented index**.
2. A new single-action helper `pwa/punkti/punkto-reply.mjs` that reuses the frozen
   Punkti 0.6 encoding/signing/verification (no independent cryptography), signs
   locally, publishes, and returns a machine-readable receipt.
3. Self-contained tests proving the required properties (§5).
4. An exact UX transcript produced from a **fresh empty working directory** using
   only the `/ai` URL and a text message, against an **isolated local fixture**
   (never production).

Out of scope (must not appear in this PR): any change to the Punkti carrier/spec,
SHA-256/MID derivation, the signature algorithm, replication, existing records,
network security, production `punkto.xyz` / `test2`, DNS or node configuration;
any production publish; any change to `pwa/punkti/{carrier,spatial,reader,submit}.js`
or `pwa/nacl.min.js`; any merge of PR #125 (draft) or other branches.

## 2. The helper: `pwa/punkti/punkto-reply.mjs`

The file lives at `pwa/punkti/punkto-reply.mjs` and is therefore served by the
node at `<origin>/punkti/punkto-reply.mjs`. **One name everywhere:** the
downloaded local file is `punkto-reply.mjs` and it is invoked as
`node punkto-reply.mjs …`. Never mix `punkti-reply.mjs` and `punkto-reply.mjs`.

Node.js 20.19+/22+, ESM, **no npm dependency, no package install, no build step**.
Dependencies: Node built-ins (`node:crypto`, `node:fs`, `node:path`) only, plus the
frozen Punkti client modules loaded from the node's own origin.

### 2.1 Reuse of the frozen protocol code — mandatory

The helper MUST NOT implement Ed25519, SHA-256, MID derivation, canonical body
encoding, record framing or spatial parsing itself. It MUST load the frozen modules
`pwa/punkti/{spatial,carrier,reader,submit}.js` and `pwa/nacl.min.js` **served by the
same origin** and use them:

* `carrier.js` → `canonical`, `encodeRecord`, `decodeRecord`, `validate`,
  `computeMid`, `sha256Hex`, `signingInput`, `VERSION`, `State`.
* `spatial.js` → `parse_h`, `encode_h`, `xy_key`.
* `reader.js` → `createReader` (and its `hexShardedResolver` paths) for publication
  reads and signature verification of parent records.
* `submit.js` → `createSubmitClient` for the `/submit` POST.
* `nacl.min.js` → the Ed25519 primitive used by `carrier.js`.

Loading mechanism (already proven feasible): fetch each module over plain HTTP GET
from `<origin>/punkti/<name>`, rewrite its relative import specifiers (`'./spatial.js'`,
`'./carrier.js'`) to `data:text/javascript;base64,…` URLs of the already-rewritten
dependency, and `import()` the result. The modules must be loaded in dependency
order: `spatial.js` → `carrier.js` → `reader.js` → `submit.js`. `nacl.min.js` is not
an ES module: wrap it as
`globalThis.self = globalThis;\n<nacl source>\nexport default globalThis.nacl;\n`
and assign `globalThis.nacl` before any carrier call.

Do **not** use `--experimental-network-imports` and do **not** `eval` module source.

### 2.2 Origin and node selection

* `--origin <url>` (default `https://punkto.xyz`, also overridable by env
  `PUNKTO_ORIGIN`) — the origin of the `/ai` page the agent actually fetched. The
  helper resolves every relative path against this origin; it never silently
  switches hosts.
* Bootstrap: `GET <origin>/nodes.json`, require `v === "punkti/bootstrap/1"` and a
  non-empty `nodes` array.
* Write-node selection: prefer a node whose `base` origin equals `--origin` **and**
  which advertises `submit`; otherwise the first node that advertises `submit`;
  otherwise fail with a clear error. (Live `nodes.json` lists `punkto-test2` first
  and it has no `submit`, so "first node" is wrong for writes.)
* Read node selection: prefer a node whose `base` origin equals `--origin`,
  otherwise the first node; read the publication from that node.
* Only `http:`/`https:` URLs, no credentials in the URL, no redirect following
  (`redirect: 'error'`).

### 2.3 Commands

```
node punkto-reply.mjs read  [--origin URL] [--limit N]
node punkto-reply.mjs reply <MID> "text" [--origin URL] [--key-file PATH]
node punkto-reply.mjs post  "text" (--h <xy>_<z> | --lat <lat> --lon <lon> --height <m>) [--origin URL] [--key-file PATH]
```

* `read` — read the publication with the frozen reader and print, per valid record:
  `mid`, `h`, `text`, `state`. Used to discover a thread and its MID.
* `reply <MID> "text"` — the single-action publish. Steps:
  1. `read` the publication (frozen reader, unbounded scope).
  2. Find the record whose `mid` equals `<MID>`. If absent → clear error.
  3. Require that record's frozen-reader `state` is `VALID` (signature verified).
     If it is not `VALID`, fail: the reply's `h` may only be inherited from a
     **verified** parent. Never use an unverified parent's `h`.
  4. Inherit the parent's **exact** `h` verbatim. The reply MUST NOT accept a
     `--h` override and MUST NOT invent, round, re-encode or "correct" `h`.
  5. Build the reply atom with `refs: [{target: <parent MID>, rel: "reply"}]`,
     `h` = parent's exact `h`, `x` = `JSON.stringify({text})`, `alg: "ed25519"`,
     `t` = current epoch ms, `v` = `punkti/0.6`.
  6. Sign locally with a locally held Ed25519 key (§2.4) via `carrier.encodeRecord`.
  7. `POST` to the write node's `submit` via the frozen `submit.js` client.
  8. Re-read the publication (fresh root) and look for the new `mid`.
  9. Print the receipt (§2.5).
* `post "text"` — a **new** conversation at an explicitly chosen address:
  * `--h <xy>_<z>`: must satisfy the frozen `parse_h` (lowercase GeoHash 4–12
    chars, canonical WGS84 ellipsoidal Z). Reject `h=""`, reject a missing `_z`,
    reject `z` that is not canonical.
  * `--lat/--lon/--height`: all three required together; `--height` is a chosen
    ellipsoidal height in metres, never a lookup of ground elevation. Use the frozen
    `encode_h`. Never guess Z; never default Z to 0; never imply an implicit `h`.
  * `--h` and coordinates together → error.
  * The chosen address is a **destination**, not evidence of physical presence.
* Unknown command, missing arguments, unknown flag → clear error, exit 1.
* A `--limit` applies to the `read` output only.

### 2.4 Key handling — local custody, disclosed limits

* Default: a **fresh ephemeral** Ed25519 key generated in memory for this
  invocation. It is never written to disk and never uploaded.
* `--key-file PATH`: load or create a 32-byte lowercase hex seed at `PATH`
  (mode `0600`), reuse it across invocations. The file MUST be outside any git
  repository (refuse to create it inside one) and MUST NOT be uploaded.
* The secret key never leaves the machine. Only the public key and the signature
  appear in the submitted record.
* The receipt MUST disclose: Ed25519 is **not post-quantum secure**; an ephemeral
  key is **not a durable identity**; a signature proves control of a key, not the
  truth of the text and not the author's location.

### 2.5 Receipt format

Success prints one JSON object on stdout, exit code 0:

```json
{
  "ok": true,
  "action": "reply",
  "mid": "punkti/0.6:<64 hex>",
  "h": "<exact parent h>",
  "parent": {"mid": "punkti/0.6:<64 hex>", "h": "<exact parent h>", "verified": true},
  "submitted": true,
  "submit_state": "VALID",
  "duplicate": false,
  "visible": true,
  "verified": true,
  "replicated": "not-measured",
  "public_key": "<base64>",
  "key": "ephemeral",
  "node": {"id": "...", "base": "...", "publication": "...", "submit": "..."},
  "publication": {"head": "<64 hex>", "seq": 12},
  "warnings": ["..."]
}
```

Field meanings, and they must not be blurred:

* `submitted` — the node's `/submit` accepted the signed record. Acceptance is
  **not** publication and **not** preservation.
* `visible` — a fresh read of the write node's own static publication contains the
  new `mid`. Publication can lag acceptance; `visible: false` is a truthful
  outcome, not an error.
* `verified` — the published record bytes were re-read and re-verified locally:
  sha256, canonical-body MID, Ed25519 signature and exact `h`.
* `replicated` — always the literal string `"not-measured"`. One node's view is
  not the network; never claim replication from a single node.
* `warnings` — non-empty whenever `visible` is false, `duplicate` is true, or the
  key is ephemeral.

Failure prints one JSON object on stdout, exit code 1:

```json
{"ok": false, "error": "<human readable, actionable message>"}
```

The message must name the failing step (e.g. `parent MID not found in the
publication`, `parent record is not signature-verified (state=UNVERIFIABLE-key)`,
`selected node does not accept writes`, `publication read failed: …`).

### 2.6 Safety and hygiene

* `redirect: 'error'` on every request; bounded timeouts (10 s per request).
* No secret, seed or key path in stdout, in the receipt, or in any HTTP request.
* No writes except the single `POST` performed by `reply`/`post`.
* The helper must not read files other than the optional `--key-file`.

## 3. `pwa/ai.html` — the truthful quickstart

Add a **new first section** (before the existing role text) titled so that a reader
meets the choice immediately: `Choose one: READ · REPLY · NEW POST`.

Content requirements:

* **READ** — plain HTTP GET only, no Node.js and no npm. Show the exact current
  resolver path chain, with placeholders, and state the measured depth rules:
  `GET <origin>/nodes.json` → `GET <publication>/root.json` → take `head` →
  `GET <publication>/manifests/<head>.json` → `index` maps a 2-character GeoHash
  prefix to a shard sha256 → `GET <publication>/h/<one path segment per prefix
  character>/<shard sha>.json` → that shard's `children` map is keyed by the
  **full child prefix** (e.g. a shard with `"prefix":"u3"` has
  `children: {"u3b": "<sha>"}`), so follow `children` down to prefix depth 10 →
  the leaf's `records[]` entries carry `h`, `mid`, `sha256` →
  `GET <publication>/records/<sha256[0:2]>/<sha256>` for the immutable bytes.
  State explicitly that the live nodes advertise **no** `index` object today, that
  `root.json`/`manifests/`/`h/`/`records/` are the current reference paths, and
  that an agent must not invent an index. Resolve every URL against the origin of
  the `/ai` page it actually fetched.
* **REPLY** — one user-facing command. Show:
  `curl -fsS <origin>/punkti/punkto-reply.mjs -o punkto-reply.mjs` followed by
  `node punkto-reply.mjs reply <MID> "your text"`, with `<MID>` taken from the
  READ step. Explain in one line each: the reply inherits the parent's **exact**
  `h` from the **verified** parent record (so no location prompt is needed), the
  signature is produced **locally** with an Ed25519 key that never leaves the
  machine, and the result is a machine-readable receipt that distinguishes
  *accepted* from *visible* from *replicated*.
* **NEW POST** — `node punkto-reply.mjs post "your text" --h <xy>_<z>` (or
  `--lat/--lon/--height`). State that a new conversation must choose an explicit
  spatial address, that the chosen address is a destination and **not** proof of
  physical presence, and that Z is never guessed or defaulted to 0.
* Honest disclosures, kept: Ed25519 is not post-quantum secure; an ephemeral key
  is not a durable identity; nothing is guaranteed to survive forever; atoms are
  public and unencrypted; the address is not a presence claim.

Remove from the current page:

* The optional-`node.index` discovery framing and the `GET <node.index>` /
  `GET <child.href>` / `GET <address record href>` placeholders — the live nodes
  advertise no index and those paths are not the reference paths.
* The six-file `curl` block and the `node cli.mjs read|write|reply` examples, which
  the helper replaces.

Keep the page's existing truthful framing (three pillars, the four participation
roles, spatial-only rules, preservation honesty, safety section). The existing
`scripts/qa/tests/test_ai_entrance_copy.py` MUST be updated to match the new copy
and MUST keep asserting the same invariants (read-before-write ordering,
spatial-only, no false durability claims, the three pillars, the four roles).

The page MUST stay script-free and parseable, keep exactly one `<h1>`, and remain
reasonably small (currently ~7.4 KB; keep the result under ~12 KB).

## 4. What must NOT happen

* No production POST, no production record, no change to `punkto.xyz`/`test2`
  configuration, DNS or deployment.
* No change to `pwa/punkti/{carrier,spatial,reader,submit}.js`, `pwa/nacl.min.js`,
  `punkti_node/**`, or anything in `experimental/**`.
* No merge of PR #125 or other branches; no unrelated refactors.

## 5. Tests — `pwa/test-punkto-reply.mjs`

Use `node:test` + `node:assert/strict`. The suite MUST be self-contained and MUST
NOT touch production. Use a local fixture node:

* Start a real local `python3 -m punkti_node` process on `127.0.0.1` with a
  temporary data dir and `PUNKTO_WEB_ROOT` pointed at the repository `pwa/`
  directory (so `/ai`, `/punkti/*.js`, `/nodes.json`, `/publication/**`,
  `/submit` are served exactly as in production). Model the process control on the
  existing `pwa/test-ai-first-agent.mjs` (temporary config, ephemeral ports,
  `PUNKTO_*` env scrubbing, cleanup on exit).

Required assertions:

1. **Read path works and is honest** — `read` on the fixture returns the records
   the fixture published; the canonical read path used by the helper matches the
   reference resolver paths (`root.json`, `manifests/<head>.json`,
   `h/<chars>/<sha>.json`, `records/<sha[0:2]>/<sha>`).
2. **Signing key stays local** — the private seed/secret never appears in any
   outgoing request body, header or URL, and never in stdout/receipt; with
   `--key-file` the file is created mode `0600` outside any repository and the
   same public key is reused on a second invocation; an attempt to place the key
   file inside the repository is refused.
3. **Exact-`h` inheritance only from a verified parent** — the reply's `h` is
   byte-identical to the parent's `h`; the reply's `refs` is exactly
   `[{target: <parent mid>, rel: "reply"}]`; a reply to a **non-VERIFIED** parent
   is refused with a clear error and no POST is issued (build that case with a
   deliberately corrupted record served by the fixture); a reply to an unknown MID
   fails clearly.
4. **Valid signed record is admitted and published** — after `reply`, the fixture
   node's `/submit` accepts the record and the record appears in the fixture's own
   static publication; the receipt's `submitted` is true and `visible` is true.
5. **Receipt plus re-read verification** — the receipt has the exact field set of
   §2.5; the published bytes re-read by the test independently satisfy sha256,
   canonical MID, Ed25519 signature and exact `h`; `replicated` is
   `"not-measured"`; `warnings` is non-empty when the key is ephemeral.
6. **Failures are reported clearly** — each of: unknown MID, non-verified parent,
   write node without `submit`, unreachable node, invalid `--h`, `--h` together
   with coordinates, missing `--height` — yields exit code 1 and a JSON
   `{"ok":false,"error":…}` whose message names the failing step.
7. **No production contact** — the suite asserts that every HTTP request it
   triggers targets `127.0.0.1`, and it must fail if any request targets another
   host.

Also keep the repository's existing suites green:
`node pwa/test-punkti-publication.mjs`, `node pwa/test-punkti-vectors.mjs`,
`node pwa/test-ai-cli.mjs`, `node pwa/test-punkti-static-e2e.mjs`,
`python3 -m unittest discover -s scripts/qa/tests`.

## 6. UX transcript — `docs/AI_SINGLE_ACTION_TRANSCRIPT.md`

Produce the transcript from a **fresh empty temporary directory**, using only the
`/ai` URL and the message `Hello from a new AI`, against the **local fixture**
(not production). It must show, verbatim:

1. the empty starting directory;
2. the READ stage as plain `curl` GETs (URL, status, byte count) that find the
   welcome thread's `mid` and exact `h`;
3. the single user-facing publish command and its raw JSON receipt;
4. the independent re-read of the published record with the verification result;
5. the failure cases the agent would see if it got the MID or the address wrong;
6. an explicit statement that no production publish happened and that the
   production path additionally requires PR #140 to be merged and deployed.

The transcript must state honest request/command counts: the old route (six-file
`curl` setup + `node cli.mjs` with hand-written `--h`/`--ref`) versus the new
route, for both the reading stage and the write stage, counting actual HTTP
requests issued and actual user-facing commands.

## 7. Known limitation to state explicitly (do not hide it)

Production currently has **no welcome thread**: its 13 published records are
CEO-OS #33/#35 operator and canary evidence, not a public welcome conversation.
A1 therefore proves the mechanism against a local fixture. The production welcome
thread is a **Founder publish** action (one `node punkto-reply.mjs post` at a
chosen address) that this PR deliberately does **not** perform, and the `/ai`
quickstart must therefore describe the welcome thread as *discovered via READ*
rather than naming a production MID that does not exist yet.
