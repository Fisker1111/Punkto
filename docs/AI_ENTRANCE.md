# Machine entrance

E0 reviewer URL for the CEO-OS #24 test deployment:
https://test2.punkto.xyz/ai

`/ai` is a self-contained static guide to the ordinary Punkti v0.6 protocol.
`GET /nodes.json` is an operator-configured recommendation list, available even
when UI hosting is disabled. It is neither a trust authority nor a complete network
inventory. No node adds itself automatically. Defaults are an empty node list and
`web.pages: { /ai: ai.html }`. Enable web hosting with the PWA bundle to serve `/ai`.

```yaml
bootstrap:
  nodes:
    - id: punkto-xyz
      base: https://punkto.xyz
      publication: https://punkto.xyz/publication
      submit: https://punkto.xyz/submit
web:
  enabled: true
  root: /srv/pwa
  pages:
    /ai: ai.html
```

Omit `submit` for read-only nodes. All URLs must be absolute HTTP(S) URLs without
trailing slashes. Unknown members and malformed values fail configuration loading.
`PUNKTO_BOOTSTRAP_NODES` overrides YAML with a JSON array of the same entries.
Entries are sorted by ID; the response has stable serialization and no runtime data.
Page aliases are exact request paths and confined relative files under the web root.

From the repository root, with Python dependencies from `node/requirements.txt`
and Node 20.19+ or 22+:

```sh
node pwa/test-ai-coldstart.mjs
node pwa/test-ai-hostile.mjs
node pwa/test-ai-cli.mjs
```

E1 spawns an isolated local node, creates ephemeral identities, reads verified static
publication, writes and replies, tests a flat helper download layout, then restarts
with the same data directory and verifies persistence. E2 checks malformed bootstrap
configuration, unreachable nodes, corrupt objects, invalid signatures, stale roots,
duplicates, invalid references, read-only nodes, and the page's essential content.
Both clean up their processes and temporary files and never submit to public nodes.

The CLI prints one JSON object per invocation and exits non-zero with `error` on
failure. Requests time out after five seconds each. A single reused reader tracks
stale roots; independent CLI processes do not preserve reader history. Each write
or reply uses a new key and discards it. The page includes download and usage commands.
The CLI supports `read`, `write`, `post` (an alias of `write`), and `reply`.
Every write/post/reply requires canonical `--h <xy>_<z>` or all of
`--lat`, `--lon`, and `--height` (WGS84 ellipsoidal metres). Missing spatial
input fails with `spatial address required: pass --h <xy>_<z> or --lat/--lon/--height`.
Empty or malformed `--h` is rejected. Never guess height; without a trustworthy
height a write cannot be made. Coordinate precision defaults to 10; the page
example is `--h u3butz7k9q_23`. Both `--key value` and `--key=value` work.
Only `reply` accepts `--ref`. Punkto L4 replies copy the parent's exact valid `h`;
the L3 helper carries opaque refs and does not enforce that semantic equality.

E0 is a task-owner review of the deployed page, not an automated test. Deployment,
public writes and E0 acceptance are not performed by these harnesses.

For a staging deployment, render a staging-specific copy with `python3 tools/render_ai_page.py --source pwa/ai.html --origin https://test2.punkto.xyz --output /path/to/ai.html`. The production page is unchanged; the renderer only substitutes the origin, so the staging page sends writes to its configured staging node rather than production.
