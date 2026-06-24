# Punkto

> A coordinate in reality that can carry meaning.

Punkto is a minimal system for addressing points in 3D space and attaching small, signed data to those locations. Open protocol, local-first, no central authority.

Every atom is addressable. Every ROOT atom is a board.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Repo release](https://img.shields.io/badge/release-v0.5-blue.svg)](https://github.com/Fisker1111/Punkto/releases/tag/v0.5)
[![Live](https://img.shields.io/badge/live-punkto.xyz-green.svg)](https://www.punkto.xyz)

> Status: **v0.x public draft**. The `v0.5` tag covers the current UI shell refactor + Docker stabilisation. Individual specs evolve independently. See the per-spec versions in [Status](#status) and [Documentation](#documentation).

## Live

🌍 **https://www.punkto.xyz** — PWA, works offline, no account needed.

---

## What it does

- Every location in the world has a canonical address: `p:<12-char-3D-geohash>`
- You drop an **atom** (a short signed message) at a real-world coordinate
- Atoms are stored in an append-only NDJSON log on a relay node

> **⚠ Public data notice:** Atoms are public and may be retained by other nodes. Do not post passwords, secrets, sensitive personal information, or anything you may need permanently deleted. Signing proves authorship and integrity; it does not encrypt the atom.
- Relays expose two read endpoints. `/feed?since=<cursor>` is a byte-offset stream — used by the PWA for resumable sync and by relay-to-relay replication. `/latest` returns the most recent N atoms in a single response — preferred for new clients and Flow-TV-style live displays. Both are first-class today; `/feed` may eventually be replaced by `/latest` for clients while staying for peer sync.
- Signed atoms can be verified offline by clients or with `tools/punkto-key.py verify`. Reference relays enforce signature requirements (`PUNKTO_REQUIRE_SIG=true`) — unsigned atoms are rejected with HTTP 403 `missing_sig`.
- The PWA shows atoms as 3D bubbles on a map (MapLibre + deck.gl)
- Every atom is addressable by its canonical `atom_id`
- A ROOT atom starts a board — a public conversation at one exact location
- A REPLY atom lives inside a board, linked by explicit `parent_id`, not by proximity
- A nearby ROOT atom (even 2 cm away) is a separate board; clustering is UI only

### Canonical form

```
p:u07qskyuhbus        ← 12-char 3D geohash (lat + lon + alt interleaved)
```

### Atom (minimum)

```json
{ "punkto": "p:u07qskyuhbus", "t": 1777147183712 }
```

With identity (full):

```json
{
  "f": "cw8sj6q5xzsc",
  "pubkey": "nVM1dfmtw+FO9pQzj1b0Sg+/x8tIi+NHAAxpNeAR0l0=",
  "punkto": "p:u07qskyuhbus",
  "t": 1777147183712,
  "x": "hello, world",
  "sig": "<base64 Ed25519 signature>"
}
```

---

## Repository structure

```
Punkto/
├── pwa/                  ← Reference web app (vanilla JS, MapLibre, deck.gl)
│   ├── Dockerfile        ← Docker image: Caddy serving static files
│   ├── index.html        ← App shell (two-view UI: Text / Map + ⚙ settings)
│   ├── app.js            ← App lifecycle, sync, IndexedDB, atom creation, network
│   ├── ui-shell.js       ← Page switching, bottom nav, settings panel
│   ├── ui-text.js        ← Text feed rendering, cards, empty states
│   ├── ui-map.js         ← Map view wrapper, lazy init, resize
│   ├── sw.js             ← Service worker unregister (SW disabled — plain web app)
│   ├── manifest.json     ← PWA manifest
│   ├── key-management.js ← Ed25519 identity, BIP39 mnemonic
│   ├── geohash3d.js      ← 3D geohash encoder/decoder
│   ├── privacy.html      ← Privacy page
│   └── reset.html        ← Local-data reset / cache bust page
│
├── relay/                ← Reference relay node (Python + requests)
│   ├── Dockerfile        ← Docker image: Python relay service
│   ├── relay.py          ← Single-file relay server
│   ├── README.md         ← Operator guide
│   ├── requirements.txt  ← Just `requests`
│   ├── test_relay.py     ← Smoke tests
│   └── .env.example      ← Configuration template
│
├── deploy/               ← Docker deployment configs
│   ├── docker-compose.yml ← Service definitions (web + relay)
│   ├── .env.example      ← Shared environment template
│   ├── server1/          ← Caddyfile for primary server
│   ├── app2/             ← Caddyfile + env for secondary server
│   └── README.md         ← Deployment guide
│
├── core/                 ← Pure-Python core library + CLI (stdlib only)
│   ├── punkto.py         ← Address encode/decode
│   ├── geohash3d.py      ← 3D geohash implementation
│   └── cli.py            ← Command-line tools
│
├── tools/                ← Standalone CLI utilities
│   ├── punkto-keygen-v0.1.py   ← Mint a fresh identity (12-word mnemonic)
│   └── punkto-key.py            ← Full identity toolkit (new/import/sign/verify)
│
├── punkto.md             ← Address format & atom (the protocol's heart)
├── punkto.sync.md        ← Replication: canonical bytes, atom_id, peer sync
├── punkto.node.md        ← Node API: endpoints, storage, behavior
├── punkto.relay.md       ← Relay role: rolling buffer, /latest, three-role model
├── punkto.identity.md    ← Identity: Ed25519, BIP39 mnemonic, Author ID
├── punkto.manifest.md    ← Atom data model & storage
├── punkto.ui.md          ← UX guidelines
├── punkto.ai.md          ← AI agents as Punkto nodes
│
├── README.md             ← This file
├── LICENSE               ← MIT
├── CONTRIBUTING.md       ← How to contribute
├── CODE_OF_CONDUCT.md    ← Contributor Covenant 2.1
├── SECURITY.md           ← Vulnerability disclosure policy
└── CHANGELOG.md          ← Version history
```

---

## Documentation

All specs are authoritative source-of-truth Markdown files in this repository:

| Spec | Topic |
|---|---|
| [`punkto.md`](punkto.md) | Address format, canonical form, atom basics |
| [`punkto.identity.md`](punkto.identity.md) | Ed25519 keys, 12-word BIP39 mnemonic, Author ID |
| [`punkto.sync.md`](punkto.sync.md) | Canonical JSON, atom_id, signature, peer replication |
| [`punkto.node.md`](punkto.node.md) | Node HTTP API: `/atom`, `/feed`, `/health`, `/info` |
| [`punkto.relay.md`](punkto.relay.md) | Relay role, rolling buffer, `/latest`, three-role architecture |
| [`punkto.manifest.md`](punkto.manifest.md) | Atom data model and storage rules |
| [`punkto.ui.md`](punkto.ui.md) | UI principles for any Punkto client |
| [`punkto.ai.md`](punkto.ai.md) | AI agents as Punkto nodes |
| [`docs/punkto-node.md`](docs/punkto-node.md) | Deployable node model: config, persistence, identity, serving policy |
| [`docs/fresh-install-ubuntu.md`](docs/fresh-install-ubuntu.md) | Step-by-step: fresh Ubuntu 24.04 server to running Punkto node |
| [Launch Candidate Checklist](docs/launch-candidate-checklist.md) | Pre-public-alpha readiness checklist |

Also of interest:

- [`relay/README.md`](relay/README.md) — operator guide for running a relay
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute
- [`SECURITY.md`](SECURITY.md) — how to report vulnerabilities
- [`CHANGELOG.md`](CHANGELOG.md) — what changed and when

---

## Quick start

### Run the PWA locally

No build step — just static files.

```bash
git clone https://github.com/Fisker1111/Punkto.git
cd Punkto/pwa
python3 -m http.server 8080
# Open http://localhost:8080
```

By default the PWA talks to `https://www.punkto.xyz`. Edit `pwa/app.js` to point at your own relay.

### Run a relay node (local / development)

```bash
git clone https://github.com/Fisker1111/Punkto.git
cd Punkto/relay
pip install -r requirements.txt
python3 relay.py
# Listens on http://127.0.0.1:8000
```

See [`relay/README.md`](relay/README.md) for configuration and operator notes.

### Deploy a production node (Docker)

Each node runs two containers — Caddy (static PWA + TLS) and the Python relay.

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Set up the node
mkdir -p ~/punkto
# Copy deploy/docker-compose.yml and the matching Caddyfile to ~/punkto/
# Create ~/punkto/.env from deploy/.env.example

# 3. Start
cd ~/punkto && docker compose up -d

# 4. Verify
curl https://your-domain.example.com/health
```

Upgrade: `docker compose pull && docker compose up -d`  
Rollback: edit `.env` → `PUNKTO_VERSION=v0.44` → `docker compose up -d`

See [`deploy/README.md`](deploy/README.md) for the full deployment guide.

### Mint a Punkto identity

```bash
pip install cryptography   # or: sudo apt install python3-cryptography
wget https://raw.githubusercontent.com/Fisker1111/Punkto/main/tools/punkto-keygen-v0.1.py
python3 punkto-keygen-v0.1.py
```

Produces a 12-word recovery phrase + Author ID + public key. Write the words on paper.

---

## Tech stack

| Layer | Technology |
|---|---|
| Map | [MapLibre GL JS](https://maplibre.org/) |
| 3D rendering | [deck.gl](https://deck.gl/) (Scatterplot, PointCloud, Line layers) |
| Local storage | [Dexie.js](https://dexie.org/) (IndexedDB) |
| 3D geohash | Custom `geohash3d.js` (12-char Base32, 60-bit, lat/lon/alt interleaved) |
| Relay | Python 3 stdlib + `requests` (only dep) |
| Sync | Pull-based `/latest`, rolling buffer (Flow TV semantics) |
| Identity | Ed25519 + 12-word BIP39 mnemonic |
| Tiles | [OpenFreeMap](https://openfreemap.org/) (open, no API key) |
| Terrain | AWS elevation tiles (Terrarium encoding) |

---

## Three roles

Punkto separates concerns across three independently-scalable roles ([`punkto.relay.md`](punkto.relay.md)):

| Role | Stores | Cost profile | Free? |
|---|---|---|---|
| **Relay** | Rolling buffer — last N atoms or last T time | Tiny RAM, no DB scans | Free, easy to run |
| **Client** (PWA, native) | User's local slice (IndexedDB) | User's device | Free, user-owned |
| **Archive** (future) | Full history, indexed, searchable | Heavy I/O, real DB | Optionally paid |

Relays are a public commons. Clients are user-owned. Archives are optional and may be operated commercially without breaking the protocol's open nature.

---

## Status

Active development — **v0.5**, dogfood stage.

- **Live nodes**: two synced reference relays (`app1.punkto.xyz`, `app2.punkto.xyz`) — both running Docker (Caddy + Python relay), auto-HTTPS via Let's Encrypt, deployed via `docker compose`
- **Atoms**: 20+ on the live feed, mostly seed/test content
- **PWA**: at v53 — minimal two-view shell (Text / Map), 4-button bottom nav (Text | Map | + | ⚙), modular UI (ui-shell.js / ui-text.js / ui-map.js), Docker-deployed, no service worker, in-browser key generation, 3D altitude input, Open Graph deep links
- **Relay**: v0.1 — rolling buffer (10 000 atoms or 7 days), `/latest`, peer sync, `/p/<id>` server-rendered cards
- **Identity**: v0.1 — `tools/punkto-keygen-v0.1.py` and `tools/punkto-key.py` produce byte-identical results across implementations
- **AI-discoverable**: `robots.txt`, `llms.txt`, `openapi.json`, `sitemap.xml`, server-rendered `/p/<id>` with OpenGraph + JSON-LD

### Roadmap

- **v0.5** — relay-side signature verification (`PUNKTO_REQUIRE_SIG=true`); PWA identity export / print recovery card
- **v0.6** — Phase 2 altitude: Open-Elevation ground lookup so "Floor 17" resolves to absolute altitude above sea level
- **v0.7** — Phase 3 altitude: building stack view, altitude filter, floor-specific deep links
- **v1.0** — first reference Archive node, third-party relay implementations in other languages, real users in multiple cities

### Known issues

- **Relay v0.1 stores `sig` and `pubkey` but does not verify signatures yet** — verification is planned for relay v0.2
- **Flow TV pruning is active**: atoms older than 7 days age out of the relay buffer. This is by design; archives are the future home of long-term history
- **PWA identity UI is basic** — in-browser key generation and import work; export / print recovery card are on the v0.5 roadmap
- **Real-user adoption is small** — early dogfood phase; growing the network is the next priority after v0.5

---

## Philosophy

> A Punkto is not a database entry — it's a coordinate in reality that can carry meaning.

- **Local-first, not cloud-first** — no central authority, no global coordination required
- **3D-first, 2D-graceful** — altitude is a first-class dimension; UI reveals it where data exists, hides it when not
- **Simple > clever · explicit > implicit · readable > compact** (except the canonical address format itself, which is compact by design)
- **Minimum protocol, maximum composability** — Punkto defines atoms + replication only; everything else is an app on top
- **Backward compatibility is sacred** — once v1.0, the canonical format never breaks
- **Append-only, signed** — atoms are never rewritten; signatures bind identity to content
- **Forgettable by default** — relays carry the now; clients keep what they witnessed; archives serve those who ask

---

## Python core library & CLI

The `core/` directory is a pure-stdlib Python library for working with Punkto addresses.

```bash
# Generate a Punkto address
python3 -m core.cli make 55.7028 12.5088 13
# → p:u07qsuustfsh

# Decode an address
python3 -m core.cli decode p:u07qsuustfsh
# → lat=55.702820 lon=12.508793 alt=13.0m  (±2.4m)

# Convert between forms
python3 -m core.cli https p:u07qsuustfsh
# → https://www.punkto.xyz/p/u07qsuustfsh

# Write an atom to a live relay
python3 -m core.cli write 55.7028 12.5088 13 "Hello from Bellahøj"
```

Default relay: `https://www.punkto.xyz` — override with `PUNKTO_NODE=https://your.relay`.

---

## License

Punkto is released under the [MIT License](LICENSE).

Copyright © 2026 Fisker. The protocol itself is uncopyrightable; what's licensed is this reference implementation. You're free to use, modify, sublicense, and distribute under MIT terms.

---

## Contributing

Contributions are very welcome — typo fixes, spec clarifications, performance improvements, new language implementations, or running a relay in your city.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). For security issues, see [`SECURITY.md`](SECURITY.md).

---

## Get in touch

- **Issues & discussion**: [GitHub Issues](https://github.com/Fisker1111/Punkto/issues)
- **Security**: fisker@protonmail.ch (see [SECURITY.md](SECURITY.md))
- **Live PWA**: [punkto.xyz](https://www.punkto.xyz)

---

> *Punkto begins. Anyone, anywhere, can sign atoms.*
