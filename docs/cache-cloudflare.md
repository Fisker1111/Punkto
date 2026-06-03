# Cache and Cloudflare Policy

> **Status:** Documentation only — defines cache and CDN policy for Punkto nodes.
> Actual Caddy/Cloudflare configuration changes are separate future PRs.

This document defines how Punkto should use caching, CDN (including Cloudflare), and HTTP cache headers safely.

## Core Principles

1. **Cache static/public assets.** Do not blindly cache live node truth.
2. **Cloudflare is optional.** Punkti must still work without DNS, HTTPS, Cloudflare, or any central service.
3. **The durable truth is the node atom log and node sync, not the CDN cache.**

| Layer | Role | Caching |
|-------|------|---------|
| Atom log (`/data/atoms.log.jsonl`) | Durable node truth | Never cached externally |
| Node sync (peer-to-peer) | Truth replication | Never cached — direct node-to-node |
| Public API (`/feed`, `/latest`, etc.) | Live node state | Must bypass CDN cache |
| PWA static assets (`/lib/*`, etc.) | Application code | Cacheable (with versioning) |
| Future static snapshots | Public read snapshots | Cacheable (immutable or near-static) |

## Cloudflare Role

Cloudflare (or equivalent CDN) is an **optional performance layer**, not a truth layer.

### Permitted Uses

| Use | Priority |
|-----|----------|
| Static asset acceleration (JS, CSS, fonts, icons) | Recommended |
| Basic DDoS/rate shielding | Recommended |
| TLS/HTTPS termination convenience | Recommended |
| Future cacheable public snapshots | Planned |

### What Cloudflare Must NOT Be Required For

- Node-to-node Punkti sync
- IP:port node operation
- Node identity verification
- Atom validity
- Trust decisions
- Operator SSH access

## Endpoint Cache Policy Table

### Cache Hard / Long TTL

These assets change infrequently and are safe to cache aggressively when versioned:

| Path | Policy | Notes |
|------|--------|-------|
| `/lib/*` | `public, max-age=31536000, immutable` | Third-party libraries (MapLibre, Dexie, etc.) |
| `/icons/*` | `public, max-age=31536000, immutable` | Static icon assets |
| `/static/*` | `public, max-age=31536000, immutable` | Future static assets |
| Future versioned assets (`*.v123.js`) | `public, max-age=31536000, immutable` | Content-hashed filenames |

### No-Cache / Bypass (Dynamic or Live)

These endpoints represent live node state and must **never** be blindly cached by CDN, browser, or intermediary:

| Path | Policy | Reason |
|------|--------|--------|
| `/` | `no-store, no-cache, must-revalidate` | PWA shell changes with every deploy |
| `/index.html` | `no-store, no-cache, must-revalidate` | PWA entry point |
| `/app.js` | `no-store, no-cache, must-revalidate` | Hard marker changes per deploy |
| `/ui-*.js` | `no-store, no-cache, must-revalidate` | UI code changes per deploy |
| `/feed` | `no-store` | Content changes with every new atom |
| `/feed?since=*` | `no-store` | Dynamic cursor-based response |
| `/latest` | `no-store` | Changes as new atoms arrive |
| `/stream` | `no-store` | Long-lived live stream (future) |
| `/node/info` | `no-store` | Changes with node state |
| `/status` | `no-store` | Changes with node state |
| `/health` | `no-store` | Must reflect real-time health |
| `POST /atom` | Negative (never cache) | Idempotent writes only |
| `/p/<atom_id>` | `no-store` | Currently dynamic; may become cacheable |
| `/sw.js` | `no-store` | Service worker must always be fresh |

**Important:** During active development with frequent deploys, even static-like JS assets (`/app.js`, `/ui-*.js`) use no-cache because the filenames are not yet content-hashed. Once versioned filenames are implemented, these move to the "cache hard" table.

## Future Cacheable Model

When static public snapshots are implemented (Phase 8.x), the following paths may become Cloudflare-cacheable:

| Path | Policy | Description |
|------|--------|-------------|
| `/public/feed-latest.json` | `public, max-age=60` | Latest atom snapshot, regenerated periodically |
| `/public/feed-000001.json` | `public, max-age=31536000, immutable` | Immutable historical snapshot by sequence |
| `/public/atoms/<atom_id>.json` | `public, max-age=31536000, immutable` | Immutable individual atom record |

These are generated cacheable public read snapshots. They are **eventually consistent** and not substitutes for live `/feed` or `/stream`.

## Caddy Header Guidance

The following `Cache-Control` headers should be set by Caddy (or equivalent reverse proxy) for each endpoint path prefix:

### Current Development Phase (no filename hashing)

```caddy
# All PWA and API endpoints — no caching during active development
header /* {
    Cache-Control "no-store, no-cache, must-revalidate"
    Pragma "no-cache"
}

# Exception: third-party libraries are cacheable
header /lib/* {
    Cache-Control "public, max-age=31536000, immutable"
}
```

### Future Stable Phase (with content-hashed filenames)

```caddy
# Live/dynamic endpoints
header /feed {
    Cache-Control "no-store"
}
header /latest {
    Cache-Control "no-store"
}
header /stream {
    Cache-Control "no-store"
}
header /node/info {
    Cache-Control "no-store, no-cache, must-revalidate"
}
header /status {
    Cache-Control "no-store, no-cache, must-revalidate"
}
header /health {
    Cache-Control "no-store, no-cache, must-revalidate"
}

# Application shell (still dynamic)
header / {
    Cache-Control "no-store, no-cache, must-revalidate"
}

# Versioned static assets (immutable once published)
header /*.v*.js {
    Cache-Control "public, max-age=31536000, immutable"
}
header /*.v*.css {
    Cache-Control "public, max-age=31536000, immutable"
}

# Third-party libraries
header /lib/* {
    Cache-Control "public, max-age=31536000, immutable"
}

# Future cacheable public snapshots
header /public/* {
    Cache-Control "public, max-age=60"
}
```

### Strict Headers for Production

```caddy
# Ensure no sensitive responses are cached
header / {
    Cache-Control "no-store, no-cache, must-revalidate"
    Pragma "no-cache"
    Expires "0"
}

# CORS for relay API when served on a different domain
header /node/info {
    Access-Control-Allow-Origin "*"
}
header /feed {
    Access-Control-Allow-Origin "*"
}
header /latest {
    Access-Control-Allow-Origin "*"
}
header /status {
    Access-Control-Allow-Origin "*"
}
header /health {
    Access-Control-Allow-Origin "*"
}
```

## Cloudflare Page Rules / Cache Rules Guidance

When configuring Cloudflare (or equivalent CDN) for a Punkto node:

### Bypass Cache Rules

These patterns should bypass Cloudflare cache entirely:

```text
*example.org/feed*
*example.org/latest*
*example.org/stream*
*example.org/node/info*
*example.org/status*
*example.org/health*
*example.org/atom*
*example.org/p/*
*example.org/sw.js
```

**Configuration approach:**

1. Create a Cache Rule (preferred) or Page Rule with "Cache Level: Bypass" for these patterns.
2. Do not enable "Always Online" for any of these paths.
3. Set Edge TTL to "Respect Origin" for uncacheable paths.

### Cache Eligible Patterns

These patterns may use Cloudflare cache:

```text
*example.org/lib/*
*example.org/icons/*
*example.org/static/*
*example.org/public/atoms/*    (future)
*example.org/public/feed-*.json (future)
```

**Configuration approach:**

1. Create a Cache Rule with "Cache Level: Standard" for these patterns.
2. Set Edge TTL to match origin's `max-age` directive (respect `Cache-Control`).
3. Enable "Always Online" only for these static patterns.

### Security Settings

```text
# Always use HTTPS
SSL/TLS: Full (strict)

# Enable WAF/rate limiting on POST /atom
WAF: On
Rate Limiting: 10 req/min per IP to /atom (adjust as needed)

# Disable caching of admin/operator pages
# (No admin pages currently exist; if added later, bypass cache)
```

## Safety Notes

1. **Never cache POST /atom.** All atom submissions must reach the origin relay.
2. **Do not cache admin or operator pages** if they are ever added.
3. **Do not expose private_key/secrets through cached pages.** The `/status` and `/node/info` endpoints already exclude secrets at the application level, but cache bypass adds defense-in-depth.
4. **If /status or /node/info accidentally expose bad data,** cache bypass reduces blast radius because the stale incorrect version is not served from cache.
5. **Node Doctor should be run against origin-representative hostnames** (e.g., `node1.punkto.xyz`, `node2.punkto.xyz`), not only cached CDN hostnames.
6. **Always verify cache behavior after Cloudflare configuration changes** using `curl -I` and cache-status headers.

## IP-First Compatibility

Cloudflare is an optional service layer. A Punkto node must function fully without it:

- A Punkti node may run on `http://IP:PORT` without DNS, HTTPS, or Cloudflare.
- DNS/HTTPS/Cloudflare are convenience layers for public web access.
- `node_id`/`fingerprint` remains node identity — it is not affected by caching.
- Atom signatures are verified by content, not by CDN.
- Trust is local operator policy, not CDN configuration.

## Implementation Status

| Item | Status |
|------|--------|
| This documentation | ✅ Complete (Phase 8.5) |
| Caddy header configuration | ⬜ Future PR |
| Cloudflare zone configuration | ⬜ Future PR |
| Versioned static asset filenames | ⬜ Future PR |
| Static public snapshots | ⬜ Future Phase (8.x) |
| Node Doctor cache header checks | ⬜ Future enhancement |

This PR is **documentation only**. Actual Caddy and Cloudflare configuration changes are separate, deployable PRs.
