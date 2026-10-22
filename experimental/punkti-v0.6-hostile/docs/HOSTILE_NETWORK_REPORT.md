# Punkti 0.6 — hostile-network hardening report

Branch: `hardening/punkti-0.6-hostile` (base: approved clean-room proof `cb5f5a5`; additive only, not merged,
not deployed)
Scope: CEO-OS Issue #13. Nothing in this report freezes the protocol.

## 1. What was executed

| Suite | Tests | Result |
|---|---|---|
| Reference mesh (`experimental/punkti-v0.6-mesh`) | 27 | pass |
| NairobiDot clean-room (`experimental/nairobidot-l3`) | 23 | pass |
| Clean-room interop matrix | 13 | pass |
| Hostile harness (this experiment) | 125 | pass (twice, locally) |
| Hostile harness inside a resource-limited container | 125 | pass |

The hostile harness drives two independent implementations through their own subprocess adapters and
real loopback HTTP: no wire mocks. Faults are injected by a programmable TCP proxy
(`src/hostile/faultproxy.py`): partition, drop-before, drop-after-admission, duplicate delivery,
reordered PUSH batches, delay, stall, slow drip, truncated responses, single-byte corrupt JSON.
Ten network scenarios each run in both initiator directions (reference→clean-room, clean-room→reference).

Container run: image `ghcr.io/fisker1111/punkto-node@sha256:15209a2df79723c5486c03997516cf0b53c3d8892966687de3256ed40c03b81d`,
`--network host --cpus 0.5 --memory 512m --pids-limit 256`, on node1.punkto.xyz. All 125 hostile tests
passed in 220 s (120 s locally), which shows the harness and both implementations survive a 0.5-CPU /
512 MB cgroup limit. The peer URLs stay on `127.0.0.1` because the reference implementation only accepts
loopback peer origins; a two-host container cluster was therefore **not** executed (see Limitations).

Adversarial protocol suite: 308 cases (154 per implementation) covering the mandatory Issue test classes:
malformed/truncated/tampered envelopes, replay/duplicates, provenance failures, corrupt range responses,
out-of-order delivery, sparse/large set differences, overlapping spatial scopes, XY+Z boundaries, cursor
edge cases, bootstrap/eclipse manipulation, stale/incomplete coverage advertising, unknown future L4
payloads, disappearance/rejoin. Every case is classified AGREE / DIVERGE / DEFECT and stored with exact
input bytes in `evidence/protocol.json`.

Result: **282 AGREE, 24 DIVERGE, 2 DEFECT (both in the clean-room reading of a bound-policy the spec leaves
open). No case admitted a forged, malformed or mismatched record into a valid store; none suppressed a
valid record; none crashed a node.** Unknown algorithms and future versions stayed opaque and were
preserved byte-exact; unknown payload bytes, refs and extension bytes survive both implementations.

## 2. Demonstrated protocol ambiguities and minimal resolutions

Full table with exact observed behaviour is in `docs/FINDINGS.md` §2b. Summary of what a freeze text must
settle (no wire-format change is proposed for any item):

1. **`t: -0`** — reference accepts, clean-room rejects. Resolution: reject as non-canonical on JSON import.
2. **Wrapper-level failures** (transport digest mismatch, declared-address mismatch) — reference returns
   HTTP 400 for the request, clean-room returns per-record `INVALID-structural`. Resolution: descriptor
   errors are request errors (400); record-content errors stay per-record.
3. **Page limit above the advertised maximum** — 400 vs 413. Resolution: resource refusal (413).
4. **Initial MID cursor value** — `null` vs `["", ""]`. Resolution: `null`; clients echo tokens, never construct them.
5. **`lo >= hi` / equal or reversed spatial-Z bounds** — reference rejects, clean-room returns an empty
   page. Resolution: reject as a bad request, because an empty result is indistinguishable from "no data"
   for freshness reasoning. This is the only item that requires a behaviour change in one implementation.
6. **`hello.limits` member names** — differ. Resolution: publish a normative table or declare `limits`
   informational.
7. **Poisoned discovery hints** — both raise different exceptions. Resolution: hints are untrusted; a
   malformed hint is skipped, never fatal.
8. **Peer error taxonomy** (timeout / unreachable / malformed) and failure deadlines — unspecified, both
   implementations differ. Resolution: local policy, must not be inferred from strings.
9. **Interrupted/corrupt page atomicity** — undefined whether a JSON page with mixed valid/invalid items is
   transactional. Tests pin the observed safe subset; the text should state that a failed body does not
   advance the checkpoint and does not admit from the undecodable page.
10. **Coverage freshness** — `hello` advertises scopes but not completeness or freshness; a peer may
    legitimately hold only part of an advertised scope. No protocol mechanism detects withholding. This is
    a limitation to state, not a defect to fix.
11. **PUSH framing** — the reference uses one record per request and wraps the reciprocal direction of
    `connect()` in one synchronous HTTP callback; at 5000 atoms that callback exceeded its own 5 s client
    deadline while the same records transferred fine when the directions were driven separately. The spec
    does not require a synchronous callback; implementations should bound or split it.
12. **Eclipse/bootstrap** — `discover()` returns hints only; neither implementation auto-connects to hints.
    Tests confirm 500 bogus advertised peers cause no outbound connections and no store change. Keep this
    as a MUST in the Mesh text.

## 3. Measured PUSH + HTTP Range PULL (decision evidence)

`docs/SCALE_MEASUREMENT.md`, raw data in `evidence/scale.json`. Reference implementation, loopback, 200-byte
payloads, JSON body bytes (headers excluded):

| n | overlap | converged | requests | wire bytes | useful bytes | steady re-sync |
|---|---|---|---|---|---|---|
| 100 | 1.0 | yes, 1 round | 212 | 295 KB | 0 | 1.7 KB / 6 req |
| 1000 | 1.0 | yes, 1 round | 2068 | 2.94 MB | 0 | 1.7 KB / 6 req |
| 1000 | 0.0 | yes, 1 round | 2068 | 2.91 MB | 384 KB | 1.7 KB / 6 req |
| 5000 | 0.0 | yes, 1 round | 10 318 | 14.6 MB | 1.92 MB | 1.7 KB / 6 req |
| 5000 (fresh subscriber) | — | yes | 158 | 3.48 MB | — | — |

- Correctness: every cell converged in one round to the exact union, with no duplicates and no candidate growth.
- Cost: the **first** mutual sync of a pair is O(total set) in both directions, independent of the size of
  the difference (1000 identical atoms still cost 2068 requests / 2.94 MB).
- Incremental cost with retained cursors is O(1) (6 requests / ~1.7 KB even at 5000 atoms).
- A fresh subscriber costs one full O(n) sweep (158 requests / 3.48 MB at 5000 atoms); that is the case a
  digest-summary reconciliation would improve.
- PUSH is one request per record, so request count dominates WAN latency, not bytes.
- One near-limit 1 MiB record costs ~1.33x its size on the wire (base64 in JSON).

**Verdict: keep simple PUSH + Range PULL.** No measured cell shows a correctness need for Negentropy or any
other reconciliation protocol. The measured inefficiency is bootstrap/whole-set bandwidth, which is an
efficiency question that can be addressed after freeze without changing the carrier or the Mesh wire shape.

## 4. Remaining limitations (must not be papered over)

- No global completeness or freshness: withholding, partitions and retention mean a full page is not global truth.
- No peer authentication, no transport confidentiality, no rate limiting, no durable storage in either implementation.
- No deletion/compaction agreement; convergence is conditional on eventual delivery and compatible retention.
- No proof of real-world location, time or identity; signatures prove key control only.
- Measurements are loopback (single host) plus a single-host container cgroup run; no two-host container run
  and no WAN measurement were executed because both implementations reject non-loopback peer origins.
- The adversarial corpus is finite (308 cases) and generated by this harness; it is not a proof of total coverage.
- Sequence numbers are local arrival order, not protocol order.

## 5. Recommendation

**Focused revision, then freeze candidate.** Carrier bytes, MIDs, signatures and the PUSH/Range-PULL wire
shape are interoperable across two independent implementations on every measured correctness case, and the
simple mechanisms are sufficient. The blockers to a freeze candidate are 11 specification-text gaps plus one
small behaviour alignment (equal/reversed bounds rejection). Closing those is a focused documentation and
conformance-vector task, not a protocol redesign. Freeze still requires separate Founder approval.

Suggested freeze vectors to add (only where a divergence was demonstrated): `t: -0` rejection, wrapper-level
error tier, over-limit page refusal, equal/reversed MID and spatial bounds, initial MID cursor, `hello.limits`
shape. Existing normative vectors need no change.

## 6. Reproduction

```sh
# hostile suite (real loopback HTTP, no mocks)
PYTHONPATH="$PWD/experimental/punkti-v0.6-hostile/src" \
  python3 -m unittest discover -s experimental/punkti-v0.6-hostile/tests -v

# scale matrix -> evidence/scale.json + docs/SCALE_MEASUREMENT.md
python3 experimental/punkti-v0.6-hostile/src/hostile/measure_scale.py

# baselines
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
PYTHONPATH="$PWD/experimental/nairobidot-l3/src" python3 -m unittest discover -s experimental/nairobidot-l3/tests
python3 -m unittest discover -s experimental/nairobidot-l3/interop
```

Work split: part 1 (fault-injection harness) was authored by Codex CLI; the Codex account hit its usage
limit mid-task, so the adversarial suite, scale measurement and this report were completed directly by the
Hermes worker with the same constraints (additive only, no implementation changes) and full local test runs.

No implementation source, baseline test, proposal document, deployment or production state was modified.
