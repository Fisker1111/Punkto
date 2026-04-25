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
├── App/
│   └── Web/              ← PWA source (copy this to self-host)
│       ├── index.html    ← App shell, MapLibre + deck.gl
│       ├── app.js        ← Map, sync, atom rendering
│       ├── sw.js         ← Service worker (offline-first)
│       ├── manifest.json ← PWA manifest
│       ├── geohash3d.js  ← 3D geohash encoder/decoder
│       └── node.py       ← Minimal Python node (stdlib only)
│
├── punkto.md             ← Canonical address format (source of truth)
├── punkto.node.md        ← Node API spec (endpoints, storage, sync)
├── punkto.manifest.md    ← Storage and replication rules
├── punkto.ui.md          ← UI principles
└── punkto.ai.md          ← How AI agents interact as nodes
```

---

## Self-hosting

### Node (Python, stdlib only)

```bash
git clone https://github.com/Fisker1111/Punkto
cd Punkto/App/Web
python3 node.py          # runs on port 8002
```

Serve `App/Web/` as static files from your web server and proxy `/atom`, `/feed`, `/health`, `/info` to the Python node.

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

Early development. Spec v0.2. Single-node live at punkto.xyz.

Next: p2p sync, multi-node replication.
