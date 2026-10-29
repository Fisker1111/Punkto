# Future isolated AI-first rollout and rollback

**No deployment is authorised by this document.** Stage 0 writes only to local
loopback nodes. This plan concerns a future, separately authorised isolated
`test2.punkto.xyz` rollout, never production or node1/node2. #32 stays backlog;
this document creates no tasks and authorises no pilot seed publications.

## Preconditions

- #30 merged; spatial-only v0.6 re-frozen and Founder-accepted after independent
  conformance proof. Reconcile PR #124/#125 and #127 in the documented order.
- Exact reviewed commit and image digest, required CI green, operator authorization.
- `/ai` and `/nodes.json` serve the current protocol; reads require no SDK/account.
- Entrance presents Explore / harvest, Publish / discuss, Store / serve,
  Replicate / preserve as voluntary overlapping activities, not Layer-3 types.
  Punkti remains universal/open/CC0/provider-neutral; Punkto competes as one
  commercial managed-service provider, without address ownership or captivity.
- A genuine cold-agent archive is distinct from the Stage-0 scripted harness log.

## Inspect first, record before changing anything

Record timestamp, host, running container image digest (`docker inspect`), compose
configuration, node config, bootstrap list, production/staging identities, data
directory and publication path, log atom count and publication record count,
root head/seq, available disk, Caddy route and current rate/size rules. Check that
mounts and upstreams cannot target production. Retain sanitized config and hash
of the backup manifest; do not expose credentials. Stop if the host differs from
the approved target or the datastore cannot be backed up consistently.

## Stages, one separately verified change at a time

1. Freeze staging writes and peer ingestion at the proxy/runtime, stop the node,
   snapshot the entire data directory (atom log, metadata, cursors, publication)
   and config together. Validate readability and hashes. Rollback: restore that
   complete snapshot and original config; restart the original digest, then reads.
2. While still isolated, start the explicitly approved image **by digest**, with
   separate staging data and identities. No production mounts/peers/bootstrap.
   Check health and config. Rollback: stop it and restore the previous digest plus
   the consistent pre-change snapshot; retain failed-state data for inspection.
3. Configure staging `/ai` and bootstrap for the spatial-only entrance; verify GET
   tree hashes before allowing controlled writes. Rollback: restore recorded Caddy
   and bootstrap config, validate Caddy config and reload; keep writes closed.
4. Enable only the authorised controlled trial, capture real read → signed anchored
   write → static verify → peer verify → same-h reply evidence. Rollback: close
   writes/ingestion, preserve a new consistent snapshot, then follow full rollback
   below. An accepted signature alone is not visibility proof.
5. Stop for Founder acceptance. A public invitation requires the separate
   [pre-alpha gate](launch-candidate-checklist.md), not this run's success.

## Public-write safeguards (proposed operator policy, not installed here)

Before enabling writes document and test actual enforced limits at the proxy and
node. A conservative starting staging policy is 4 MiB HTTP body, 1 record per
request, 1 submit/second/source IP with burst 5, plus a global 10 submits/second;
these are operator policy, not Layer-3 protocol changes or guaranteed safe values.
The frozen carrier separately bounds body to 1 MiB and record to 2 MiB. JSON/base64
expansion must fit the transport limit. Return explicit 413/429 and Retry-After;
test batching, chunked requests, concurrent sources and disk-full behavior.
Do not pretend signatures prevent flooding or that IP limits prevent Sybils.
Set a storage budget and stop writes before reserve disk is exhausted, monitor
log/publication growth, maintain abuse reporting and retention/archive policy,
and bound CPU/concurrency. Re-evaluate capacity before expanding the trial.

Reads remain ordinary static files over HTTP, no login or live database; preserve
Pi/nginx/CDN/Cloudflare compatibility. Cache immutable digest-named objects for a
long lifetime; root/bootstrap must revalidate to avoid hiding new heads. The
current development static server uses no-cache for JSON, so check the future
proxy's actual cache headers instead of claiming immutable caching is installed.
Review global public spatial-memory privacy wording before invitation: payloads
are public, signatures do not encrypt, remote copies may outlive local deletion.

## Full rollback procedure

1. Close `/submit` and pause peer ingestion; record final head/seq and errors.
2. Stop the container. Snapshot the failed state for recovery; never overwrite it.
3. Select the recorded previous image digest and its matching, verified full
   datastore/config snapshot. If retaining post-change writes is required, first
   prove old-image replay compatibility in isolation; otherwise archive them and
   restore the pre-change snapshot as a unit.
4. Restore atom log, metadata, cursors and publication together to the staging
   mount. Point the compose image at the recorded `repository@sha256:digest`,
   restore recorded config/routes, and start that digest. Never use a moving tag.
5. Verify running digest, health, log count, root head/seq, immutable-object hashes
   and sample signatures against the snapshot. A rollback must not leave the
   publication and atom log disagreeing. Keep writes closed on any mismatch.
6. Test GET and the controlled local acceptance path; only then seek renewed
   staging-write authorization. Record outcome, exact digest and preserved data.

## Metrics and keys

Capture CPU/memory via `docker stats --no-stream`, disk/log/publication sizes via
filesystem accounting, GET counts/bytes and submit/error rates from Caddy access
logs grouped by path/status, cache-hit ratio from proxy/CDN cache-status counters,
and head/seq by fetching publication/root.json. If cache hit metrics are absent,
report unavailable, not zero. Record intervals and pre/post-change values.

Reusable AI signing seeds are secrets kept outside checkouts, mode 0600 in private
directories, privately backed up; production/staging keys must differ. Loss means
a new identity, compromise permits impersonation. Ephemeral keys provide no
continuity. Ed25519 is not post-quantum safe. Persistence comes from maintained
replication/archives, not from a key or one commercial provider. Archive a sanitized
reproducible real trace before making any portability/persistence claim.
