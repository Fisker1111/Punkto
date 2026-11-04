# Punkto MCP M1

MCP is an **optional convenience entrance** to one node's published Punkti view.
Plain HTTP through `/ai` remains the universal fallback; it is never redirected or changed.
This read-only, stateless Worker serves only `POST /mcp` using Agents' default MCP
host/CORS handling. It fetches only publication objects from `https://punkto.xyz`,
falling back to `https://test2.punkto.xyz` only after transport failures (including
timeouts) or 5xx. Missing objects, redirects and digest failures do not trigger fallback.

Connection URL shape: `https://<worker>.<subdomain>.workers.dev/mcp`.

**deployment: not-done — Cloudflare account access required**

## Tools

- `read_place({ h?, limit? })`: canonical `xy_z`, default `s00000000000_0`;
  limit defaults to 4, minimum 1, values above 8 clamp to 8 with a result note.
  Exact full-address matching, verified manifest/shard/record bytes, root explicitly
  unverified by digest. Missing exact addresses return `not_found_in_publication`.
- `get_record({ sha256, include_raw? })`: exactly 64 lowercase hex characters;
  MID addresses are rejected. Raw base64 defaults off and is available only up to
  32768 bytes. Each decoded MID uses the `punkti/0.6:<digest>` address form.

Tool results contain matching pretty JSON text and `structuredContent`. Published
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
context; **all upstream responses are offline mocks**. Fixtures are local static
publication objects with inert zero-filled signature/public-key framing, not
signature-valid records or credentials. No local workerd test fallback is needed.
The final test prints `process.cpuUsage()` measurements around each tool invocation,
fetch counts, pretty-JSON character counts and rough tokens (`chars/4`). These include
local mock/Node runtime overhead, exclude network waiting, and are **not Cloudflare
Free's 10 ms measurement**. Live Workers metrics require account access.

One warm local Node 22.23.4 sample (`npm ci && npm test`, 30 passed / 0 failed):

| Tool | CPU ms | Fetches | JSON chars | Approx. tokens |
| --- | ---: | ---: | ---: | ---: |
| `read_place` (2 records) | 4.571 | 13 | 2024 | 506 |
| `get_record` | 0.946 | 1 | 945 | 237 |

If a client retains the full returned text, all those tokens remain in model
context until it drops/summarizes them. If it exposes both MCP representations,
the serialized envelope is 4008 / 1937 characters (~1002 / 485 tokens), before
outer JSON-RPC overhead. Client behavior determines actual context use. These
single samples are not performance guarantees; local CPU varies between runs.
The tests also measured 19 fetches for eight entries, 38 for a late traversal
fallback, and 40 for a two-attempt client stress case.

For deployment, the operator runs `npx wrangler login` with their own Cloudflare
account (credentials stay outside git), then `npx wrangler deploy` here to obtain a
`workers.dev` URL. Rollback: `npx wrangler versions list`, then `npx wrangler rollback`,
or redeploy the previous revision. No deployment has been attempted.

## What this does not prove

No global coverage, persistence guarantee, presence proof, payload truth, or trust
authority. Hash verification establishes byte integrity against references, not
actor authenticity or the truth of a mutable publication root.

Not implemented: publish, submit, login, LLM, KV/D1/DO, custom domain, production
hostname, session state, or signature verification.
