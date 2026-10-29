# Stage 0 reference client

This is a **scripted harness**, not a blind-AI experiment. Genuine blind-agent evidence lives in **Hermes' separate cold-agent archive**; #32 must not cite these scripted runs as independent agents. This is Stage 0 development evidence, not a live public-network experiment and not a deployment. Nothing is published to a shared host.

Node 20.19+/22+ and Python with the repository's existing `cryptography` and `PyYAML` dependencies are required. No package install, build step or new dependency is needed.

## One local runnable path

From the checkout root:

```sh
node pwa/test-ai-first-agent.mjs
```

This starts two `python3 -m punkti_node` processes on separate ephemeral loopback ports, with separate temporary data directories. Each advertises both nodes, with local IDs chosen so the frozen node's ID-sorted bootstrap puts itself first. The test maps `/ai` to the new entrance only in temporary configuration; `/ai-first/` serves the same page. The existing `pwa/ai.html` stays untouched. All temporary keys and stores are removed on exit. HTTP URLs/statuses, real MIDs, hashes, heads, sequences and public keys are printed; secret keys are never printed.

The harness uses explicit static-publication pulls. The frozen runtime's `sync_known()` loop uses mesh `connect()`, not `replicate_publication()`. To avoid introducing a new runtime behavior or simultaneous datastore writers, the harness stops the receiving process, calls the existing `PersistentNode.replicate_publication(peer_publication_base)` with its unchanged configuration, closes its store, and restarts the real runtime. The other node remains serving real HTTP. It repeats this in reverse for the reply. This proves byte-identical import, republishing and rereading through the frozen static GET path; it does **not** prove automatic background static replication. No new API is added.

## Client commands

Against a local node you are already running, set `NODES` to its printed nodes.json URL, and `KEY_FILE` / `SECOND_KEY_FILE` to private paths outside any checkout. The first advertised node is selected, including for writes; configure local node IDs so the other node sorts first to inspect its view independently.

```sh
node pwa/ai-first/agent.mjs --help
node pwa/ai-first/agent.mjs boot --nodes "$NODES"
node pwa/ai-first/agent.mjs discover --nodes "$NODES" --xy u3 --limit 10
node pwa/ai-first/agent.mjs publish --nodes "$NODES" --h u3butz7k9q_23 --text 'Chosen destination' --key-file "$KEY_FILE"
node pwa/ai-first/agent.mjs publish --nodes "$NODES" --lat 55.6761 --lon 12.5683 --height 23 --text 'Chosen coordinates' --key-file "$KEY_FILE"
node pwa/ai-first/agent.mjs verify --nodes "$NODES" --mid "$MID" --h u3butz7k9q_23
node pwa/ai-first/agent.mjs reply --nodes "$NODES" --parent-mid "$MID" --text 'Same exact point' --key-file "$SECOND_KEY_FILE"
```

Set MID from the publish result. Coordinate and explicit-address examples choose an ellipsoidal height; they do not measure it. Never guess Z. Height strings retain their exact decimal value. Reply reads and verifies the parent and copies the exact h, with `refs: [{target: parentMID, rel: "reply"}]`. A cross-address override is rejected. Omit `--key-file` only for a labelled ephemeral identity with no continuity. See [key format](keys.md.example).

JSON results use stdout; every HTTP request and response summary uses stderr. Exit 1 denotes a command error, failed verification, or a MID absent from the current publication (explicitly reported as publication lag or absence from that node view). Reads use the frozen reader. Discovery counts all traversed leaf entries by XY prefix before applying the candidate limit, including entries whose provenance is not valid; `rejected` reports reader rejection count. Counts are occupancy, not trusted authorship. The old fixture's nonspatial entry is excluded from candidates/counts; no new nonspatial atom is created. Prefix/limit currently filter output, not network traversal, so this is not a scale optimization.

The root and bootstrap are mutable and unauthenticated. Immutable manifests, shards, packs and records are digest checked. Verify reports SHA-256, canonical-body MID, signature and exact-h checks; failure to traverse a corrupt publication is a publication verification failure. No trust/completeness claim follows from matching hashes.

## Client-only cold start and evidence

```sh
pwa/ai-first/coldstart.sh "$NODES"
```

Its only argument is the local nodes.json URL. It creates a fresh `/tmp` directory, downloads only the entrance, client and frozen client dependencies over HTTP, then runs boot → discover → publish → verify there, with no checkout or package installation. A discovered exact h is chosen; an empty publication uses the explicitly stated harness destination `u3butz7k9q_23`. This is scripted selection, never a measured elevation or presence claim. Keys are mode 0600, outside the repository, deleted on exit. Every HTTP request/response summary is printed. Stage 0 enforces 127.0.0.1 and refuses redirects, including advertised endpoints; future staging requires separate authorization and removal of this deliberate guard. Downloaded executable code is trusted only because this run uses the operator's local server, not because bootstrap authenticates it.

To retain a sanitized reproducible real transcript outside the checkout:

```sh
node pwa/test-ai-first-agent.mjs > /tmp/punkti-stage0-transcript.txt 2>&1
```

The transcript contains local URLs, public keys, hashes and scripted payloads, no seed/private key. Ports, timestamps, keys and MIDs vary on each run. A captured roundtrip excerpt is in [the walkthrough](../../docs/AI_FIRST_WALKTHROUGH.md). Archive the full log with the reviewed commit SHA for #32; the genuine blind-agent archive is separate.

## Limits

Success proves the tested local static read → canonical signed write → verification → explicit replication → differently keyed same-h reply path. Both nodes use the same implementation; this is not independent implementation conformance, a blind-AI trial, public-network propagation, crash recovery, load testing, or human UI acceptance. Publication can lag signed acceptance. There is no global coverage, guaranteed persistence, guaranteed propagation, physical-presence proof, payload-truth proof, or post-quantum security for Ed25519. Persistence requires maintained replication and archives; losing a key loses that identity. The full spatial-only protocol re-freeze remains #30's work.
