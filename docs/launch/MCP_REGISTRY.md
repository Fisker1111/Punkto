# Punkto MCP — official MCP Registry metadata and manual registration

## Status

Review-only draft for CEO-OS #62. Nothing has been published, no registry account was used, and no credentials were created. Publication requires explicit founder approval and the PWA/MCP M9 customer-facing readiness gate. Checked on 2026-11-11: CEO-OS #61 remains OPEN, with `status:review` (previously `status:in-progress` on 2026-11-10), so M9 readiness is NOT MET. CEO-OS #58 is OPEN with `status:review`; the www DNS cutover is NO-GO. `www.punkto.xyz` does not resolve and must never be used as a landing destination.

The factual baseline comes from the task specification: endpoint and registry checks on 2026-11-10, issue and Glama checks on 2026-11-11. No network checks were repeated while writing these files. The official registry searches for Punkto and Punkti returned zero results. Adding repository metadata does not publish it: `https://punkto.xyz/server.json` returned HTTP 404 at the baseline check.

## The published draft

The heading names the proposed publication payload, not an already published listing. The following is byte-identical to the root [server.json](../../server.json).

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "xyz.punkto/punkto-mcp",
  "title": "Punkti read-only MCP endpoint (by Punkto)",
  "description": "Read-only MCP access to signed Punkti spatial records published at punkto.xyz.",
  "version": "0.1.0",
  "repository": {
    "url": "https://github.com/Fisker1111/Punkto",
    "source": "github"
  },
  "websiteUrl": "https://punkto.xyz/",
  "icons": [
    {
      "src": "https://punkto.xyz/logo-192.png",
      "sizes": [
        "192x192"
      ],
      "mimeType": "image/png"
    }
  ],
  "remotes": [
    {
      "type": "streamable-http",
      "url": "https://punkto.xyz/mcp"
    }
  ],
  "_meta": {
    "io.modelcontextprotocol.registry/publisher-provided": {
      "com.punkto": {
        "service": "punkto",
        "protocol": "punkti",
        "readOnly": true,
        "auth": "none"
      }
    }
  }
}
```

| Field | Meaning |
|---|---|
| `$schema` | Pins the supplied official registry schema version. |
| `name` | Domain namespace `xyz.punkto` plus server name; maximum 200 characters and exactly one `/`. |
| `title` | Human-readable catalogue title; maximum 100 characters. |
| `description` | Read-only spatial-record description; maximum 100 characters. |
| `version` | `0.1.0` matches the live `serverInfo.version`. |
| `repository.url` | The Punkto GitHub repository. |
| `repository.source` | Identifies GitHub as the repository source. |
| `websiteUrl` | The working apex PWA URL. |
| `icons[].src` | The logo URL verified HTTP 200 on 2026-11-10. |
| `icons[].sizes` | Array of size strings, `["192x192"]`; a bare string fails schema validation. |
| `icons[].mimeType` | Declares the PNG icon media type. |
| `remotes[].type` | Only `streamable-http`; no deprecated SSE transport or `http` remote entry. |
| `remotes[].url` | The POST-only read-only MCP endpoint. |
| `_meta` | Contains only the registry-supported `io.modelcontextprotocol.registry/publisher-provided` key; other top-level metadata keys are silently dropped. |
| `com.punkto.service` | Identifies Punkto as the service. |
| `com.punkto.protocol` | Identifies Punkti as the protocol. |
| `com.punkto.readOnly` | Declares the adapter read-only. |
| `com.punkto.auth` | Declares no endpoint authentication; publisher authentication is separate. |
| No `packages` | This is a remote-only server, a valid registry shape without installable packages. |

The supplied shape was previously validated against `https://registry.modelcontextprotocol.io` with output `✅ server.json is valid`. This is prior evidence, not a validation run in this writing task.

## Namespace choice: domain vs GitHub

| Option | Namespace | Proof required | Effort | Notes |
|---|---|---|---|---|
| Domain, recommended | `xyz.punkto/punkto-mcp` | Apex DNS TXT `MCPv1` record or `https://punkto.xyz/.well-known/mcp-registry-auth` | Founder manages domain proof and an Ed25519 keypair | Reverse DNS of `punkto.xyz`; the registry grants the namespace to the domain controller, and the name travels into importing directories. |
| GitHub | `io.github.fisker1111/punkto-mcp` | OAuth device-flow login | Simplest execution route | Tied to the GitHub account rather than the service domain. |

Use the domain namespace as primary. The founder may switch the `name` line in `server.json` to the GitHub form before publishing; then validate and use that exact name in all searches and submissions. `Fisker1111` is a GitHub **User**, not an Organisation, so the org-namespace route and its org-owner proof do not apply.

## Manual registration steps

These commands are future founder instructions, not authorization to run them now. The readiness gate and explicit founder approval apply before publication. Steps 3–4 are founder-executed only, must not be automated, and Hermes must not authenticate on the founder's behalf. Angle-bracket values are placeholders, never credentials supplied by this document.

1. Install the official release binary:

   ```bash
   curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher && sudo mv mcp-publisher /usr/local/bin/
   ```

   Alternative:

   ```bash
   brew install mcp-publisher
   ```

   Verify installation:

   ```bash
   mcp-publisher --help
   ```

   Expected commands: `init`, `login`, `logout`, `publish`, `status`, `validate`.

2. From the repository root, validate only; this does not publish:

   ```bash
   mcp-publisher validate server.json
   ```

   Expected output:

   ```text
   ✅ server.json is valid
   ```

3. Choose one namespace proof route, performed by the founder only:

   - DNS: generate an Ed25519 keypair using the publisher's supported procedure, then publish this TXT record **at the apex** `punkto.xyz`, not `_mcp-auth.punkto.xyz`:

     ```text
     punkto.xyz. IN TXT "v=MCPv1; k=ed25519; p=<base64 public key>"
     ```

     A selector record in the wrong place fails with a generic signature error. After installing the correct proof:

     ```bash
     mcp-publisher login dns --domain punkto.xyz --private-key "<key>"
     ```

   - HTTP: generate an Ed25519 keypair and host the required proof at `https://punkto.xyz/.well-known/mcp-registry-auth`, then:

     ```bash
     mcp-publisher login http --domain punkto.xyz --private-key "<key>"
     ```

   - GitHub: edit the single `name` line as above, revalidate, and complete the founder's device flow:

     ```bash
     mcp-publisher login github
     ```

   Exact key-generation command, private-key encoding and HTTP proof-file contents are not supplied by the verified facts; the operator must confirm them before executing a domain route. Never commit or share a private key.

4. Only after founder approval and readiness, the founder publishes the reviewed file:

   ```bash
   mcp-publisher publish server.json
   ```

5. Search for the exact published name:

   ```bash
   curl "https://registry.modelcontextprotocol.io/v0/servers?search=xyz.punkto%2Fpunkto-mcp&version=latest"
   ```

   If the GitHub name was selected, use:

   ```bash
   curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.fisker1111%2Fpunkto-mcp&version=latest"
   ```

   Inspect the returned `server.name` for an exact match, not merely a search hit. The registry is in preview: "Breaking changes or data resets may occur before general availability."

## Verification

Future operator checks, not executed for this draft:

```bash
mcp-publisher validate server.json
curl "https://registry.modelcontextprotocol.io/v0/servers?search=xyz.punkto%2Fpunkto-mcp&version=latest"
curl -i -X POST https://punkto.xyz/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"founder-readiness-check","version":"1.0.0"}}}'
curl -i -X POST https://punkto.xyz/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

For the GitHub route substitute its URL-encoded name from step 5. No match returns `{"servers":[],"metadata":{"count":0}}`; a match has a `servers` array containing a `server` object and registry-managed `_meta`. Confirm the name, version and remote URL. The version-less listing form is `https://registry.modelcontextprotocol.io/v0/servers?limit=1`; `/v0.1/servers?search=<name>` also responded in the baseline checks.

Expected live endpoint result: POST HTTP 200, Streamable HTTP with SSE-framed JSON-RPC, protocol version `2025-06-18`, `serverInfo` equal to `{"name":"punkto-mcp","version":"0.1.0"}`, and capability `tools.listChanged`. `tools/list` must expose exactly `read_place`, `get_record`, `discover_places`, all read-only. GET to `/mcp` returns HTTP 405 as expected for this POST-only endpoint; it is not a health failure. SSE framing does not mean a separate legacy SSE remote should be added.

From a fresh MCP client session, configure the remote `https://punkto.xyz/mcp` with Streamable HTTP and no account, initialize, then list tools. Record the client/version and actual result as operator QA. A fresh-client pass remains an operator action to confirm, not a result claimed by this draft. Plain HTTP GET through [the AI entrance](https://punkto.xyz/ai) remains the universal fallback and is never redirected or changed.

## What the registry does and does not prove

The registry proves namespace ownership through domain or GitHub authentication; it does **not** prove control of the remote URL. Namespace allocation is proof-of-ownership-gated, not first-come-first-served. A listing provides machine access through a catalogue; it does not mean any model will notice, prefer or use the server. A catalogue entry is never evidence of demand or a customer. The registry is in preview, with possible breaking changes or data resets.

## Downstream directories

Directory facts were checked on 2026-11-10; the Glama baseline was checked on 2026-11-11.

| Directory | How to get in | Cost | Review | Note |
|---|---|---|---|---|
| Official MCP Registry | Founder authenticates namespace and publishes `server.json` | $0 planned; price not independently specified in verified facts, operator to confirm | Timing unverified | Primary source for importing directories; no Punkto/Punkti results at baseline. |
| Glama, registry import | Publish to official registry; Glama ingests and re-publishes it | Free | Import timing unverified | No Punkto server page at baseline. |
| Glama, remote connector | Submit remote HTTPS Streamable HTTP connector; claim domain with `/.well-known/glama.json` | Free; optional free boosts; paid boost approximately $49/month, out of budget | Health-checked; timing unverified | Separate from an installable server; no Punkto connector at baseline. |
| mcpservers.org | Submit form; fill “Official MCP Registry Name (optional)” and “This server supports remote connections” | Free $0; premium $39 one-time | Free review within 2 weeks; premium within 24 hours | Premium includes Official badge and dofollow link; no demand guarantee. |
| MCP Market | Submit at `https://mcpmarket.com/submit` with GitHub repository URL | Free; expedited $29 one-time | Free queue averages 4–6 weeks; expedited listing within 24 hours | Paid tier includes Official badge. |
| PulseMCP | Submission page directs publishers to official registry; no new submissions accepted | Not applicable; future terms unverified | Closed to submissions | Treat as possible future automatic pickup, not an established current registry importer. |
| Smithery | Plain directory remains; submission process to be confirmed | Unverified | Unverified | Hosted MCP proxy shut down 2026-10-31; do not plan on proxy hosting. |
| awesome-mcp-servers / awesome-remote-mcp-servers | Founder opens a curated-list PR | $0 planned; any fee to be confirmed | Maintainer review, timing unverified | Remote list requires live Glama connector badge, a star on the repo and CI passing a live `initialize` handshake. |

The Glama claim file is hosted at `https://punkto.xyz/.well-known/glama.json`, outside this task's file scope. Its required shape is:

```json
{"$schema":"https://glama.ai/mcp/schemas/connector.json","maintainers":[{"email":"…"}]}
```

The founder supplies an actual maintainer email only when approving that separate action. Recommended order: official registry first (planned free route, with fee confirmation before action), because Glama imports and re-publishes it; then claim/verify the Glama remote connector and health check; then the curated GitHub list PR. Paid-expedite options come last, only if the founder decides a 24-hour listing is worth the money; none is purchased here.

## Out of scope

- No account was created and no credential was stored.
- No listing was submitted and no directory was contacted.
- No paid listing was bought.
- No promotional copy was published anywhere.
- No product code, deployment, DNS record or well-known proof file was changed.

**Notes and open items**

- The exact supplied JSON takes precedence over the deliverable's prose character count; lengths are measured by the requested local self-check rather than copied from that prose.
- “The published draft” is retained as the required heading but explicitly means an unpublished payload.
- Domain namespace is primary; the single-line GitHub alternative remains founder-selectable.
- Verified facts do not provide key-generation commands, key encoding or HTTP proof contents; these remain operator checks rather than invented executable steps.
- Registry and curated-PR routes are planned at $0 per the deliverable; their fees and unspecified directory review timings/processes remain unverified. The verified free Glama and mcpservers.org routes are identified separately.
- PulseMCP is a possible future pickup, not a confirmed current importer; remote-list badge/star/CI requirements are attributed specifically to the remote list.
- Publication and fresh-client checks await readiness and founder action; prior verification evidence is not represented as a new run.
