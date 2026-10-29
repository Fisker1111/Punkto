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
5. **Two independent local nodes** — start **two separate node processes** (`python3 -m punkti_node`,
   see `punkti_node/runtime.py` / `node-config.example.yml` and `punkti_node/test_node.py` for the
   real startup and config shape) with **separate data directories and separate ports**, publish an
   anchored atom to node A through the client, verify it in node A's **static publication** over
   HTTP, let node B import/republish the same canonical signed record from node A's static
   publication (the node already has a static-GET replication path — find it, use it, do not
   invent a second protocol), and verify on node B via an independently configured client that the
   SHA-256, MID and signature all match. Then have a **second, differently keyed** client reply at
   the **same exact `h`**, and verify from node A that the reply is present, references the parent
   MID, and is at the identical `h`.
   * If the two-process topology cannot be made to work with the repository's real startup path,
     do **not** fake it: implement the closest honest version (for example two node processes with
     an explicit static-publication pull), and record in the test output and in the README exactly
     what was and was not exercised, and why.
6. **Publication-lag honesty** — assert the client's output distinguishes "node accepted the
   signature" from "the atom is present in the latest static publication".

Every test must use real HTTP over `127.0.0.1` with ephemeral ports and must clean up its
temporary data directories. No network access to the public internet in the test suite.

### 2.3 `pwa/ai-first/README.md` and `pwa/ai-first/keys.md.example`

* `README.md`: what the client does, the exact commands, what a successful run proves, what it
  does **not** prove (no global coverage, no persistence guarantee, no presence proof, no PQ
  security), the local two-node harness invocation, and an explicit statement that this is
  Stage 0 development evidence — **not** a live public-network experiment and not a deployment.
* `keys.md.example`: the on-disk key-file format, permissions, and a warning that key files are
  secrets. **No real key material.**

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
