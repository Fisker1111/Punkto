# M9 release readiness

Audit: **2026-11-10 UTC**, existing M7 deployment. Measured values come exclusively
from the supplied `EVIDENCE.md` audit; date citations below refer to that audit,
not new live tests by this documentation change. PASS is scoped to the stated
check, not blanket release approval. Historical README measurements remain historical.

| Item | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Endpoint reachability | PASS | 2026-11-10 audit: initialize HTTP 200 on both endpoints | Canonical `https://punkto.xyz/mcp` is node1's Caddy exact-path proxy to `https://punkto-mcp.sunebech.workers.dev/mcp`; both serve the same adapter. |
| MCP handshake | PASS | 2026-11-10 audit: initialize 200, notifications/initialized 202 with empty body, tools/list 200 | SSE RPC response; stateless, no Mcp-Session-Id. Requested protocol 2025-06-18 retained; Python SDK negotiated 2025-11-25. |
| Tool count, names and annotations | PASS | [src/tools.js](src/tools.js); 2026-11-10 audit | Exactly three: read_place, get_record, discover_places; readOnlyHint true, destructiveHint false, idempotentHint true, openWorldHint true. No write/publish/submit. |
| Deterministic schemas | PASS | 2026-11-10 audit: byte-identical repeated tools/list schemas | Identical across endpoints and SDK stacks. |
| Live tool coverage | PASS | 2026-11-10 audit: Null Island s00000000000_0 returned 2 records; u3butz7k9q_23 returned 3; discovery returned 5 places | All three tools exercised on both endpoints. get_record with and without include_raw; raw 354-byte record produced 472 base64 characters and re-hashed to the requested digest in both SDKs. |
| Independent client conformance | PASS | 2026-11-10 audit: Python MCP SDK mcp 2.0.0 / Python 3.11; Node @modelcontextprotocol/sdk 1.32.2 / Node v26.9.0; raw Python 3 stdlib urllib JSON-RPC/SSE harness | Both SDKs completed sessions on both endpoints; identical lists, results and typed errors. Raw harness changed its initially blocked default UA. |
| Negative / hostile matrix | PASS | 2026-11-10 audit: malformed JSON 400/-32700; invalid RPC 400/-32600; unknown method 200/-32601; unknown/write tool 200/-32602; wrong Content-Type 415; missing Accept pair 406; non-POST 405 | Invalid h/sha/limit, absent record and SSRF-style URL in `h` and in `sha256` rejected (`invalid_h`, `invalid_sha256`); SDK schema failures may lack adapter codes. |
| Source error inventory | PASS | [src/tools.js](src/tools.js), [src/publication.js](src/publication.js), [src/upstream.js](src/upstream.js) | All spec-listed codes exist. Source additionally has internal_error (unexpected-exception response) and unsupported_origin (internal configuration guard, unreachable through public tool arguments). README follows source, as required. |
| Read-only routing and bounded upstream | PASS | [src/index.js](src/index.js), [src/upstream.js](src/upstream.js); 2026-11-10 audit | Worker route boundary: POST /mcp only, other paths 404 on the Worker. The canonical apex proxies only the exact path /mcp, so non-`/mcp` apex paths are served by the PWA, not the adapter. Upstream GET only under /publication/ on fixed punkto.xyz then test2.punkto.xyz allowlist; redirects refused; 1 MiB body cap; 20 fetches per attempt, at most 2 attempts. |
| Prompt injection handling | PASS | [src/records.js](src/records.js) and 2026-11-10 audit trust labels | unverified_published_text, explicit untrusted-data delimiter, at most 2000 UTF-16 code units. Labels instruct consumers; they cannot guarantee downstream model behaviour. |
| Signature-verification honesty | PASS | [src/records.js](src/records.js), [src/upstream.js](src/upstream.js) | SHA-256 against references only; no Ed25519 verification, actor proof, persistence guarantee or trust authority. Verify independently with Punkti-compatible code. |
| Immutable digest vs MID | PASS | 2026-11-10 audit: MID input returns use_sha256_not_mid; raw record re-hash succeeded | Immutable byte SHA-256, canonical MID and Ed25519 signature are distinct checks. |
| Trusted-root boundary | PASS | [src/publication.js](src/publication.js); 2026-11-10 audit: root_verification unverified-by-digest | Mutable root is not digest-verified; snapshot is one node's published view, not completeness or persistence. |
| Catalog staleness / updates | OPEN | [src/catalog.json](src/catalog.json); 2026-11-10 audit: node scripts/live-m6-check.mjs → live-verified places: 5/5; upstream fetches: 63 | Manual curation, no automatic refresh; snapshot seq 14, checked_at 2026-11-07T13:05:00Z. Re-check after node parity rollout. |
| Duplicate response overhead | OPEN | [src/tools.js](src/tools.js); 2026-11-10 audit: discovery 2010 structured characters / 4277 HTTP bytes; clamped 2044 / 4349 | JSON text plus structuredContent retained for compatibility; token overhead exists, tokenizer count UNVERIFIED. Whole-response byte totals include the JSON-RPC `id` and shift with its length; structured-content character counts are id-independent. |
| Apex latency / response bytes | PASS | 2026-11-10 audit: 10 calls per method, 4-way concurrency | p50/p95 ms; HTTP bytes (three-digit ids): read_place default 140.14/287.08; 4245. Non-default 133.09/257.39; 2823. discover_places 90.42/251.07; 4279. get_record 92.51/205.24; 2259. Wall time, not CPU or SLA. |
| Direct Worker latency / response bytes | PASS | 2026-11-10 audit: 10 calls per method, 4-way concurrency; 0 errors across all 80 timed calls | p50/p95 ms; HTTP bytes (three-digit ids): read_place default 211.12/293.38; 4245. Non-default 152.56/197.90; 2823. discover_places 83.43/186.02; 4279. get_record 100.95/337.03; 2259. Largest observed body 4350 bytes, structured content 2044 characters. |
| Cloudflare CPU budget | UNVERIFIED | 2026-11-10 audit: no account or analytics access | Local Node CPU and live network latency do not establish the Free 10 ms metric; no CPU or cost claim. |
| Cloudflare WAF 1010 | OPEN | 2026-11-10 audit: case-sensitive Python-urllib* prefix → HTTP 403, browser_signature_banned, retryable false, owner_action_required true | Includes Python-urllib3; lowercase python-urllib and python-requests/2.32.3 returned 200. Both MCP endpoints affected; Worker root also blocked. Apex /, /ai and /publication/root.json returned 200 for Python-urllib/3.11. Tested SDK stacks succeeded; default urllib clients can fail. |
| Browser Origin validation | OPEN | 2026-11-10 audit: OPTIONS 405; absent Origin, Worker origin and localhost:3000 → 200; apex/www/evil/null Origin → 403 | No preflight allow headers; plain POST with Origin has access-control-allow-origin: *, but origin validation still rejects non-allowlisted origins. Retain DNS-rebinding protection; native/CLI clients without Origin unaffected. |
| TLS certificates | PASS | 2026-11-10 audit: curl ssl_verify_result 0 on both; TLS 1.3, HTTP/2 | punkto.xyz: Let's Encrypt YE2, 2026-09-12–2026-12-11. Worker hostname: Let's Encrypt YE1, 2026-11-05–2027-02-03. Valid at audit time. |
| Degraded-node fallback | UNVERIFIED | [src/upstream.js](src/upstream.js), [test/](test/); 2026-11-10 audit: all live reads used primary, attempts 1 | Offline mocks cover fallback on transport failure, timeout or 5xx only; no production node degraded. No fallback for 429, missing objects, redirects or digest failures. Live degraded-node behaviour unmeasured. |
| Publication snapshot parity | OPEN | 2026-11-10 audit: primary seq 14 / head c77ba862be21e00d37bdc62f35bac7359d09698d19cd4ef8b2ce5be33ff0a9e5; fallback seq 16 / head 392bab1513f4708c6de96a193b418c9cce59e834dc5748e0d066de9a657c71e0 | Catalog metadata describes primary snapshot; fallback restarts the read and may return a different snapshot. |
| Local tests / CI definition | PASS | Audit npm test: 86 tests, 86 pass, 0 fail, 0 cancelled, 0 skipped, 0 todo; [.github/workflows/punkto-mcp.yml](../../.github/workflows/punkto-mcp.yml) | Offline mocks only, no network; PR workflow uses Node 22, npm ci then npm test. Exact-change GitHub check status UNVERIFIED; local pass is not a remote CI result. |
| Known / acceptable limitations | OPEN | 2026-11-10 audit; [README.md](README.md) | Native-client support, small staleable catalog, divergent snapshots, duplicated results, Workers Free hobby tier without business SLA, unverified CPU. Founder acceptance remains separate. |
| Deployment and rollback | PASS | 2026-11-10 audit: deployed M7 Worker version b2a93a7f-c4d6-4822-a7a9-8cf74aff6012; [.github/workflows/punkto-mcp-deploy.yml](../../.github/workflows/punkto-mcp-deploy.yml) | Nothing deployed by this change. Manual default-branch workflow requires Founder approval. Operator: npx --no-install wrangler versions list then npx --no-install wrangler rollback, or redeploy reviewed prior revision; smoke-check afterward. No automatic rollback; never export the Actions token for local use. |

## Open items for Founder approval

- **Cloudflare WAF 1010 user-agent ban (P1 for public listing).** Narrow the
  case-sensitive `Python-urllib*` ban to the specific abusive UA instead of the
  entire prefix; do not disable protections. The audit does not identify the
  abusive UA, so the owner must determine it. This needs Founder approval and
  Cloudflare account access unavailable to this change. No change made in this PR.
- **Browser-origin support (P2).** OPTIONS returns 405; non-allowlisted cross-origin
  clients are rejected. Desktop/CLI clients without Origin are unaffected. Keep
  DNS-rebinding protection and document native-client-only support; revisit if
  browser clients become a goal. No change made in this PR.
- **Publication-node snapshot divergence (P1).** Catalog metadata can describe a
  different snapshot from fallback reads. State this caveat in client-facing docs
  (included in the README) and re-check the catalog after node parity rollout.
  No code, catalog or node-parity change made in this PR.

## Scope of this change

Documentation only: no runtime code changed, no deploy performed, no
Cloudflare/Caddy/DNS change. The three operational open items above deliberately
require separate Founder-approved work. No commit or push performed.
