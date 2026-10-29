# CODEX TASK 31 — CEO-OS #31 Stage 0: blank-agent reference client + local two-node roundtrip harness

**Status:** ACTIVE (read this file and `AGENTS.md` before editing)
**Base:** `origin/main` (Fisker1111/Punkto, main = f4e6f87)
**Branch:** `feat/ai-first-stage0` (create from `origin/main`)
**CEO-OS issue:** https://github.com/Fisker1111/CEO-OS/issues/31
**Stage:** Stage 0 only (isolated development). **No deployment. No DNS. No merge. No push of any
branch other than `feat/ai-first-stage0`.** No production (`punkto.xyz`), no staging (`test2.punkto.xyz`)
writes, no node1/node2 changes.

## 0. Hard coordination boundary — CEO-OS #30 is live on a parallel branch

CEO-OS #30 (`punkti-org/punkti` PR #4 and the Punkto WIP branch
`wip/v0.6-spatial-only-correction`) is an active, unmerged spatial-only correction that removes
`h=""` and the `~` publication index. Its Punkto-side work touches at least:

```
pwa/ai.html
pwa/app.js
pwa/index.html
pwa/punkti/carrier.js
pwa/punkti/cli.mjs
pwa/punkti/reader.js
pwa/punkti/spatial.js
pwa/punkti/test-vectors/*.json
pwa/storage/atom-store.js
pwa/sync/punkti-client.js
pwa/test-ai-cli.mjs
pwa/test-ai-coldstart.mjs
pwa/test-ai-hostile.mjs
pwa/test-punkti-vectors.mjs
pwa/test-spatial-xy-z.mjs
pwa/ui-board.js
pwa/ui-create.js
pwa/ui-text.js
punkti_node/carrier.py
punkti_node/publication.py
punkti_node/spatial.py
punkti_node/test_spatial_only.py
experimental/**
.github/workflows/pilot-ci.yml   (touched by PR #125)
docs/CODEX_TASK_28.md             (added by PR #125)
```

**You must not edit any file in that list, and you must not rebase onto, merge, or cherry-pick any
unmerged #30/#124/#125 branch.** This task is deliberately **additive**: new files only, plus the
two documentation files named explicitly in §5. If a requirement cannot be met without editing a
listed file, **stop and report** the exact conflict instead of editing it.

If you believe the list is incomplete, re-check `git diff --stat origin/main...origin/wip/v0.6-spatial-only-correction`
(on the remote branch if fetchable) and extend the do-not-touch list before editing anything.

## 1. Goal

Deliver the code half of CEO-OS #31 Stage 0: a **blank-agent reference client** and a **local,
real-HTTP two-node roundtrip harness** that let an agent with no repository context:

1. `GET nodes.json` and discover advertised nodes (read path only, no account, no API key);
2. discover occupied geographic branches and their record counts from the **static publication**
   (HTTP GET only), then choose an **exact** `XY_Z` spatial address;
3. sign and publish a real canonical signed Punkti v0.6 atom with a **reusable** signing key
   (stable optional AI identity), receiving a verifiable MID/content address and SHA-256 receipt;
4. re-read the **static publication** over HTTP and verify its own atom (SHA-256, recomputed MID,
   signature, exact `h`);
5. on a second, independently keyed client, find the exact `h` and **reply at the same exact `h`**
   referencing the parent's MID, with the first client able to fetch and verify the reply;
6. run the whole thing between **two independent local node processes** (separate data dirs,
   separate ports), proving replication of the same canonical signed record through the frozen
   static GET mechanism.

Everything must run locally over real HTTP. No mocked network. No fabricated output.

## 2. Deliverables (new files only)

```
pwa/ai-first/agent.mjs            # blank-agent reference client (CLI)
pwa/ai-first/index.html           # minimal machine entrance for the local harness (served at /ai-first/)
pwa/ai-first/README.md            # how to run it, what it proves, what it does not prove
pwa/ai-first/keys.md.example      # example key-file layout (never commit a real key)
pwa/ai-first/coldstart.sh         # cold-start evidence run: fresh temp dir, only the /ai+nodes.json URL
pwa/test-ai-first-agent.mjs       # executable test suite (node, no framework beyond node:test/assert)
docs/AI_FIRST_WALKTHROUGH.md      # smallest readable GET path + signing/submission walkthrough
docs/AI_FIRST_ROLLOUT.md          # staged rollout/rollback, rate/size limits, security, metrics
docs/AI_FIRST_RECONCILIATION.md   # how PR #124 / PR #125 must be reconciled onto spatial-only v0.6
```

Plus exactly three edits to existing documentation files (allowed exceptions, listed in §5):
`README.md`, `CONTRIBUTING.md` and `docs/launch-candidate-checklist.md`. Do not edit any other
pre-existing file.

### 2.1 `pwa/ai-first/agent.mjs` — commands

A single self-contained Node CLI (Node 20.19+/22+) with subcommands. Use only the Node standard
library plus the repository's already-vendored `pwa/nacl.min.js` (require it exactly the way
`pwa/punkti/cli.mjs` does). **No new npm dependencies, no bundler, no build step.**

```
node pwa/ai-first/agent.mjs boot    [--nodes <nodes.json URL>]
node pwa/ai-first/agent.mjs discover --nodes <url> [--xy <prefix>] [--limit N]
node pwa/ai-first/agent.mjs publish  --nodes <url> --h <xy>_<z> --text <text> --key-file <path>
node pwa/ai-first/agent.mjs publish  --nodes <url> --lat <lat> --lon <lon> --height <m> --text <text> --key-file <path>
node pwa/ai-first/agent.mjs verify   --nodes <url> --mid <punkti/0.6:<64 hex>> [--h <xy>_<z>]
node pwa/ai-first/agent.mjs reply    --nodes <url> --parent-mid <mid> --text <text> --key-file <path>
```

Required behaviour:

* **boot** — `GET <nodes.json>`; validate `v === "punkti/bootstrap/1"` and that `nodes` is a
  non-empty array; print id/base/publication/submit per node; print the bootstrap notice
  ("starting point, not a trust authority, not a completeness claim").
* **discover** — pure static GET over the node's `publication` base:
  `root.json` → `manifests/<head>.json` → `h/<one char per path component>/<shard-sha>.json` →
  leaf `records[]` entries `{h,mid,sha256}`. Report occupied XY branches and **record counts per
  branch** (counts derived from the traversed shard tree; state in output how counts were derived),
  and list candidate exact `h` values. Never use a live database or a dynamic read endpoint.
  Verify the SHA-256 of every immutable object you fetch against the digest that referenced it,
  and fail loudly on mismatch.
* **publish** — requires an **explicit** spatial address: either `--h <xy>_<z>` or all three of
  `--lat/--lon/--height`. Reject `h=""`, reject a missing address, and reject a malformed or
  non-canonical `XY_Z` with a clear message. Never invent or default Z, never look up ground
  elevation, never claim physical presence — the address is a chosen destination.
  Build the canonical signed v0.6 record with the repository's frozen implementation
  (`pwa/punkti/carrier.js` — import it, do not modify it) and POST it with the repository's frozen
  submitter (`pwa/punkti/submit.js` — import it, do not modify it). Print the returned MID/content
  address, the record SHA-256, the publication head/seq, and whether it was a duplicate.
  **Signed acceptance ≠ publicly visible:** print a clear note that the atom is visible in the
  static publication only after the publisher's publication writer emits it.
* **verify** — GET the record bytes for a MID out of the **static publication**, recompute the
  record SHA-256, recompute the MID from the canonical body, verify the Ed25519 signature, and
  compare the exact `h`. Report per-check PASS/FAIL. If the MID is not yet in the publication,
  say so explicitly (publication lag) rather than failing opaquely.
* **reply** — take `--parent-mid`, read the parent out of the static publication, and reuse the
  parent's **exact** `h` string (never a re-derived one). Reference the parent with
  `refs: [{ target: <parent mid>, rel: "reply" }]`. Refuse to reply if the parent has no valid
  spatial address. Cross-address references are not replies — reject with a clear message.
* **Stable optional AI identity** — `--key-file <path>` holds a reusable Ed25519 secret key
  (32-byte seed, base64 or hex — pick one and document it). Create it on first use with mode
  `0600`; on later runs **load the same key** so the public key and therefore the author's
  continuity are stable across invocations. Print the public key (base64) so continuity is
  checkable. If `--key-file` is omitted, generate a clearly-labelled ephemeral key for that run
  only and say in the output that it is ephemeral and does not provide continuity.
  Never write a real key into the repository, the docs, or any committed file.
* **Honesty** — the agent must never claim that Ed25519 is post-quantum safe, that an address
  proves the author's physical presence, that a valid signature proves the payload is true, or
  that one node's view is the whole network.

### 2.2 `pwa/test-ai-first-agent.mjs` — executable tests

`node pwa/test-ai-first-agent.mjs` must run green from the repository root and print a summary.
Use only `node:test`/`node:assert` and the standard library (the existing suites in `pwa/` use
`node:assert/strict`; follow their style).

The suite must include, at minimum:

1. **Canonical/MID self-consistency** — sign an atom and independently recompute the MID and the
   record SHA-256 from the raw record bytes; both must equal what the submit path returned.
2. **Reusable key continuity** — two successive `publish` runs with the same `--key-file` produce
   the same public key; a fresh key file produces a different public key; the ephemeral mode is
   labelled ephemeral in its output.
3. **Explicit address enforcement** — `publish` with no `--h`/coordinates fails; with `h=""` fails;
   with a malformed `XY_Z` fails; with `--lat/--lon` but no `--height` fails; with a valid
   `--h` succeeds.
4. **Static GET discovery** — over a **local static HTTP server** serving a real frozen Punkti
   0.6 publication fixture (reuse the repository's existing fixture data, e.g.
   `experimental/punkti-v0.6-publication/vectors.json` / the existing `pwa/test-punkti-static-e2e.mjs`
   materialisation approach — read it, do not edit it), assert that `discover` finds occupied
   branches, reports counts, and that every fetched object digest matches.
5. **Two independent local nodes** — start **two separate node processes** with **separate data
   directories and separate ports**. Concrete pointers for the implementer (read the files, do
   not edit them):
   * `python3 -m punkti_node --config <file>` starts a node; `node/entrypoint.py` is the container
     entrypoint and `punkti_node/runtime.py` is the service loop.
   * Every setting can be supplied by **environment variable** (`PUNKTO_HOST`, `PUNKTO_PORT`,
     `PUNKTO_DATA_DIR`, `PUNKTO_PEERS`, `PUNKTO_PUBLICATION_PATH`, `PUNKTO_PUBLICATION_ENABLED`,
     `PUNKTO_WEB_ENABLED`, `PUNKTO_WEB_ROOT`, `PUNKTO_BOOTSTRAP_NODES`, `PUNKTO_SYNC_INTERVAL` —
     see the `ENV` table in `punkti_node/config.py`), which is the easiest way to run two nodes
     with different ports and data dirs from one checkout. `node-config.example.yml` is the
     canonical YAML shape.
   * Node A's static publication is written under its `PUNKTO_PUBLICATION_PATH` and served at
     `<base>/publication/…`; node B learns it through `network.peers` (`PUNKTO_PEERS`).
   * The **static-GET replication path already exists** in `punkti_node/store.py`:
     `PersistentNode.replicate_publication(peer_base)` reads the peer's published tree over
     HTTP with the frozen `Reader`, admits the records and republishes. Use that real path — do
     not invent a second protocol, and do not write a bespoke copy of the reader.
   * `/nodes.json` is served by `PersistentNode.special_route` from the `bootstrap.nodes`
     configuration, so each local node must advertise itself (and the other node) via
     `PUNKTO_BOOTSTRAP_NODES` for the client to find it.
   * Publish to node A with the client, verify in node A's static publication over HTTP, let node
     B import/republish the **same canonical signed record** from node A's static publication,
     and verify on node B via an independently configured client that the SHA-256, MID and
     signature all match. Then have a **second, differently keyed** client reply at the **same
     exact `h`**, and verify from node A that the reply is present, references the parent MID and
     is at the identical `h`.
   * If the two-process topology cannot be made to work with the repository's real startup path,
     do **not** fake it: implement the closest honest version (for example two node processes with
     an explicit static-publication pull), and record in the test output and in the README exactly
     what was and was not exercised, and why.
6. **Publication-lag honesty** — assert the client's output distinguishes "node accepted the
   signature" from "the atom is present in the latest static publication".

Every test must use real HTTP over `127.0.0.1` with ephemeral ports and must clean up its
temporary data directories. No network access to the public internet in the test suite.

### 2.3 `pwa/ai-first/index.html` — minimal machine entrance

A **minimal, self-contained** HTML machine entrance (the Stage-0 analogue of the existing
`pwa/ai.html`, but additive and not touching that file) that a blank agent can follow with
nothing but the URL it was given. It must:

* be valid standalone HTML, no external CSS/JS/fonts/CDN, no build step, dark-on-light readable,
  and small (aim for well under 10 KB);
* state, in a handful of short sections, exactly: **BOOT** (`GET /nodes.json`), **DISCOVER**
  (the static GET path `root.json` → `manifests/<head>.json` → `h/<chars>/<sha>.json` →
  `records/<sha[:2]>/<sha>`), **PUBLISH** (the exact `node …/agent.mjs publish --h <xy>_<z>
  --text … --key-file …` command), **VERIFY**, **REPLY** (same exact `h`), and **LIMITS** (no
  global coverage, no guaranteed persistence, address ≠ presence, Ed25519 is not PQ-safe,
  publication can lag signed acceptance);
* require an **explicit** `XY_Z` and never mention an unanchored write;
* refer to the client by a **relative** path so the same page works when the agent was given a
  different origin (e.g. `agent.mjs` next to the page, and `/nodes.json` at the site root);
* contain no unanchored example, no "never guess z → write unanchored" advice, and no claim of
  persistence or physical presence.

### 2.4 `pwa/ai-first/README.md` and `pwa/ai-first/keys.md.example`

* `README.md`: what the client does, the exact commands, what a successful run proves, what it
  does **not** prove (no global coverage, no persistence guarantee, no presence proof, no PQ
  security), the local two-node harness invocation, and an explicit statement that this is
  Stage 0 development evidence — **not** a live public-network experiment and not a deployment.
* `keys.md.example`: the on-disk key-file format, permissions, and a warning that key files are
  secrets. **No real key material.**

### 2.4 `docs/AI_FIRST_WALKTHROUGH.md`

The **smallest readable GET path** and the **first-agent signing/submission walkthrough**, written
for an agent that has never seen this repository. It must contain, in this order:

1. **Boot** — `GET <origin>/nodes.json`; what the bootstrap list is and is not (starting point,
   not a trust authority, not a completeness claim; one node = one published view).
2. **Discover** — the exact static GET sequence with the real reference paths:
   `root.json` → `manifests/<head>.json` → `h/<one character per path component>/<shard>.json` →
   leaf `records[]` → `records/<sha[:2]>/<sha>`. State that the paths are the reference
   implementation's non-normative layout and that an operator may map them differently. State
   that the GET sequence yields bytes, **not** verified authorship.
3. **Choose an address** — `h=<xy>_<z>`, XY = standard lowercase GeoHash 4–12 chars, Z = canonical
   exact signed decimal WGS84 **ellipsoidal** metres. **Never guess Z.** No map is required; an
   agent may reason about prefixes symbolically. The address is a chosen destination, **not**
   proof of physical presence.
4. **Sign and publish** — the exact `node pwa/ai-first/agent.mjs publish …` command, what the
   response means (MID = content address of the canonical body; the record SHA-256 = address of
   the stored signed bytes), and the distinction between **signed acceptance** and **visible in
   the latest static publication** (the publication can lag).
5. **Verify** — the exact `verify` command and what each check means (record SHA-256, recomputed
   MID, signature, exact `h`). A valid signature proves one key signed the bytes — not that the
   payload is true, and not that the author is a person or a robot.
6. **Reply** — the exact `reply` command; the parent MID is the reference; the reply must reuse
   the parent's **exact** `h`; cross-address references are not replies.
7. **What this does not prove** — no global coverage, no guaranteed persistence or propagation
   (persistence is maintained by replication and archives), no presence proof, no PQ security for
   Ed25519, one node's view is not the network.

Keep it short and concrete. Every command shown must be one that actually runs.

### 2.5 `docs/AI_FIRST_ROLLOUT.md`

The **staged rollout and rollback** plan for the isolated `test2.punkto.xyz` environment, plus
the operator safeguards. It must state plainly that **no deployment is authorised by this
document** — it describes what a future, separately authorised rollout would look like. It must
cover:

* **Preconditions** — spatial-only v0.6 re-frozen and Founder-accepted after independent
  conformance proof; #30 merged; PR #124/#125 reconciled; the `/ai` and `nodes.json` routes
  serving the current protocol.
* **Pre-flight inspection** — inspect the existing host and datastore first (what to look at:
  container image digest, node config, bootstrap list, data dir, publication path, existing
  atom count, Caddy route). Record the observed state before changing anything.
* **Staged steps** — isolated staging only, never production; one change at a time; each step
  with an explicit rollback action; data preservation and separate production/staging identities.
* **Public-write safeguards** — documented operator-side rate limits for `/submit` (size, count
  and frequency), storage/abuse/flooding controls, no login required for reads, immutable file
  cacheability preserved (reads stay static files over HTTP, compatible with Pi/nginx/CDN/
  Cloudflare caching; no live database on the read path).
* **Rollback** — exact procedure, including how to restore the previous image digest and how to
  keep the datastore consistent; state that a rollback must not leave the publication and the
  atom log disagreeing.
* **Metrics to capture** — CPU, cache hit ratio, GET counts/bytes, publication head/seq, submit
  rate, error rate; and how to measure them on the node.
* **Key custody and identity limits** — the reusable AI signing key is a **secret**; a lost key
  means a new identity; Ed25519 is not post-quantum safe; an ephemeral key provides no
  continuity; persistence comes from replication/archives, not from the key.

### 2.6 `docs/AI_FIRST_RECONCILIATION.md`

The reconciliation plan for the **unmerged** PRs #124 (docs READ block) and #125 (static
discovery index prototype), written against the spatial-only v0.6 correction. It must:

* For **#124** (`docs/AI_READ_BLOCK.md`): list every sentence that still describes the
  pre-correction world — in particular the `h=""` unanchored description, the `~` index, and the
  statement that unrestricted scope selects a hidden global bucket — and give the exact
  spatial-only replacement wording for each. Do **not** modify PR #124 or its branch.
* For **#125** (static GeoHash density index): state that the discovery index must contain **no
  unanchored terminal** after the correction, that occupied-branch counts and the GET-only
  fallback must remain correct with anchored-only records, and that the index is a derived
  Layer-4 artifact that must not change the frozen Layer-3 publication contract. Do **not**
  modify PR #125 or its branch.
* Record the **file-overlap map** between PR #124 / PR #125 and the spatial-only correction
  branch, so a single integrator can sequence the three changes without conflicting edits.
* Recommend the integration order and state explicitly that none of it is merged or deployed yet.

## 2.7 Verified implementation notes (Hermes already proved these — do not rediscover them)

Hermes ran a workspace-only probe against the **repository's existing, unmodified modules** and
confirmed the whole roundtrip works. Use these facts; do not spend the run rediscovering them.
The probe script and its real output are in the task workspace
(`evidence/probe-full-roundtrip.sh`, `evidence/probe-full-roundtrip.txt`).

* **Two independent node processes start cleanly** with no config file at all, purely from
  environment variables:
  ```bash
  PUNKTO_HOST=127.0.0.1 PUNKTO_PORT=<port> PUNKTO_DATA_DIR=<dir> \
  PUNKTO_PUBLICATION_PATH=<dir>/publication PUNKTO_WEB_ENABLED=true \
  PUNKTO_WEB_ROOT=<repo>/pwa PUNKTO_PEERS= PUNKTO_SYNC_INTERVAL=3600 \
  python3 -m punkti_node
  ```
  Both answer `/health` with `{"service":"punkti-node","status":"ok","version":"0.6.0-draft.1"}`
  and serve their own `/publication/root.json`.
  **Do not pass `--config`**: `python3 -m punkti_node --config /dev/null` fails with
  `configuration must be a YAML mapping`, because an empty file is not a YAML mapping. Omit
  `--config` and use the environment variables above.
* **`/nodes.json` returns an empty node list** until `PUNKTO_BOOTSTRAP_NODES` is set. For the
  harness, set `PUNKTO_BOOTSTRAP_NODES` to a JSON array of
  `[{"id":"a","base":"http://127.0.0.1:<portA>","publication":"http://127.0.0.1:<portA>/publication","submit":"http://127.0.0.1:<portA>/submit"}]`
  so the client can find the node.
* **Signing key format**: `nacl.sign.keyPair.fromSecretKey()` requires the **64-byte** secret key
  and throws `bad secret key size` for a 32-byte seed. Use
  `nacl.sign.keyPair.fromSeed(seed32)` instead — it takes the **32-byte seed** and returns
  `{publicKey, secretKey}` where `secretKey` is the 64-byte value that `encodeRecord()` requires.
  This is exactly the shape a reusable key file should store: the **32-byte seed**, from which
  the 64-byte secret key and the public key are both derived.
* **`replicate_publication(peer_base)` expects the peer’s PUBLICATION base**
  (`http://host:port/publication`), **not** the node base. Passing the node base fails with
  `HTTP Error 404` → `PublicationReadError: missing object`. With the publication base it
  returns the republished state, e.g.
  `{'v': 'punkti/pub/0.6', 'seq': 2, 'head': '350c5af0…'}`.
* **The roundtrip is confirmed to work** with the repo's own modules, in this order:
  1. `encodeRecord(atom, secretKey)` from `pwa/punkti/carrier.js` → `{address, mid, sha256, record}`;
  2. `POST <node>/submit` with `{records:[{address, sha256, record}]}` → HTTP 200,
     `results[0].state === "VALID"`, `admitted: true`, plus the new publication `head`/`seq`;
  3. the record is then readable out of the node's **static publication** over plain HTTP at
     `publication/root.json` → `manifests/<head>.json` → `h/<chars>/<sha>.json` → leaf `records[]`
     → `records/<sha[:2]>/<sha>`, and the recomputed SHA-256 of the fetched bytes **equals** the
     leaf entry’s `sha256` **and** the submitted `sha256`;
  4. `replicate_publication()` on node B produces node B’s own static publication with the
     **same** head and the **same** leaf entry, and node B’s copy verifies byte-identically;
  5. a second, **differently keyed** client can submit a reply with
     `refs:[{target: <parent mid>, rel:"reply"}]` at the **exact same `h`** (e.g.
     `u3butz7k9q_23`), and the reply is then readable out of node A’s static publication with
     its own MID/SHA-256 verified, at the identical `h`.
  Confirmed public keys differed between the two clients while the `h` string was byte-identical.
* **Publication lag is real and observable**: the `POST /submit` response already carries the new
  `head`/`seq`, and the static publication is updated in the same request — but a client that
  read the publication *before* the submit sees the old head. The client must therefore re-read
  the publication after publishing and report "accepted but not yet visible" rather than fail
  opaquely when the MID is absent.
* **`h` values observed live** (valid canonical `XY_Z`, safe to use in tests):
  `u3butz7k9q_23`, `u3butz7k9q7v_12`, `9q8zhuvubq_227`, `u33dc0cpnp45_34.5`.

## 3. Constraints

* No new dependencies. No npm install. No bundler. Node standard library + the repo's existing
  vendored `pwa/nacl.min.js` + the repo's existing Python dependencies (`PyYAML`, `cryptography`,
  already in `node/requirements.txt`).
* Do not change the protocol, the canonical framing, the publication format, the reader, the
  submitter, or the node. **Import** the frozen implementations; never fork them into new files.
* Do not add new Layer-3 semantics, no registries, no new APIs, no login, no rate-limit bypass.
* Do not merge or modify PRs #124, #125, #123. Do not create new CI workflow jobs.
* Do not commit credentials, tokens, private keys, or the contents of `~/.codex` / `~/.ssh`.
* Keep the diff additive and small. One focused commit for the code + tests, one focused commit for
  the docs. Use the repository's existing commit style (see `git log --oneline -10`).
* Python `3.14` and `node v26` are available in this environment; `cryptography` and `PyYAML` are
  installed. Verify with `python3 -c "import cryptography, yaml"` and report a blocker instead of
  vendoring a substitute if they are missing.

## 4. Acceptance criteria (all must be met before you report)

1. `node pwa/ai-first/agent.mjs --help` (or a usage line) works; every subcommand behaves as
   specified above.
2. `node pwa/test-ai-first-agent.mjs` exits 0 and prints a per-test summary.
3. `python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication`
   still passes (you changed nothing there, but prove it).
4. `node --check pwa/ai-first/agent.mjs` and `node --check pwa/test-ai-first-agent.mjs` exit 0.
5. `git diff --check` is clean; the diff contains **only** the files listed in §2 plus `README.md`
   and `CONTRIBUTING.md`; no file from the §0 do-not-touch list appears in `git diff --name-only`.
6. The test output contains **real** MID values, real record SHA-256 values, real publication
   head/seq values and real HTTP interactions — no placeholders, no `TODO`, no skipped critical
   test without an explicit, justified note.
7. `pwa/ai-first/coldstart.sh` exists, is executable (`chmod +x`), and performs a **cold-start**
   run: it creates a **fresh temporary directory**, copies only the client files into it (no
   repository checkout, no package install, no repository context), and drives
   `boot → discover → publish → verify` against a **local** node, printing every real HTTP
   request/response summary it makes. It must accept the node's `nodes.json` URL as its only
   required argument, so the same script can be pointed at a local node or, later, at an
   isolated staging node once the Founder authorises it. It must refuse to write into the
   repository and must never place a key file inside the repository tree.

## 5. The three allowed edits to pre-existing files

* `README.md` — add **one** clearly delimited section near the top titled
  "Current Punkto 0.6 path (one runnable path)" that:
  - states that the older `p:<12-char-3D-geohash>` deep links, `/latest`, `/feed`, `/atom`
    relay and the older `punkto.*.md` docs are **legacy** and describe an earlier protocol;
  - gives exactly **one** current runnable path for the v0.6 static publication + submit flow,
    pointing at `pwa/ai-first/README.md`, `docs/AI_FIRST_WALKTHROUGH.md` and the `/ai` page;
  - does not delete or rewrite any legacy section, and does not claim that any of it is current.
* `CONTRIBUTING.md` — add **one** clearly delimited section "Working on the current Punkto 0.6
  path" pointing contributors at `AGENTS.md`, `docs/AI_FIRST_WALKTHROUGH.md` and this task's
  additive-first rule; mark the older relay-era instructions as legacy.
* `docs/launch-candidate-checklist.md` — this file is dated 2026-06-22 and contains legacy
  checks and unchecked public-alpha gates; it is **not** current launch proof. **Replace its
  content with a short, current, 0.6-specific gate** (roughly 20–40 lines): what must be true
  before a public AI invitation / public write network is announced. Do **not** resurrect the 35
  obsolete checks. The gate must cover, at minimum: (a) spatial-only v0.6 re-frozen and accepted
  by the Founder after independent conformance proof; (b) `/ai` + `nodes.json` reachable and
  serving the current protocol; (c) a real cold-agent roundtrip archived (discover → signed
  anchored publish → static GET verification → independent peer verification → same-`h` reply);
  (d) public-write safeguards: submit rate/size limits, storage/abuse controls, key custody
  documented, backups and a tested rollback; (e) privacy wording re-reviewed for a global public
  spatial memory; (f) a sanitized reproducible trace archived before any portability/persistence
  claim. Mark the whole file clearly as a **pre-alpha gate**, not proof of readiness, and record
  today's date and the fact that it supersedes the 2026-06-22 list.

Both the README and CONTRIBUTING edits must be short, factual and clearly marked as an addition.
Do not reformat, reorder or "fix" anything else in those files.

## 6. Report back

Report, in plain text:
* the branch name and the exact commit SHAs you created;
* the full list of files added/changed;
* the exact commands you ran and their real output summaries (test counts, pass/fail);
* the real MIDs, record SHA-256 values, publication head/seq values and the two nodes' URLs/ports
  used in the two-node roundtrip;
* precisely what the two-node test exercised and what it did **not** exercise;
* any place where you had to deviate from this brief, and why;
* confirmation that `git diff --name-only origin/main...HEAD` contains no §0 do-not-touch file.

**Do not push, do not tag, do not merge, do not deploy.** Hermes reviews the diff, then pushes the
branch and opens the draft PR.
