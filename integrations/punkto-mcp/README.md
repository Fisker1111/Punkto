# Punkto MCP M1 / M3 CPU / M6 discovery

MCP is an **optional convenience entrance** to one node's published Punkti view.
Plain HTTP through `/ai` remains the universal fallback; it is never redirected or changed.
This read-only, stateless Worker serves only `POST /mcp` using Agents' default MCP
host/CORS handling. It fetches only publication objects from `https://punkto.xyz`,
falling back to `https://test2.punkto.xyz` only after transport failures (including
timeouts) or 5xx. Missing objects, redirects and digest failures do not trigger fallback.
HTTP 429 deliberately returns `upstream_unavailable` with “Publication rate limited;
retry later.” without retry or fallback, and never includes the upstream body.

## Quickstart (public, read-only)

Canonical endpoint: **https://punkto.xyz/mcp**. Direct Worker fallback:
**https://punkto-mcp.sunebech.workers.dev/mcp**. The canonical apex URL is a
Caddy exact-path proxy on node1 to the Cloudflare Worker; the workers.dev URL
is the Worker itself. Both serve the same read-only adapter. There is no write,
publish or submit tool.

Use POST with `Content-Type: application/json` and
`Accept: application/json, text/event-stream`. Both media types in Accept are
required; omitting the pair returns HTTP 406. Successful RPC responses have
`Content-Type: text/event-stream` and a single `event: message` frame.
`notifications/initialized` instead returns HTTP 202 with an empty body.
GET/HEAD/PUT/DELETE/OPTIONS on `/mcp` return HTTP 405 with the route error
`{"error":"method_not_allowed"}` (HEAD has no wire body); paths other than `/mcp`
return HTTP 404 with `{"error":"not_found"}`.

```bash
curl --fail-with-body 'https://punkto.xyz/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"quickstart","version":"1.0.0"}}}'
```

Send each of these JSON-RPC bodies separately with the same URL and headers:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"read_place","arguments":{"h":"s00000000000_0"}}}
```

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"discover_places","arguments":{"limit":5}}}
```

```json
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_record","arguments":{"sha256":"21cbb254c6902c1ae3c5ccb573f34e476cafdc6ac8f9205ea366ba728cd9379a"}}}
```

Generic remote HTTP MCP server configuration (adapt the enclosing keys to your
client; this is not a vendor-specific tested configuration):

```json
{"url":"https://punkto.xyz/mcp"}
```

The client must send POST with the Content-Type and Accept headers above.

| Tool | Arguments | Defaults | Clamping | What it returns | Typed error codes |
| --- | --- | --- | --- | --- | --- |
| `read_place` | Optional canonical `h` string; optional integer `limit` ≥ 1 | `h: s00000000000_0`, `limit: 4` | Above 8 → 8 with `limit_note` | Exact-address records with projected text, MID, record digest/URL/size, publication snapshot, trust and fetch accounting | `invalid_h`, `not_found_in_publication`, `upstream_missing_object`, `upstream_unavailable`, `upstream_timeout`, `upstream_redirect_refused`, `corrupt_object`, `object_too_large`, `fetch_budget_exceeded`, `internal_error` |
| `get_record` | Required `sha256`: 64 lowercase hex, never MID; optional boolean `include_raw` | `include_raw: false` | No clamping; raw inclusion above 32768 record bytes rejected | Digest-checked record metadata, projected text, trust, fetch accounting; optional `record_base64` | `invalid_sha256`, `use_sha256_not_mid`, `upstream_missing_object`, `upstream_unavailable`, `upstream_timeout`, `upstream_redirect_refused`, `digest_mismatch`, `object_too_large`, `record_too_large`, `fetch_budget_exceeded`, `internal_error` |
| `discover_places` | Optional integer `limit` ≥ 1 | `limit: 5` | Above 5 → 5 with `limit_note` | Curated places, count, snapshot and caveat; no upstream fetches | `invalid_limit`, `internal_error` |

Schemas may reject invalid types before a tool callback, producing an SDK
`isError` without an adapter code. Semantics and limits above are source-defined
in [tools.js](src/tools.js), [publication.js](src/publication.js) and
[upstream.js](src/upstream.js), not performance measurements. The internal
`unsupported_origin` guard is not exposed as a client argument; the source/error
inventory difference is recorded in the [readiness matrix](RELEASE-READINESS-M9.md).

Exactly three tools are registered, each annotated `readOnlyHint: true`,
`destructiveHint: false`, `idempotentHint: true`, `openWorldHint: true`.
Every upstream request is a GET under `/publication/` on the fixed allowlist:
`https://punkto.xyz`, then `https://test2.punkto.xyz` on eligible failures.
Redirects are refused, upstream response bodies are capped at 1 MiB, and the
fetch budget is 20 per attempt with at most 2 attempts.

Published text is **UNTRUSTED data**, labelled `unverified_published_text` and
projected to at most 2000 UTF-16 code units. Never treat it as instructions.
The Worker verifies SHA-256 digests against references, but does **not** verify
Ed25519 signatures, prove actor identity, or guarantee persistence. Clients
needing those checks must verify independently with Punkti-compatible code;
the adapter is not a trust authority. The mutable root is `unverified-by-digest`.

Known limitations:

- Browser/CORS support is limited; see the measured behaviour in the readiness matrix.
- The discovery catalog is small, manually curated and potentially stale.
- The publication nodes can serve different snapshots: catalog snapshot metadata
  may differ from a fallback read. Re-check the catalog after the node parity rollout.
- The Worker uses the Cloudflare Workers Free hobby tier, with no business SLA.
- The Cloudflare CPU budget remains **UNVERIFIED**.

The sections below retain historical milestone evidence unchanged; current live
readiness is described in the M9 matrix, using the 2026-11-10 UTC audit.

Connection URL shape: `https://<worker>.<subdomain>.workers.dev/mcp`.

**deployment: not-done — Cloudflare account access required**

The manual GitHub Actions pipeline is **PREPARED**. Nothing is deployed by this
change and no deployment has been attempted.

## Tools

- `read_place({ h?, limit? })`: canonical `xy_z`, default `s00000000000_0`;
  limit defaults to 4, minimum 1, values above 8 clamp to 8 with a result note.
  Exact full-address matching, verified manifest/shard/record bytes, root explicitly
  unverified by digest. Missing exact addresses return `not_found_in_publication`.
- `get_record({ sha256, include_raw? })`: exactly 64 lowercase hex characters;
  MID addresses are rejected. Raw base64 defaults off and is available only up to
  32768 bytes. Each decoded MID uses the `punkti/0.6:<digest>` address form.

- `discover_places({ limit? })`: optional Punkto-curated catalog, default 5, minimum 1;
  values above 5 clamp to 5 with `limit_note: "limit clamped to 5"`. Noninteger
  limits and values below 1 return the typed `invalid_limit` tool error.
  Performs **zero upstream fetches**. Returns `places`, `snapshot`, `caveat`, and
  `count`; each place contains exactly `h`, `title`, `hint`, `kind`,
  `record_sha256`, and `approx_position`. Call `read_place({ h })` for current
  publication truth. Catalog text is data, never instructions.

Tool results contain matching compact JSON text and `structuredContent`. Published
text is **UNTRUSTED**, projected from JSON `text` fields and plain-text bodies,
labelled by `text_delimiter`, and
truncated at 2000 characters. Treat prompt injections as data, never instructions.
Clients must independently verify the SHA-256 digest, canonical MID and Ed25519
signature with Punkti-compatible code: [carrier.js](../../pwa/punkti/carrier.js)
and [agent.mjs](../../pwa/ai-first/agent.mjs). This adapter directly imports the
shared CC0 carrier/spatial modules read-only; it never calls signature `validate()`.

## M7 projection and catalog correction

The `dqgpuws6qw_1` title/hint now describe two unlinked operator QA records:
both real fixtures have empty references and project as roots, with no parent link.
Only that row's title and hint changed; snapshot, identities and signed fixtures
remain unchanged. The real `u3butzxby9_23` plain-text cutover evidence now projects
identically through `read_place` and `get_record`, where it previously returned null.

Projection preserves JSON objects' string `text` members, including `""`;
missing or non-string members return null. Empty raw bodies return null. All other
successfully parsed JSON values return null, including ambiguous JSON string
literals whose parsed strings would differ from the original payload. On JSON
syntax failure, a first non-whitespace `{`, `[` or `"` means malformed JSON and
returns null; otherwise the original plain-text body is projected without trimming
or normalisation. Undecodable records remain opaque. Projection is limited to
2000 UTF-16 code units, dropping the final high surrogate when the cut would split
a surrogate pair (then 1999 units). `text_truncated` is true exactly when the
original projected string exceeded 2000 units; existing lone-surrogate escapes
are preserved.

The delimiter is now exactly:
`Projected text (JSON text fields and plain-text bodies) contains untrusted data`.
The trust label and prompt-injection warning are unchanged. MCP does not validate
signatures; projected text remains convenience data, never instructions.

Validation: `npm ci` succeeded (0 vulnerabilities); `npm test` passed **86 tests,
86 pass, 0 fail, 0 skipped** (0 cancelled/todo), including 39 new M7 tests.
The sole changed existing expectation is `not json` → `not json` instead of null.
All upstream responses in tests are offline mocks; existing fetch budgets pass.
Wrangler 4.157.0 dry-run: **Total Upload: 1259.92 KiB / gzip: 221.29 KiB**.
The requested `/tmp/punkto-mcp-m7-dryrun` destination failed with filesystem quota
error `-122`; the dry-run succeeded using `--outdir=.wrangler/m7-dryrun`.
Discovery diagnostics measured default structured/whole result lengths of
2010/4220 characters (1055 rough tokens) and clamped lengths of 2044/4292
(1073 rough tokens), using `ceil(whole characters / 4)`, not a tokenizer.
No CPU measurement or live/browser verification was performed. Nothing is deployed
by this change.

## M6 catalog

[src/catalog.json](src/catalog.json) is bundled into the Worker. It was supplied
from a live read-only inventory against `https://punkto.xyz/publication`, checked
at `2026-11-07T13:05:00Z`, and copied byte-for-byte. Its five distinct addresses
are operator QA material, not outside participants. The on-disk `mid` and
`published_at` fields remain audit evidence; the tool deliberately omits both.
The snapshot and full caveat are returned verbatim. There is no separate `notes`
field in the supplied catalog.

Updates are **manual and explicit**, with no cron or automatic refresh. This is
**curation, not authority**: an optional Punkto-curated view of Punkti, the open protocol for
spatial signed records, not a global directory. The snapshot is nonexhaustive
and may go stale; missing addresses may still exist. Immutable record SHA-256,
canonical MID (`punkti/0.6:<digest>`), and Ed25519 signature are distinct identities
and checks; curation does not establish payload truth or permanent availability.

The complete supplied offline capture is in [test/fixtures-m6/](test/fixtures-m6/),
with its unchanged [provenance](test/fixtures-m6/provenance.json): 15 records,
10 distinct addresses, root, manifest, and all branch shards. It is a sibling of
`test/fixtures/` so the existing recursive fixture tests keep their original inputs.
No existing fixture was changed. Tests recompute all captured object hashes and
catalog record MIDs, discover and read all five non-default addresses, check
hostile text and redirect refusal, and enforce GET-only allowed publication URLs.

To verify that the catalog is still truthful against the live publication, run
`node scripts/live-m6-check.mjs` from this directory. This is an explicit online
maintenance / verification command, **never a test step**. It performs only
credential-free GETs under `/publication/` on `https://punkto.xyz` (with the
adapter's transport/5xx fallback to `https://test2.punkto.xyz`), refuses redirects,
and writes no files. It prints a verdict for each place and exits non-zero if an
address fails to resolve or its record SHA-256 / canonical MID differs from the
catalog. It also reports measured discovery sizes and upstream fetch counts.

Measured compact response sizes (excluding JSON-RPC envelope):

| discover_places | Structured characters | Whole-result characters | Rough tokens |
| --- | ---: | ---: | ---: |
| Default five entries | 1964 | 4128 | 1032 |
| Clamped limit 99 | 1998 | 4200 | 1050 |

Rough tokens are `ceil(whole characters / 4)`. Both representations remain;
`content[0].text === JSON.stringify(structuredContent)`. Both cases fit the
amended 2100 / 4400 character budgets and make **0 upstream fetches**.

M6 validation: `npm ci` succeeded; `npm test` passed **47 tests, 47 pass,
0 fail, 0 cancelled, 0 skipped, 0 todo** (all 40 existing tests plus 7 M6 tests).
Only the existing tools/list assertion and title changed to expect three tools.
No browser, live network, or deployed runtime acceptance was performed for M6.

## Budgets and operation

Workers Free: 100,000 requests/day, 10 ms CPU/invocation, 50 subrequests/request.
We cap upstream fetches at **20 per origin attempt**, at most **2 attempts**:
worst-case **40**, not 20 per invocation. A successful uncached traversal needs
at most **19** (root + manifest + 9 shards + 8 records). Fallback restarts the whole
snapshot; reported counts include failed attempts. Concurrency is at most 4;
fetch timeout 4 seconds; each fetched object at most 1 MiB. Immutable verified
objects use the optional Workers Cache API; `root.json` is never cached.
`workers.dev` is a hobby/initial environment, not a business-grade SLA.

From this directory, use `npm ci`, `npm test`, or `npm run dev`. Tests use Node's
built-in runner and the real `createMcpHandler` with Requests and a stub execution
context; **all upstream responses are offline mocks**. `npm ci && npm test`
passed initially with 31 tests; after adding 429 coverage, `npm test` passed on
Node v26.9.0: 32 tests, 32 passed, 0 failed/cancelled/skipped/todo,
0 suites (2085.766403 ms). No local workerd test fallback is needed.

Local bundle check: `npx wrangler deploy --dry-run --outdir=/tmp/punkto-mcp-dryrun`
(Wrangler 4.157.0) exited 0: `Total Upload: 1254.73 KiB / gzip: 219.15 KiB`,
`No bindings found.`, `--dry-run: exiting now.` This is local-only: no upload,
authentication, or account. It proves the Worker bundles, including cross-directory
`../../../pwa/punkti/carrier.js` and `spatial.js` imports; it is NOT a Cloudflare
runtime acceptance test.

The orchestrator's addendum records local workerd (Miniflare) runtime acceptance
using `npx wrangler dev --local` against live `https://punkto.xyz`: initialize,
exactly two read-only tools, both real Null Island records (13 fetches, 12 verified
objects), `get_record` (447 bytes, correct MID), raw base64, limit clamping, typed
errors and unknown-method handling passed. This was runtime acceptance against
live publication, not a deployed Cloudflare Workers test. Cold/warm `read_place`
wall times of 0.41/0.15 s include network wait and are not CPU; local workerd does
not expose Cloudflare CPU accounting, so the Free 10 ms budget remains UNVERIFIED.

Fixtures were captured using GET only from `https://punkto.xyz/publication/` at
2026-11-04T13:44:12.089868+00:00 by `python3 scripts/capture-fixtures.py`.
The live root (seq 14, head `c77ba862be21e00d37bdc62f35bac7359d09698d19cd4ef8b2ce5be33ff0a9e5`),
its manifest, nine shards (`s0` through `s000000000`), and both Null Island raw
records are byte-identical captures. The leaf already contained exactly those two
records; no trimming or rehashing was necessary. Full paths and SHA-256 hashes are
in [provenance.json](test/fixtures/provenance.json). Record digests:
- ROOT: `2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d`
- REPLY: `0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b`

These contain published public keys/signatures; no `validate()` call or signature
verification is performed. Injection coverage generates a separate inline record.
The capture utility is an explicit online maintenance command, never a test step.

## M3 offline CPU evaluation (Issue #46)

Baseline commit: `5c23c1a2bb57101e860bd5683137feef719d30e8`. The harness
archives that tree to a temporary directory and loads it alongside optimized source
in **one Node process**, sharing the exact installed, lockfile-checked dependencies.
For each tool/path it alternates baseline, optimized for **50 pairs**. Fixture-only
GETs, cache disabled, no warm-up and no discarded samples. RPC includes request
creation and response consumption; invoke measures the inner tool path separately.
All raw samples, fetch counts, sizes and paired differences are in
[test/measurements.json](test/measurements.json), alongside historical M1 evidence.
CPU is `process.cpuUsage()` user + system; p95 uses nearest rank.

| Path / tool | Variant | Min ms | Median ms | p95 ms | Max ms | >10 ms / 50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| rpc / read_place | baseline | 3.0410 | 5.5890 | 13.4130 | 211.1290 | 8 |
| rpc / read_place | optimized | 2.8770 | 5.8350 | 14.2940 | 55.1310 | 11 |
| rpc / get_record | baseline | 1.4910 | 1.9020 | 5.4760 | 6.6550 | 0 |
| rpc / get_record | optimized | 1.3910 | 1.8950 | 3.8590 | 9.3020 | 0 |
| invoke / read_place | baseline | 1.7220 | 2.4365 | 5.5010 | 12.7270 | 2 |
| invoke / read_place | optimized | 1.4880 | 2.2740 | 5.9600 | 9.6100 | 0 |
| invoke / get_record | baseline | 0.2610 | 0.3855 | 0.8960 | 2.3410 | 0 |
| invoke / get_record | optimized | 0.2420 | 0.3650 | 0.8330 | 1.3370 | 0 |

| Path / tool | Paired median Δ ms (optimized − baseline) | Optimized faster |
| --- | ---: | ---: |
| rpc / read_place | -0.0755 | 56% |
| rpc / get_record | -0.0615 | 54% |
| invoke / read_place | -0.1885 | 66% |
| invoke / get_record | -0.0165 | 68% |

Uncached fetch/verification counts remain 13/12 for `read_place` and 1/1 for
`get_record` in every sample; paired structured results are asserted identical.
The RPC read paired median difference is **−0.0755 ms**, with optimized faster
in **56%** of pairs. This is weak evidence: paired differences range from
−190.633 to +45.754 ms (p95 +5.531 ms). Cold first calls, shared JIT/GC and fixed
baseline-first order remain confounders; pairing does not eliminate them.
A stable whole-RPC speedup is not established. Do not subtract RPC and invoke
medians to infer SDK overhead.

**Local Node CPU numbers are NOT the Cloudflare Free 10 ms metric. The Free budget
remains UNVERIFIED until a manual, Founder-approved deploy and representative
per-method Cloudflare measurements.** No deployment was performed. The Founder's
4 invocations / 13 subrequests / 0 errors, “CPU time summary 12 ms” and deployment
median 26.29 ms are mixed-method, tiny-sample observations, not a per-method p95.

### Accepted changes and isolated handler measurement

The handler now lives once at module scope, following the installed Agents 0.33.0
[server documentation](node_modules/agents/docs/mcp-servers.md) (line 62) and
[transport documentation](node_modules/agents/docs/mcp-transports.md) (line 7).
The factory still creates and registers a **fresh McpServer per request**.
`route: '/mcp'`, `legacy: 'stateless'`, `responseMode: 'auto'` are unchanged.

The separate handler-lifetime experiment uses identical optimized tool code and
SDK in both arms, alternating per-request construction and module-scope reuse for
50 RPC `read_place` pairs in the same process:

| Handler lifetime | Min ms | Median ms | p95 ms | Max ms | >10 ms / 50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| per_request | 2.3990 | 4.0260 | 8.5140 | 14.7530 | 1 |
| module_scope | 2.9590 | 4.2685 | 9.3350 | 18.1360 | 2 |

Measured paired saving (per-request minus module-scope) is **−0.3040 ms**:
reuse was slower at the paired median and faster in only **36%** of pairs.
Optimized-minus-baseline differences range from −4.893 to +5.715 ms, p95 +3.383 ms.
This run does **not** reproduce the orchestrator's ~0.9 ms saving. The documented
lifetime is adopted and allocation is removed, but a positive per-request CPU
saving is not claimed from these noisy local measurements.

The retained component experiment alternates before/after order across 50 paired
samples of **1000 operations each**. These are **batch CPU milliseconds**, not
per-request CPU, and cannot be added to or subtracted from invocation results.

| Accepted change | Batch median before → after ms | Batch p95 before → after ms |
| --- | ---: | ---: |
| Local digest hex formatting | 4.9845 → 1.1260 | 8.288 → 3.076 |
| Reused fatal UTF-8 decoder | 0.4245 → 0.3465 | 1.996 → 1.463 |
| Compact text fallback, both representations retained | 19.1750 → 17.2265 | 24.210 → 21.694 |

These historical round-1 batch results are retained with their raw samples.
The decoder uses synchronous non-streaming fatal decoding; recovery after malformed
UTF-8 is tested. Individual whole-RPC gains cannot be attributed to these batches.

### CPU analysis and rejected alternatives

| Area | Evidence and decision |
| --- | --- |
| Cold start / initialization | First RPC samples are retained and include lazy initialization/JIT. Module imports happen before sampling. Neither Node imports nor bundle sizes measure Cloudflare cold-start CPU. |
| MCP construction | Shared McpServer remains rejected: SDK `assertNotServing` rejects reuse of a connected server. Server construction and registration remain per request. Module-scope **handler** is adopted per the shipped docs cited above. Its inflight set tracks per-request servers for teardown; the event bus is SDK notification infrastructure, not cross-request application state. |
| JSON encode/decode | 11 publication JSON objects are parsed per read. Compact fallback avoids pretty whitespace while preserving both representations; parsing and signed bytes are unchanged. |
| Geohash/prefix traversal | Nine sequential shard fetches for depths 2–10 remain; deterministic traversal and validation are retained. |
| SHA-256 and hex | Twelve immutable-object digest verifications per common read remain. Local formatting only; two canonical MID hashes still use unchanged core computeMid. |
| Cache | CPU runs disable cache. Tests prove cache hits verify bytes and reject corrupt objects, while root is fetched fresh and never cached. |
| Redundant work | Digest syntax checks, schema validation and canonicalization protect entry points and typed errors; retained. |
| Fetch parallelism | No fetches reordered or parallelized; budget/error semantics preserved. |
| Response duplication | Both compact text and structured content remain for compatibility. |

### Response sizes and em dash

| Tool | Text chars before → after | Structured chars (unchanged) | Whole tool result chars before → after | Rough whole-result tokens before → after |
| --- | ---: | ---: | ---: | ---: |
| read_place | 2227 → 1962 | 1962 | 4418 → 4108 | 1105 → 1027 |
| get_record | 1180 → 1082 | 1082 | 2411 → 2290 | 603 → 573 |

Rough tokens are `ceil(chars / 4)`, not tokenizer counts. Text-only estimates are
557 → 491 and 295 → 271; structured-only estimates are 491 and 271. Whole-result
sizes include JSON escaping and the tool wrapper, but exclude the JSON-RPC envelope.
The deterministic reduction is 310 chars / 78 rough tokens (read) and 121 chars /
30 rough tokens (record); neither representation is removed.

Direct inspection of the original 447-byte `records/24/2446a3b3…` fixture finds
`E2 80 94` at zero-based byte offset **89**, inside `Welcome to Null Island — `.
Core decoding preserves U+2014. The observed `â` is therefore a downstream
display/decoding artifact, not damaged signed bytes. No signed data is mutated,
re-signed or passed through a lossy correction.

### Reproduction and validation

From the repository root, with the locked dependencies already installed:

```bash
node integrations/punkto-mcp/scripts/measure-cpu.mjs /tmp/m3-paired.json
node integrations/punkto-mcp/scripts/measure-components.mjs /tmp/m3-components.json
npm test --prefix integrations/punkto-mcp
git diff --check
```

The paired harness archives and cleans up the baseline automatically; no network
or dependency installation is performed. Its optional second argument selects a
baseline Git commit (default `5c23c1a`). The component command reproduces batch CPU,
not invocation CPU. Performance measurements are not test assertions.

Round 2 `npm test` exited 0: **40 tests, 40 pass**, 0 failed/cancelled/skipped/todo
(3555.558811 ms). All 32 original and six round-1 tests remain unmodified.
New coverage verifies byte-identical results across initialize/call cycles, 16
concurrent mixed requests with differing arguments and record identities,
initialization and a tool call after the burst, and exact 404/405 boundaries.
Existing tests retain digest, cache, canonical MID, signed em dash, origin,
GET-only, fallback, budget, truncation and trust-label checks.

No browser or live Cloudflare verification was performed. Residual risks include
process-wide/JIT/GC noise, fixed sampling order, legacy-compatible RPC coverage
rather than every client dialect, and unmeasured Cloudflare cold-start/cache/network
CPU. Per-request server construction remains. The target <8 ms Cloudflare budget
is not established; local handler savings were not reproduced in this run.

## Deploy (manual GitHub Actions)

1. In Cloudflare, the Founder must manually create the placeholder Worker
   **`punkto-mcp`** first. A per-Worker Editor token cannot create a Worker.
2. Create an account API token with the granular role selection:
   **Account API Tokens → Specified Workers → `punkto-mcp` → Editor**.
   This must NOT be a Product-wide Admin / account-wide token. It grants no DNS
   route or custom-domain access. See Cloudflare's
   [Worker authorization](https://developers.cloudflare.com/workers/authorization/workers/)
   and [GitHub Actions deployment](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/)
   documentation.
3. In GitHub **Settings → Environments**, create **`cloudflare-mcp-free`**.
   For approval and branch protection, configure required reviewers and deployment
   branch rules allowing only the default branch; these optional environment
   protections must be configured by the Founder in repository settings.
   Under **Settings → Secrets and variables → Actions**, add the repository
   secret **`CLOUDFLARE_API_TOKEN`**. Add **`CLOUDFLARE_ACCOUNT_ID`** as a repository
   Actions variable, or as a secret of the same name. The variable takes precedence
   if both are set. Keep the token only in GitHub Actions secrets, never in git,
   logs, comments, or chat.

Once this workflow is available on the repository's default branch, select
**Actions → Punkto MCP deploy (manual) → Run workflow → choose the default
branch → Run**. The deploy job only runs from the default branch; runs from any
other ref are skipped. There are no automatic deployments. Concurrent manual
deploys cannot overlap.

The workflow runs **`npm ci` → `npm test` → dry-run bundling → deploy**, using
Node 22 and local Wrangler 4.157.0 pinned by the committed lockfile through
`npx --no-install`. The dry-run needs no Cloudflare authentication. Only the final
deploy step receives credentials. The token never leaves GitHub Actions except
for authentication to Cloudflare; it is not printed or placed in step summaries.
The existing `workers_dev` configuration stays unchanged, with no custom domain,
DNS route, or paid bindings.

After a successful deploy, Wrangler prints the `workers.dev` URL. Use the actual
subdomain from that output; the MCP endpoint is
`https://punkto-mcp.<subdomain>.workers.dev/mcp`. Verify it with this POST request,
replacing `<subdomain>` with that actual subdomain:

```bash
curl --fail-with-body 'https://punkto-mcp.<subdomain>.workers.dev/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"deployment-check","version":"1.0.0"}}}'
```

Check for a successful MCP initialize response. A deployed Workers Free CPU
measurement is still **UNVERIFIED**: local Node CPU numbers are not Cloudflare's
10 ms metric. Deployment and initialization alone do not prove that budget is met.

Rollback is not automated through this workflow. An operator with their own
Cloudflare access can run `npx --no-install wrangler versions list`, then
`npx --no-install wrangler rollback` from this directory, or redeploy a reviewed
previous revision. The GitHub Actions token must not be copied out for local use.
This change only prepares the pipeline; no deployment has been attempted.

## Pre-deploy and post-deploy checks (reproducible)

These are operator instructions, not actions performed by this documentation
change. Audit measurements below come from EVIDENCE.md, dated 2026-11-10 UTC.

From the repository root:

```bash
cd integrations/punkto-mcp && npm ci && npm test
```

PASS: 86 tests, 86 pass, 0 fail, 0 skipped (Node 22 in CI). All upstream responses
are offline mocks; the suite never touches the network. Run subsequent commands
from `integrations/punkto-mcp`.

```bash
npx --no-install wrangler deploy --dry-run
```

PASS: exit 0 and a `Total Upload` line. This is a local bundle check only,
**not** Cloudflare runtime acceptance.

```bash
node scripts/live-m6-check.mjs
```

PASS: `live-verified places: 5/5` (audit output also reported `upstream fetches: 63`).
This is an online catalog maintenance command, never a test step.

Post-deploy smoke, read-only and low volume, against the canonical apex URL:

```bash
rpc() {
  curl --silent --show-error --include 'https://punkto.xyz/mcp' \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' --data "$1"
}
rpc '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"quickstart","version":"1.0.0"}}}'
rpc '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
rpc '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"read_place","arguments":{"h":"s00000000000_0"}}}'
rpc '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"discover_places","arguments":{}}}'
rpc '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_record","arguments":{"sha256":"21cbb254c6902c1ae3c5ccb573f34e476cafdc6ac8f9205ea366ba728cd9379a"}}}'
```

PASS: each returns HTTP 200 and `event: message`; tools/list names exactly
`read_place`, `get_record`, `discover_places`; read/get results have
`trust: "unverified_published_text"`. Discovery returns a catalog caveat instead
of a `trust` field.

Negative checks (reuse `rpc` above); each comment states PASS:

```bash
# HTTP 400, JSON-RPC -32700
rpc '{not json'
# HTTP 200, JSON-RPC -32601
rpc '{"jsonrpc":"2.0","id":1,"method":"does/not/exist"}'
# HTTP 200, JSON-RPC -32602
rpc '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"publish_record","arguments":{}}}'
# HTTP 200, isError: true, code: invalid_h
rpc '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"read_place","arguments":{"h":"not-a-place"}}}'
# HTTP 200, isError: true, code: use_sha256_not_mid
rpc '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_record","arguments":{"sha256":"punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854"}}}'
# HTTP 200, isError: true, code: upstream_missing_object
rpc '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_record","arguments":{"sha256":"0000000000000000000000000000000000000000000000000000000000000000"}}}'
# HTTP 405, {"error":"method_not_allowed"}
curl --silent --show-error --include 'https://punkto.xyz/mcp'
# HTTP 404, {"error":"not_found"} — run against the direct Worker fallback.
# The canonical apex proxies only the exact path /mcp, so other apex paths are
# served by the PWA instead of the MCP adapter.
curl --silent --show-error --include 'https://punkto-mcp.sunebech.workers.dev/not-a-route' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' --data '{}'
```

Response-size regression check for the audited discovery catalog (Python standard
library, explicit audit UA; not the blocked default `Python-urllib*` UA):

```bash
python3 - <<'PY_SIZE'
import json
import urllib.request
for arguments in ({}, {"limit": 99}):
    request = urllib.request.Request("https://punkto.xyz/mcp", method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream",
                 "User-Agent": "punkto-mcp-audit/1.0 (read-only conformance audit)"},
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "discover_places", "arguments": arguments}}).encode())
    with urllib.request.urlopen(request) as response:
        assert response.status == 200
        body = response.read()
    event = json.loads(next(line[5:].strip() for line in body.decode().splitlines()
                            if line.startswith("data:")))
    result = event["result"]
    assert not result.get("isError")
    text = result["content"][0]["text"]
    assert json.loads(text) == result["structuredContent"]
    units = len(text.encode("utf-16-le")) // 2
    assert len(body) <= 4350, len(body)
    assert units <= 2044, units
    print("PASS", arguments, "HTTP bytes:", len(body), "structured units:", units)
PY_SIZE
```

PASS: whole HTTP body ≤ 4350 bytes and compact structured content ≤ 2044 UTF-16
units for these discovery cases. Audit observations with single-digit JSON-RPC ids:
default discovery 4277 bytes / 2010 characters, clamped discovery 4349 / 2044;
default read_place 4243 / 2004, non-default read_place 2821 / 1312, get_record
without raw 2257 / 1040.
Whole-response byte totals include the JSON-RPC `id` echoed in the envelope, so they
shift with the id length (the same calls measured with three-digit ids are 2 bytes
larger). The structured-content character counts do not depend on the id.
These are snapshot-specific observations and regression bounds, not universal
response-size guarantees; re-baseline deliberately when publication/catalog data
changes. Raw inclusion is outside these measured whole-body bounds.

Rollback, using the operator's own Cloudflare access:

```bash
npx --no-install wrangler versions list
npx --no-install wrangler rollback
```

PASS: the reviewed prior version is restored and passes the smoke checks. An
alternative is to redeploy a previously reviewed revision. Never copy the GitHub
Actions deploy token out for local use. No automatic rollback exists.

Recommend structured runtime logging of request id, tool name, outcome code,
duration, upstream origin, fetch count and response byte size. Do **not** log raw
published text, record bytes, base64 payloads, fetched-record `sha256`/`record_url`,
or any client-supplied argument values. Alert on `upstream_unavailable`,
`upstream_timeout`, `fetch_budget_exceeded`, any non-200 transport status (account
for the expected notification acknowledgement), and rising publication-origin
429s. These are recommendations, not claims that logging or alerts were deployed;
the audit had no Cloudflare log/dashboard access.

## What this does not prove

No global coverage, persistence guarantee, presence proof, payload truth, or trust
authority. Hash verification establishes byte integrity against references, not
actor authenticity or the truth of a mutable publication root.

Not implemented: publish, submit, login, LLM, KV/D1/DO, custom domain, production
hostname, session state, or signature verification.
