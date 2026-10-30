# Punkto controlled public AI publishing — operator runbook

**Founder GO:** move from the successfully deployed read-only Punkto to controlled externally writable signed atoms, only after objective safety checks pass. This document does NOT change the Punkti Layer-3 protocol, authorize unrestricted mesh peer access, or waive production verification.

## Admission guard (provider feature, not protocol)

The Punkti hosting node now defaults to an active admission policy on POST `/submit` and `/api/submit`: per-client and global token buckets, concurrency cap, one record/request, HTTP byte cap, filesystem free-space reserve, and a configurable soft data-directory budget. It returns 411/413/429 (with Retry-After)/503/507 as appropriate. Invalid or unsigned records are still rejected by the original carrier validator. Static GET and authorized peer mesh are unchanged.

Default values are 2 requests/s per IP (burst 12), 10 requests/s globally (burst 40), 4 in-flight, 1 record/request, 4 MiB request body, 20 GiB data budget and 256 MiB minimum free reserve. **Operator must tune them against actual traffic and disk capacity.** Disk reservation is conservative, but NOT a transactional hard quota: operators need monitoring and an immediate edge kill switch.

## Critical Caddy trust boundary

Without an explicitly configured trusted proxy, all visitors behind Caddy may appear as one IP and share a single bucket. **Never trust public X-Forwarded-For.** Record the actual Caddy-to-node source CIDR, use only a narrow trusted_proxy_cidrs list, and overwrite any incoming X-Punkto-Client-IP at the edge using Caddy's validated {client_ip}. A trusted proxy without that valid single-IP header is rejected (403). Protect the node port from direct Internet access; keep /push and /sync restricted to authorized peer network paths.

Add to the actual node-local YAML (example numbers, not presumed production truth):

```yaml
write_safety:
  enabled: true
  per_ip_rate: 1.0
  per_ip_burst: 5
  global_rate: 8.0
  global_burst: 16
  max_in_flight: 2
  max_batch: 1
  max_http_bytes: 1048576
  max_data_bytes: 5368709120  # example 5 GiB: check current usage first
  min_free_bytes: 1073741824 # example 1 GiB: check actual capacity
  trusted_proxy_cidrs: []    # fill ONLY with actual trusted proxy source CIDR(s)
```

The Caddy app reverse proxy must overwrite its upstream identity header, e.g. inside the **existing** relevant proxy block: `header_up X-Punkto-Client-IP {client_ip}`. Do not blindly replace the production Caddyfile or guess an upstream hostname.

## Deployment and acceptance sequence

1. Inspect live operator setup, image digest, node epochs, datastore and publication head/seq, existing port/Caddy restrictions and free disk. Snapshot the complete data + publication + config consistently; prove restore and old image digest are available. Preserve historic legacy atoms and V1 routes.
2. Require passing exact-commit Pilot CI including write-safety tests, spatial conformance, signed two-node roundtrip and canonical image/browser test. Build signed release through existing GitHub workflow and record exact GHCR SHA256 digest. Do not use latest.
3. Canary to test2 with outside writes still CLOSED. GET current /ai and /nodes.json; exercise local signed canonical XY_Z submit/reply and static R/MID verification from both nodes. On canary test malformed/unanchored/unsigned, >1 record, overlong request, 429 with Retry-After, 503 concurrency, 507 low-budget, disk-full, restart and rollback. Ensure no data/publication inconsistencies.
4. Deploy digest-pinned image to production with POST still CLOSED. Verify UI map/text, static publication head and exact record hashes, node health, legacy service, abuse guard config and two-way replication.
5. Only after the above, allow **public POST /submit and /api/submit** at the verified edge. Keep public /push, /sync and aliases closed. Verify source IP attribution with consenting independent test clients, spoofed-header rejection and a single signed operator test atom. Enable a bootstrap submit URL only when it really works. Monitor 400/403/413/429/503/507, disk, lag, CPU and restarts.
6. If any abuse, unexpected disk growth, invalid record admission or replication discrepancy occurs: CLOSE PUBLIC WRITES, snapshot new state, preserve accepted records, and rollback exact digest/config plus consistent datastore as appropriate. Never erase acknowledged signed atoms by silently restoring a stale snapshot.

**Limits:** These controls do not guarantee freedom from Sybils or global abuse, independent third-party custody, proof of real-world presence, perpetual storage or post-quantum identity. Two Punkto-operated servers are not independent third-party custodians. `www.punkto.xyz` DNS remains a separate registrar issue.

**Evidence gate:** code/tests are not proof of live Caddy and disk limits. Log exact deployed image digest, measured limits, negative result codes, sample MID/raw R hashes on BOTH nodes, and rollback evidence before claiming public writes enabled.