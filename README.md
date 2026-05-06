# Punkto

> A coordinate in reality that can carry meaning.

Punkto is a minimal system for addressing points in 3D space and attaching small, signed data to those locations.

## Live

🌍 **https://punkto.xyz** — PWA, works offline, no account needed.

---

## What it does

- Every location in the world has a canonical address: `p:<12-char-3D-geohash>`
- You drop an **atom** (a short message) at a real-world coordinate
- Atoms are stored in an append-only NDJSON log
- Nodes sync with each other using byte-offset cursors
- The PWA shows atoms as a **3D point cloud** on a map (MapLibre + deck.gl)

### Canonical form

```
p:u07qskyuhbus        ← 12-char 3D geohash (lat + lon + alt interleaved)
```

### URI form

```
punkto://dk/copenhagen/bellahoj
```

### Atom (minimum)

```json
{ "punkto": "p:u07qskyuhbus", "t": 1777147183712 }
```

---

## Repo structure

```
Punkto/
├── pwa/                  ← PWA source (copy this to self-host)
│   ├── index.html        ← App shell, MapLibre + deck.gl
│   ├── app.js            ← Map, sync, atom rendering
│   ├── sw.js             ← Service worker (offline-first)
│   ├── manifest.json     ← PWA manifest
│   ├── geohash3d.js      ← 3D geohash encoder/decoder
│   └── node.py           ← Minimal Python node (stdlib only)
│
├── android/              ← Native Android app (Kotlin, MapLibre, Room)
├── core/                 ← Python library + CLI (stdlib only)
│
├── punkto.md             ← Canonical address format (source of truth)
├── punkto.node.md        ← Node API spec (endpoints, storage, sync)
├── punkto.manifest.md    ← Storage and replication rules
├── punkto.sync.md        ← Peer discovery and replication
├── punkto.ui.md          ← UI principles
└── punkto.ai.md          ← How AI agents interact as nodes
```

---

## Self-hosting

### Node (Python, stdlib only)

```bash
git clone https://github.com/Fisker1111/Punkto
cd Punkto/pwa
python3 node.py          # runs on port 8002
```

Serve `pwa/` as static files from your web server and proxy `/atom`, `/feed`, `/health`, `/info` to the Python node.

### Nginx example

```nginx
server {
  listen 443 ssl;
  server_name your.domain;
  root /var/www/punkto;

  location ~* ^/(atom|feed|health|info|punkto/) {
    proxy_pass http://127.0.0.1:8002;
  }
}
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Map | [MapLibre GL JS](https://maplibre.org/) |
| 3D rendering | [deck.gl](https://deck.gl/) ScatterplotLayer + PointCloudLayer |
| Local storage | [Dexie.js](https://dexie.org/) (IndexedDB) |
| 3D geohash | Custom `geohash3d.js` (12-char, 60-bit, alt interleaved) |
| Node | Python 3 stdlib — no dependencies |
| Sync | Byte-offset cursor, append-only NDJSON |
| Tiles | [OpenFreeMap](https://openfreemap.org/) (open, no API key) |
| Terrain | AWS elevation tiles (Terrarium encoding) |

---

## Protocol

Punkto is built on the **Punkti protocol** — open, local-first, no central authority.

See `punkto.md` for the full address format specification.

---

## Status

Early development — dogfood stage. Spec **v0.3**.

- **Live nodes**: two synced Punkto nodes (`app1.punkto.xyz`, `app2.punkto.xyz`), symmetric infra
- **Atoms**: ~21 on the live feed, mostly test content
- **PWA**: at **v22** — altitude input with building-aware floor picker just shipped
- **Python core + CLI**: complete, stdlib-only
- **Android**: paused on `android-native-paused` branch; PWA-first for v1.0
- **AI-discoverable**: `robots.txt`, `llms.txt`, `openapi.json`, `sitemap.xml`, server-rendered `/p/<id>` with OpenGraph

### Roadmap

- **Phase 1 (in progress)** — full 3D UX: altitude input ✅, lollipop sticks + altitude badges, 3D-default view
- **Phase 2** — ground truth via Open-Elevation API; "Floor 17" resolves to absolute altitude above sea level
- **Phase 3** — building stack view, altitude filter, floor-specific deep links
- **Later** — end-to-end signature validation, multi-node discovery beyond `PUNKTO_PEERS`, real users

### Known issues

- **No real users yet** — launch depends on Phase 1+2 completing (~1 week of AI-driven iteration)
- **`app1` SSL cert does not auto-renew** — manually placed cert in `/etc/ssl/punkto/`; will break on expiry. Fix: migrate to Let's Encrypt to match `app2`
- **Crypto signatures** (`sig` field) defined in spec v0.3 but not end-to-end validated in the live pipeline yet
- **AI agents can discover Punkto but can't yet meaningfully act on it** — discovery surfaces exist, incentive and tooling don't

---

## Philosophy

> A Punkto is not a database entry — it's a coordinate in reality that can carry meaning.

- **Local-first, not cloud-first** — no central authority, no global coordination required
- **3D-first, 2D-graceful** — altitude is a first-class dimension; UI reveals it where data exists, hides it when not
- **Simple > clever · explicit > implicit · readable > compact** (except the canonical format itself, which is compact by design)
- **Minimum protocol, maximum composability** — Punkti defines atoms + replication only; everything else is an app on top
- **Backward compatibility is sacred** — the canonical format never breaks
- **Append-only, signed** — atoms are never rewritten; signatures bind identity to content

---

## Python core library & CLI

The `core/` directory is a pure-stdlib Python library for working with Punkto addresses.

### Install (no dependencies)

```bash
git clone https://github.com/Fisker1111/Punkto
cd Punkto
```

### Generate a Punkto address

```bash
python3 -m core.cli make 55.7028 12.5088 13
# p:u07qsuustfsh
```

### Decode an address

```bash
python3 -m core.cli decode p:u07qsuustfsh
# lat=55.702820 lon=12.508793 alt=13.0m  (±2.4m)
```

### Convert between forms

```bash
python3 -m core.cli uri p:u07qsuustfsh
# punkto://u07qsuustfsh

python3 -m core.cli https p:u07qsuustfsh
# https://punkto.xyz/p/u07qsuustfsh

python3 -m core.cli resolve punkto://u07qsuustfsh
# p:u07qsuustfsh
```

### Write an atom to a live node

```bash
python3 -m core.cli write 55.7028 12.5088 13 "Hello from Bellahøj"
# Posted: p:u07qsuustfsh-a4x9k2
```

### Read atoms at a location

```bash
python3 -m core.cli read p:u07qsuustfsh
```

### All CLI commands

| Command | Description |
|---|---|
| `make <lat> <lon> [alt]` | Generate canonical address |
| `bare <lat> <lon> [alt]` | Spatial-only address (no id) |
| `decode <p:...>` | Decode to lat/lon/alt |
| `resolve <any>` | Any form → canonical |
| `validate <s>` | Validate format (exit 0/1) |
| `uri <p:...>` | Convert to `punkto://` form |
| `https <p:...>` | Convert to HTTPS URL |
| `near <a> <b>` | Check proximity |
| `id` | Generate a random short ID |
| `write <lat> <lon> <alt> <text>` | Post atom to node |
| `read <p:...>` | Read atoms at Punkto |
| `feed` | Read full node feed |
| `info` | Node info |

Default node: `https://punkto.xyz` — override with `PUNKTO_NODE=https://your.node`.

