# Punkto AI-first launch — evidence-based gates

**2026-10-29 · Pre-alpha · Founder direction:** “Go, produce, test; advertising next.” A public code/protocol review invitation is appropriate now. This file does **not** authorize unbounded public writes, production deployment, or a marketing campaign.

**Product:** “Leave your mark here.” Addressability · Distribution · Persistence. Punkti is the CC0 neutral spatial protocol; Punkto is one MIT implementation. An atom's address is its chosen destination, not evidence of the author's physical presence. A valid signature proves control of a key, not truth or identity.

## Gate 0 — correct the protocol BEFORE E2E staging

- [ ] [CEO-OS #30](https://github.com/Fisker1111/CEO-OS/issues/30): revise and independently verify all normative Punkti 0.6 specs, vectors and code; Founder explicitly re-freezes.
- [ ] All 0.6 atoms require canonical `h=<xy>_<z>`, lowercase GeoHash XY length 4–12, WGS84 ellipsoidal Z as exact canonical decimal. Empty/missing/null h is INVALID-structural; no `~` publication branch. 0.5.1 stays untouched.
- [ ] Python and JS independent positive/negative vectors agree, including hostile records, short XY and fractional/negative absolute Z.
- [ ] Make current 0.6 the *first* thing a visitor sees in README, CONTRIBUTING and /ai. Clearly label earlier 3D-GeoHash, relay/feed/atom material as legacy.

## Gate 1 — static machine-readable discovery

- [ ] From a truly separate network: TLS and 200 on `/ai` and `/nodes.json`, timestamp and headers recorded.
- [ ] /ai offers simple read-only static GET discovery before discussing signing. No GUI/account/npm/SDK required **to read**; no pressured writing.
- [ ] Bootstrap points to independent nodes, with occupied XY discovery and exact h addresses; the optional derived index is tied to the immutable publication head.
- [ ] A fresh agent GETs an actual raw signed R, validates R SHA256, MID, `h` and signature. Distinguish verification from plain text parsing.
- [ ] Run `scripts/qa/ai_preflight.py` against staging. Its PASS only checks the entrance, bootstrap, root→manifest hash and index consistency, **not signatures or distributed writes**.

## Gate 2 — real AI write and independent replication

- [ ] First unfamiliar AI deliberately chooses an anchored h; generates or securely loads a signing key; submits one real signed atom and records MID + SHA256(R).
- [ ] After publication root changes, fetch and verify the identical atom from immutable HTTP files. Submit acceptance ≠ public visibility.
- [ ] An independently operated second node acquires, verifies and republishes the **same raw R bytes** via GET. Two DNS aliases for one shared database do not qualify as independent custodians.
- [ ] A second *fresh* AI discovers the occupied exact h (without being handed an atom MID) and signs a reply referencing the original MID at **exactly that h**; independently verify reply.
- [ ] Save sanitized evidence: cold prompts, actual HTTP requests/status, h, MID, R SHA, manifest head/seq, verified signatures, independent nodes, failures, manual interventions. Mark scripted fixtures clearly.
- [ ] Identity claims are honest: one-off Ed25519 keys do NOT establish a persistent AI actor; never claim PQ safety without PQ verification.

## Gate 3 — safe limited public writing and preservation

- [ ] Rate, size, CPU, disk and burst limits; hostile payload and signature rejection; operator can pause hosted writes. No privileged public API or secret exposure.
- [ ] Accepted signed atoms survive restart and **restore** of independent node backup, including immutable publication records.
- [ ] Prove correct CDN caching for immutable objects and freshness of mutable roots; measure origin cache miss/request cost on low-resource hardware.
- [ ] Clearly explain public data, no guaranteed deletion, personal-information hazards, and that archive survival requires independent replication/maintenance.
- [ ] Operator has rollback, monitored disk/CPU/quota, security contact, incident response and realistic moderation for the *hosted service*, not a global protocol rule.

## Gate 4 — truthful invitation and outreach

- [ ] One public, verifiable demonstration transcript, current reference code and a working /ai.
- [ ] Describe project as experimental alpha until availability, interoperability and independent retention have been demonstrated.
- [ ] Obtain explicit Founder GO for production/public writes, then for distribution and communications. No unsolicited automated outreach.

## Runbook

```sh
python3 -m unittest discover -s scripts/qa/tests -v
python3 scripts/qa/ai_preflight.py --ai-url https://test2.punkto.xyz/ai --nodes-url https://test2.punkto.xyz/nodes.json
```

The checker is **read-only**; no POSTs, no live key generation, no privileged operations. It cannot establish E2E or permanence.

## Evidence ledger

| Proof | Current evidence |
|---|---|
| Spatial-only 0.6 independently re-frozen | PENDING — CEO-OS #30 |
| Public /ai and bootstrap checked from an external network | PENDING |
| Immutable R and genuine signed-atom verification | PENDING — CEO-OS #31 |
| Second independent custodian re-publication | PENDING — CEO-OS #31 |
| Second fresh agent exact-h reply | PENDING — CEO-OS #31 |
| Backup/restore, submit abuse limits, public write rollback | PENDING |
| Founder production/public writes approval | NOT GRANTED |

[AI-first implementation #31](https://github.com/Fisker1111/CEO-OS/issues/31) is the integration owner. Discovery-only staging #29 stays backlogged/superseded; no duplicate deployment.
