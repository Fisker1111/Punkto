# Findings

## 1. Demonstrated implementation defects

None demonstrated in the exercised scenarios. The two failing assertions were test-design
defects: partition warm-up assumed an unrequested C sync, and slow-peer failure
assumed a timeout-specific error string. Neither required implementation changes.

Warm-up now explicitly schedules B then C. Healing schedules B then C for up to
two rounds, records the rounds needed, and checks all three exact admitted sets.
The partition must fire on both outbound links; the isolated store remains
unchanged at 40 records. One test repeats the scenario three times with fresh
runners and compares status, admitted sets and store sizes, excluding transport
request counts. Slow-peer cases require failure in under 20 seconds, an empty
valid/candidate store and log, and successful follow-up convergence. Evidence
retains exact error payloads for each initiator rather than normalizing them.

Verification completed twice using real loopback TCP, without implementation
changes. Each run passed **30 hostile + 27 reference + 23 clean-room + 13 interop
= 93 tests**, with **0 failures, 0 errors and 0 skips** (186 test executions total).
Each hostile run covered 32 scenario executions. In each run the three fresh
partition repetitions were identical in status, admitted sets and store sizes:
40 records before/during isolation, then 95 records at each of three nodes after
one healing round. Both outbound partition proxies recorded injected failures.
The exact counts, durations and determinism outcomes are committed in
[`verification.json`](../evidence/verification.json); the two full capture files
contain the second run. No browser/UI verification applies to this loopback-only
harness; no deployment or production-network testing was performed.

## 2. Transport behaviours not defined by Mesh

Quotes below are from [PUNKTI_0_6_MESH.md](../../../../docs/proposals/PUNKTI_0_6_MESH.md).
These are test assumptions or narrow experimental policies, not newly imposed
protocol requirements.

- Scheduling and convergence rounds. Spec: “The caller controls scheduling.”
  Also: “Multi-hop convergence requires repeated fair peer exchanges, eventual
  delivery, compatible scopes/resource policies and retained records.”
  Tests schedule B then C explicitly, with at most two healing rounds for this
  topology; peer iteration order and a one-call global convergence guarantee
  are unspecified. Proposed clarification: “No peer iteration order or fixed
  round count is guaranteed; callers must fairly schedule each participating
  node until the required local convergence condition is observed.”
- Failure deadline. Spec: “Periodic `sync_known()` retries configured peers,
  reporting unavailable peers.” No timeout or retry interval is given. Tests
  use faults exceeding the implementations' approximately five-second waits
  and require each failing call to return within 20 seconds.
  Proposed clarification: “Implementations should bound peer operations with
  documented deadlines; timeout and retry intervals are local policy.”
- peer-error taxonomy is unspecified (timeout vs unreachable vs malformed).
  Spec only defines HTTP status classes: “Bad requests return HTTP 400; resource
  refusals return 413 with kind=`resource`, not an invalid-atom classification;
  unreachable callbacks return 502.”
  The clean-room returns a peer/unreachable-or-malformed error where the
  reference surfaces a timeout-like string. The exact observed RPC/HTTP payloads
  are in `notes.timeout_error_shapes` for both initiators.
  Proposed clarification: “Peer failure payload wording and taxonomy are
  implementation-defined; consumers must not infer retry safety from strings.”
- Interrupted/corrupt page admission. Spec: “Pull checkpoints advance only after
  an entire page is processed.” Also: “Only VALID enters the main store.”
  The tests pin no admission from the particular truncated or invalid-JSON page,
  retention of completed prior pages, and retry from the prior checkpoint.
  They do not prove general transactional rollback for a valid JSON page with
  mixed valid/invalid items; the specification does not define that atomicity.
  Proposed clarification: “An incomplete HTTP body or invalid JSON page must
  not advance the checkpoint or admit records from that undecodable page;
  previously completed pages remain admitted.”

Lost acknowledgments, duplicate admission, reordered batches and epoch replacement
are exercised as existing claims, not ambiguities: “Admission is idempotent”,
“Retries may repeat candidates”, and “A changed store epoch or changed scope
requires a new null cursor.” No broader exactly-once transport claim is made.

## 2b. Adversarial protocol findings (308 cases, 282 AGREE)

`evidence/protocol.json` records every case for both implementations. Tally:
reference 141 AGREE / 13 DIVERGE / 0 DEFECT; clean-room 141 AGREE / 11 DIVERGE / 2 DEFECT.
`DIVERGE` means both behaviours are defensible under the current text; `DEFECT` marks
where this suite's reading of the brief (`Reject lo >= hi`) is not met. No case
produced a wrong atom in a valid store, a forged record admitted, a valid record
suppressed, or a crash.

The 14 distinct cases behind the 26 non-AGREE rows:

| Case | Reference | Clean-room | Gap and minimal clarification |
|---|---|---|---|
| `t: -0` JSON | VALID | rejected | Reset says “fractional/exponent spellings rejected” and C uses minimal unsigned decimal, but does not name `-0`. Clarify: “`-0` is a non-canonical timestamp spelling and MUST be rejected on JSON import.” Wire/C unchanged. |
| corrupt opaque transport digest | HTTP 400 for the request | per-record `INVALID-structural` | PUSH is specified as per-record results, but a wrapper-level digest is not record content. Clarify: “A transport-descriptor failure (declared `sha256` mismatch) is a request error (400); content failures inside `record` stay per-record.” |
| declared address mismatch | HTTP 400 | per-record `INVALID-structural` | Same class as above. Same clarification: wrapper/descriptor errors are request-level. |
| page `limit: 33` | 400 | 413 `kind=resource` | The spec bounds pages but does not say whether an over-limit request is a bad request or a resource refusal. Clarify: “A page limit above the receiver's advertised `page` limit is a resource refusal (413), not an invalid request.” |
| initial MID cursor | `["", ""]` | `null` | Both are self-issued opaque tokens, but the first token differs on the wire. Clarify: “The initial MID `after` value is `null`; clients MUST echo a returned token and MUST NOT construct one.” |
| MID `lo == hi` / `lo > hi` | 400 | 200, empty page | Half-open bounds imply an empty interval, but rejection is not mandated. Clarify: “`lo >= hi` MUST be rejected as a bad request.” Then both implementations must change together; this is the only behaviour change proposed. |
| spatial equal/reversed `h` bounds | 400 | accepted, matches nothing | Same policy question as MID bounds. Clarify: equal or reversed spatial/Z bounds MUST be rejected rather than silently matching nothing, because an empty result is indistinguishable from “no data” for freshness reasoning. |
| spatial equal/reversed `z` bounds | 400 | accepted, matches nothing | Same clarification as above. |
| `hello.limits` member names | `body/record/page/http/candidates` | adds `batch/query_bytes/references/relation_bytes` | The spec lists admission limits but not the `hello` schema. Clarify: either publish a normative `limits` member table or declare `limits` informational and non-negotiable. |
| poisoned discovery hint | `KeyError` escapes `discover()` | `PeerError('hello-shape')` escapes | Both raise; no node death and the store is unchanged. Clarify: “Discovery hints are untrusted; a malformed hint MUST be skipped without aborting the caller's sync loop.” |

Admission under readonly/unknown conditions stayed correct across all 308 cases:
unknown algorithms were preserved as `UNVERIFIABLE-alg` candidates, unsupported
versions stayed opaque, forged signatures never entered `state.valid`, and no
candidate leaked into the valid store.

## 3. Implementation source unchanged

All additions are the hostile test harness, tests, documentation and JSON
evidence. The experiment-local `.gitignore` excludes `__pycache__/` and
explicitly retains `evidence/*.json`. The root `.gitignore` is unchanged.

The protected-path diff-stat check is:

```sh
git diff HEAD --stat -- experimental/punkti-v0.6-mesh/src experimental/nairobidot-l3 docs/proposals
```

Expected and verified before commit: empty output (0 files changed).
The interop suite's incidental `interop_report.json` rewrite is restored.
The intended commit scope is only `experimental/punkti-v0.6-hostile/**`.
No reference or clean-room implementation source, baseline test or proposal
was modified.
