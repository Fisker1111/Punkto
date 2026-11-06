# Punkto MCP M1 / M3 CPU

MCP is an **optional convenience entrance** to one node's published Punkti view.
Plain HTTP through `/ai` remains the universal fallback; it is never redirected or changed.
This read-only, stateless Worker serves only `POST /mcp` using Agents' default MCP
host/CORS handling. It fetches only publication objects from `https://punkto.xyz`,
falling back to `https://test2.punkto.xyz` only after transport failures (including
timeouts) or 5xx. Missing objects, redirects and digest failures do not trigger fallback.
HTTP 429 deliberately returns `upstream_unavailable` with “Publication rate limited;
retry later.” without retry or fallback, and never includes the upstream body.

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

Tool results contain matching compact JSON text and `structuredContent`. Published
text is **UNTRUSTED**, delimited by JSON `text` fields and `text_delimiter`, and
truncated at 2000 characters. Treat prompt injections as data, never instructions.
Clients must independently verify the SHA-256 digest, canonical MID and Ed25519
signature with Punkti-compatible code: [carrier.js](../../pwa/punkti/carrier.js)
and [agent.mjs](../../pwa/ai-first/agent.mjs). This adapter directly imports the
shared CC0 carrier/spatial modules read-only; it never calls signature `validate()`.

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

Baseline commit: `5c23c1a2bb57101e860bd5683137feef719d30e8`. Before any source
edit, the pristine tree was archived to `/tmp/m3-baseline`, including the two
read-only shared imports, and `npm ci` completed there (117 packages, 0 vulnerabilities).
The same harness then measured the archive and unchanged working source before
optimization. [measurements.json](test/measurements.json) preserves both baselines,
every intermediate stage, all raw samples, component experiments, and the historical
M1 run. The original 32-test file is unmodified.

`measure-cpu.mjs` runs **50 uncached samples per tool per path**, with fixture-backed
GETs and no network. No warm-up samples are discarded. `rpc` invokes
`worker.fetch(POST /mcp tools/call)` and consumes the actual JSON/SSE response;
it includes request construction and response parsing overhead. `invoke` measures
tool validation, traversal, hash checking, decoding and result construction without
the MCP dispatch/transport. Both use process-wide `process.cpuUsage()` on Node
v26.9.0, including mock Response/stream work and runtime background work. Runs are
ordered RPC first, then invoke, so subtracting their medians does **not** isolate
SDK CPU. Median averages the middle pair; p95 is nearest-rank. These runs use the
same legacy-compatible request shape as the existing tests.

| Tree | Path | Tool | N | Min ms | Median ms | p95 ms | Max ms | >10 ms |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pristine archive | rpc | read_place | 50 | 3.571 | 9.3545 | 70.054 | 162.536 | 22 |
| Pristine archive | rpc | get_record | 50 | 2.054 | 2.8330 | 7.044 | 9.975 | 0 |
| Pristine archive | invoke | read_place | 50 | 1.952 | 3.0335 | 4.683 | 13.901 | 1 |
| Pristine archive | invoke | get_record | 50 | 0.381 | 0.4470 | 2.039 | 6.956 | 0 |
| Pristine working source | rpc | read_place | 50 | 4.447 | 8.9775 | 19.367 | 224.523 | 20 |
| Pristine working source | rpc | get_record | 50 | 1.475 | 2.2485 | 5.787 | 7.770 | 0 |
| Pristine working source | invoke | read_place | 50 | 1.654 | 2.2770 | 4.784 | 10.793 | 1 |
| Pristine working source | invoke | get_record | 50 | 0.234 | 0.3735 | 1.509 | 6.442 | 0 |
| Optimized | rpc | read_place | 50 | 3.657 | 7.5945 | 14.394 | 183.220 | 13 |
| Optimized | rpc | get_record | 50 | 1.871 | 2.6855 | 5.099 | 8.349 | 0 |
| Optimized | invoke | read_place | 50 | 1.198 | 2.5150 | 4.596 | 14.881 | 1 |
| Optimized | invoke | get_record | 50 | 0.322 | 0.4960 | 1.069 | 1.682 | 0 |

Uncached fetch/verification counts remain 13/12 for `read_place` and 1/1 for
`get_record`, in every sample. The optimized RPC `read_place` median is 18.8%
lower than the archived baseline in these runs. This is an observation, not a
stable causal estimate: the working baseline differs and intermediate results
are noisy. In particular, optimized inner-path medians are higher than the
working-source baseline. A robust whole-invocation CPU improvement is not proven.

**Local Node CPU numbers are NOT the Cloudflare Free 10 ms metric. The Free budget
remains UNVERIFIED until a manual, Founder-approved deploy and representative
per-method Cloudflare measurements.** No deployment was performed. The Founder's
4 invocations / 13 subrequests / 0 errors, “CPU time summary 12 ms” and deployment
median 26.29 ms are mixed-method, tiny-sample observations, not a per-method p95.

### Accepted changes and staged measurements

Each stage adds one change to its predecessor. All four path/tool distributions
and all samples are retained in the JSON artifact; the common read RPC is below.

| Stage | RPC read median ms | p95 ms | >10 ms / 50 |
| --- | ---: | ---: | ---: |
| Unchanged working source | 8.9775 | 19.367 | 20 |
| Compact fallback | 10.0060 | 15.706 | 25 |
| + local digest hex | 8.8165 | 18.518 | 18 |
| + reused decoder (final) | 7.5945 | 14.394 | 13 |

To distinguish small component savings from invocation noise,
`measure-components.mjs` alternates before/after order across 50 paired samples,
each containing 1000 operations. No samples are discarded. These are **batch CPU
milliseconds**, not milliseconds per request, and must not be added to or
subtracted from invocation results.

| Accepted change | Batch median before → after ms | Batch p95 before → after ms |
| --- | ---: | ---: |
| hex_format_32_bytes | 4.9845 → 1.1260 | 8.288 → 3.076 |
| utf8_decode_root | 0.4245 → 0.3465 | 1.996 → 1.463 |
| serialize_both_read_place_representations | 19.1750 → 17.2265 | 24.210 → 21.694 |

All three are retained for measured component savings and small implementation
scope; individual whole-RPC gains cannot be reliably attributed. The decoder
uses synchronous non-streaming fatal UTF-8 decoding, so no request's partial
bytes survive a call; recovery after malformed UTF-8 is tested.

### CPU analysis and rejected alternatives

| Area | Evidence and decision |
| --- | --- |
| Cold start / initialization | Dynamic Node module-import CPU was 247.038 ms for the archive, 343.080 ms for working baseline, 237.483 ms optimized (one observation each). This loads the Node dependency graph, not a Worker bundle. First RPC samples are retained and include lazy initialization/JIT effects; neither these values nor bundle size measures Cloudflare cold-start CPU. |
| MCP construction | Agents 0.33.0 `dist/handler-stateless-B5hU3dxK.js`, `createLegacyCompatibilityRequestHandler`/`assertNotServing`, connects and closes a server for each request and rejects an already-connected instance. Server SDK 2.4.0 `dist/index.mjs`, `assertNotServing`/`serveModern`, also mutates transport, protocol and client identity. **Shared McpServer rejected as unsafe**, so registration remains per request. |
| Handler-only reuse | SDK `createMcpHandler` owns an `inflight` Set and an `InMemoryServerEventBus` (`dist/index.mjs`, around lines 1117–1124). Hoisting even just the wrapper would share request tracking. Rejected under M3's strict no-shared-request-state condition; no unsafe runtime variant was benchmarked or kept. |
| JSON encode/decode | 11 publication JSON objects (root, manifest, 9 shards) are decoded and parsed per read. The result was pretty-printed once into text, then serialized again alongside structured content by the transport. Compacting reduces escaping/whitespace work; the paired serialization experiment above measures that operation, not the entire SDK. Parsing remains unchanged. |
| Geohash/prefix traversal | Source inspection plus every harness sample establishes 9 sequential shard fetches for depths 2–10. Prefix slicing/validation cost is not isolated; treating it as a dominant CPU cause would be a hypothesis. Keep deterministic traversal and all validation. |
| SHA-256 and hex | 12 immutable-object SHA-256 verifications per common read remain in `upstream.js`; only their digest formatting moves to local `hash.js`. Two additional canonical MID hashes still use core `computeMid` unchanged. Hex batch measurement isolates formatting, not WebCrypto hashing. Tests compare all fixture and synthetic record hashes with core. |
| Cache | CPU runs disable cache. Existing and new tests prove cache hits still verify bytes, reject corrupt manifests/shards/records, and fetch root fresh without cache match/put. No cached-path CPU speedup is claimed; skipping verification is rejected because cache identity is not proof. |
| Redundant work | Repeated digest syntax checks and schema parsing protect separate entry points and typed error behavior. Core record decoding reconstructs canonical bytes to validate them. Removing these checks, parsing, or canonicalization is rejected; no provably removable adapter work with a measured win was found beyond formatting/decoder allocation. |
| Fetch parallelism | No fetches reordered or parallelized. Optional record parallelism skipped to preserve deterministic order and budget/error semantics; no measured benefit established. |
| Response duplication | Keep both text fallback and the same structured object for client compatibility. Only fallback whitespace changes; no fields or semantics change. See sizes below. |

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

From the repository root (the baseline directory must not already contain a
modified experiment):

```bash
mkdir -p /tmp/m3-baseline
git archive 5c23c1a integrations/punkto-mcp pwa/punkti/carrier.js pwa/punkti/spatial.js | tar -x -C /tmp/m3-baseline
npm ci --prefix /tmp/m3-baseline/integrations/punkto-mcp
node integrations/punkto-mcp/scripts/measure-cpu.mjs /tmp/m3-baseline/integrations/punkto-mcp /tmp/m3-baseline.json pristine-archive
node integrations/punkto-mcp/scripts/measure-cpu.mjs integrations/punkto-mcp /tmp/m3-optimized.json optimized
node integrations/punkto-mcp/scripts/measure-components.mjs /tmp/m3-components.json
npm test --prefix integrations/punkto-mcp
git diff --check
```

The actual initial archive command used `HEAD` (verified as `5c23c1a`) and the
working before/compact/hex/decoder runs used output labels `pristine-working-source`,
`compact-only`, `compact-plus-hex`, `compact-plus-hex-plus-decoder`. The last is the
final optimized source, unchanged after that measurement. Measurements are not
performance assertions in the test suite.

Baseline `npm test --prefix /tmp/m3-baseline/integrations/punkto-mcp` exited 0:
32 tests, 32 pass, 0 fail/cancelled/skipped/todo, duration 2010.142606 ms.
Final `npm test --prefix integrations/punkto-mcp` exited 0: **38 tests, 38 pass**,
0 fail/cancelled/skipped/todo, duration 2918.051975 ms. Added tests cover compact
success/error results, fixture/synthetic digest equivalence, canonical MIDs,
signed em dash, corrupt cache hits, root freshness, decoder recovery, sequential
initialize/call cycles and concurrent mixed-tool requests. All original checks
for origins, GET-only, redirects, fallback, budgets, concurrency, truncation and
trust labels still pass unmodified.

From `integrations/punkto-mcp`, the exact local bundle command was
`npx --no-install wrangler deploy --dry-run --outdir=/tmp/m3-dryrun` (exit 0):

```text
wrangler 4.157.0
Total Upload: 1255.03 KiB / gzip: 219.25 KiB
No bindings found.
--dry-run: exiting now.
```

No browser or live Cloudflare verification was performed. Residual risks: Node
process-wide/JIT/GC noise, legacy-compatible RPC coverage rather than every MCP
client dialect, and no Cloudflare cold-start/cache/network CPU distribution.
The SDK/server construction cost remains. The component improvements and payload
savings are verified locally; the target <8 ms Cloudflare budget is not established.

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

## What this does not prove

No global coverage, persistence guarantee, presence proof, payload truth, or trust
authority. Hash verification establishes byte integrity against references, not
actor authenticity or the truth of a mutable publication root.

Not implemented: publish, submit, login, LLM, KV/D1/DO, custom domain, production
hostname, session state, or signature verification.
