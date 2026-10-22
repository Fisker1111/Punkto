# Punkti node release evidence (v0.6.0-draft.1)

Founder inspection record for CEO-OS issue #12. This ships the Founder-approved
Punkti 0.6 Layer-3 Mesh (issue #11) as a generic Docker node. It is an **unfrozen
draft release** for review; no production DNS, TLS or punkto.xyz deployment was
changed.

## Release artifacts

| Item | Value |
| --- | --- |
| Branch | `codex/self-hostable-node-image` (stacked on `proposal/punkti-0.6-mesh`) |
| Code commit / tag | `768828a` / `v0.6.0-draft.1` |
| Image | `ghcr.io/fisker1111/punkto-node:0.6.0-draft.1` |
| Manifest digest | `sha256:15209a2df79723c5486c03997516cf0b53c3d8892966687de3256ed40c03b81d` |
| Platforms | `linux/amd64`, `linux/arm64` (OCI image index) |
| CI run | https://github.com/Fisker1111/Punkto/actions/runs/39606484235 |
| SHA tag | `ghcr.io/fisker1111/punkto-node:sha-768828a` |

`carrier.py` and `spatial.py` are byte-identical to
`experimental/punkti-v0.6-mesh/src/` (enforced by `cmp` in CI). The only `mesh.py`
changes are operational: configurable bind/advertise origin, arbitrary http(s)
peer origins, persistence and operational-route hooks. Carrier, wire, signature,
validation and MID semantics are untouched. `latest` is not moved by prerelease
tags.

## Test results

| Suite | Result |
| --- | --- |
| Original Mesh reference (`experimental/punkti-v0.6-mesh/tests`) | 27/27 pass |
| Node operational suite (`punkti_node/test_node.py`) | 20/20 pass |
| Config validation (`--check-config`, both examples) | pass |
| Protocol source identity (`cmp`) | pass |
| CI Node image workflow | success (build + push, both platforms) |

## Proof topology

Four containers from the identical image (`sha256:15209a2d…`), on node1:

- `punkti-a` — `node-a`, peer `http://punkti-b:8000`
- `punkti-b` — `node-b`, peer `http://punkti-a:8000`
- `punkti-c` — narrow subscription `h_lo: "z"`, peer `punkti-a`
- `punkti-xyz` — `punkto.xyz` sample config, host-local port 18088

`punkti-a`, `punkti-b` and `punkti-c` ran on a Docker `--internal` network with no
route to the internet. Both directions synchronized two atoms with distinct
opaque Layer-4 `x` payloads (one containing Unicode and a NUL code point). Pulled
records were base64-identical to the submitted raw `R` on both nodes.

Observed results:

- `/health` 200 and `/ready` 200 (`status: ready`) on all three proof nodes.
- `node-a` and `node-b` converged to 2/2 valid atoms each, 0 corrupt lines.
- `node-c` rejected the out-of-range atom with `admitted: false, reason:
  out-of-scope` and retained 0 valid atoms.
- Outbound `https://punkto.xyz` from the isolated network failed (`URLError`).
- Graceful `docker stop` exited 0; logs show `shutdown requested signal=15` then
  `node stopped`.
- Containers were removed and recreated from the same volumes and configs:
  both atoms remained byte-identical, stores reported 2 valid / 0 corrupt, and
  each node kept its original epoch.
- PID 1 in the running container is UID/GID `10001`; the image contains no
  `/config` directory and no `punkto.xyz` string.
- The `punkto.xyz` sample container reported `node.name: punkto.xyz`,
  `public_url: https://punkto.xyz`, `branding.display_name: Punkto` with empty
  peers, using the same image and no source changes.

Raw evidence is attached to the Kanban task: `phase1.json`,
`after_restart.json`, `manifest.txt`, `image_ids.txt`, `recreated_ids.txt`,
`punkto-xyz-node-info.json`, and node logs.

## Acceptance mapping

| # | Requirement | Evidence |
| --- | --- | --- |
| 1 | Dockerfile | `node/Dockerfile` |
| 2 | Compose example | `docker-compose.node.yml` |
| 3 | Canonical example config | `node-config.example.yml` |
| 4 | GitHub build/publish workflow | `.github/workflows/node-image.yml`; multi-arch CI run above |
| 5 | Published test image/tag | `v0.6.0-draft.1`, manifest digest above |
| 6 | Clean first-start evidence | first-start containers reached `/health` and `/ready`; see `phase1.json` |
| 7 | Restart/recreation with preserved store | `after_restart.json`; exit 0, 2/2 atoms, stable epoch |
| 8 | Two differently configured nodes from one image sync | `node-a`/`node-b` bidirectional convergence, 2/2 atoms each |
| 9 | No punkto.xyz dependency | isolated internal network; egress blocked; no image/config reference |
| 10 | punkto.xyz instantiation config | `node-config.punkto-xyz.example.yml`; live container `/node/info` evidence |
| 11 | No protocol changes for packaging | `cmp` for carrier/spatial; operational-only `mesh.py` diff |

## Not done (requires separate Founder approval)

- No merge to `main`.
- No production DNS, TLS, reverse-proxy or punkto.xyz cutover.
- No stable/frozen release claim; protocol and storage format remain draft and are
  subject to issue #13 hardening.
