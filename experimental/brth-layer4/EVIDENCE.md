# BRTH reference implementation evidence

Scope: `experimental/brth-layer4/` only. Proposal `brth/1`; no deployment,
no protocol freeze, no PR, no change outside this directory.

## Acceptance mapping — GitHub Fisker1111/CEO-OS Issue #3

Issue #3 requires a return to Founder review with nine items. Each item is mapped
to a named test in this checkout (branch `proposal/brth-layer4`):

| # | Issue #3 acceptance item | Evidence |
|---|---|---|
| 1 | Concise Layer-4 BRTH specification | `docs/BRTH_LAYER4_SPEC.md` — 12 sections; declares the four separated concerns, the authority log, recovery and the L3/L4 boundary |
| 2 | Deterministic independent vectors/tests | `test/vectors.test.js` against committed `vectors/root.json` + `vectors/birth.json`; `test/cjson.test.js`; `test/authority.test.js` — every seed, word list and `iat` pinned; no wall clock, no network |
| 3 | Real dual-PQ verification, not toy signatures | `test/pq.test.js` — FIPS 204 ML-DSA-87 (pk 2592 / sig 4627) and FIPS 205 SLH-DSA-SHAKE-256s (pk 64 / sig 29792), noble ↔ OpenSSL 3.5.5 in **both** directions for both families |
| 4 | One human actor and one AI actor from clean state | `human actor from clean words authorizes operational key and sets human claim`; `AI continuity, signed assertion, metadata changes, revocation, succession and historical evidence` |
| 5 | Operational key authorization + revocation/succession | `scoped authorization, expiry, claim deletion and no self-widening`; `root rotation uses prior dual policy, preserves ID and rejects old roots`; succession/revoke assertions inside the AI-continuity test |
| 6 | Deterministic recovery from the 24-word secret path | `paper recovery in fresh process reproduces Birth and roots and appends fresh authority` — recovery runs in a **separate Node process** from the same 24 words and reproduces byte-identical Birth, roots and `IdentityID` |
| 7 | AI runtime/model change does not change `IdentityID` | AI-continuity test changes `model.version`, `runtime` and `operator`, then revokes and succeeds the operational key, asserting the `IdentityID` is unchanged throughout |
| 8 | Clean separation of continuity / personhood / reputation / current authority | `attestations verify issuer authority and keep subject identity/state separate` — continuity = Birth + chain; personhood/legal = third-party `brth.attest`; current authority = derived from the log only; **no reputation state or score exists in the identity model** |
| 9 | No Punkti Layer-3 semantic dependency on BRTH | `Punkti Layer-3 opaque BRTH bytes survive real carrier and mesh store/transport` — real `carrier.py` + `mesh.py` nodes preserve atom bytes and `x` exactly, and also round-trip deliberately invalid BRTH text; no file outside `experimental/brth-layer4/` changed |

Item 8's reputation component is demonstrated by absence: `deriveState` exposes
only root, keys, claims and chain position. Reputation is left to L4 consumers
over signed history and attestations, as specified in §§0 and 11.


## Full task coverage

| CODEX_TASK test requirement | Evidence |
|---|---|
| 1 CJSON | Two named CJSON tests: ordering, normalization, escaping, duplicate members, numbers, invalid Unicode/types and round trips |
| 2 Mnemonic | Published all-zero/all-one 24-word BIP-39 vectors; invalid checksum and 23/25 words |
| 3 Root vectors | Both algorithms' complete public-key hex compared against committed JSON |
| 4 Birth/ID vectors | Complete canonical Birth hex and full IdentityID compared against committed JSON |
| 5 Human | Clean phrase → Birth → dual-root authorize → human claim |
| 6 AI | Clean deterministic Birth → authorization → five claims → signed assertion in real carrier atom |
| 7 AI continuity | Three metadata changes, explicit revoke then succession, stable ID, rejected retired signer and valid historical signature/attestation |
| 8 Succession/revocation | Predecessor handling, new key, self-scope/expiry widening rejection, expiry, claim deletion |
| 9 Root rotation | Prior dual-root quorum, unchanged ID, rejected old roots, accepted new roots |
| 10 Recovery | Separate Node process, same roots/Birth/ID, fresh deterministic test operational key against existing head; absence of words/raw entropy/hex/base64url entropy in public output and vectors |
| 11 Attestations | Valid issuer, tampering, unauthorized signer, wrong issuer, historical validity and unchanged subject log/state |
| 12 Adversarial log | Tamper, wrong prev, duplicate seq, replay, genuine fork in either input order, partial quorum, unauthorized key, unknown operation/fields/types and missing history |
| 13 Layering | Real Python carrier + real mesh store and serialized paginated transport/admission; full record/body/x equality; opaque non-JSON BRTH text |
| 14 Cross implementation | Same-seed native public keys; noble→OpenSSL and OpenSSL→noble signatures for both families; deterministic signatures also equal |
| 15 Large/slow | Native and noble SLH signatures 29792 bytes, ML signatures 4627 bytes; public keys 64/2592 bytes; forced missing-OpenSSL fallback |

## Verification results

Final commands, test counts and vector regeneration results are recorded below. Test cases have no console output of their own.
The Node test runner emits names and results. Independent checks skip only if
OpenSSL lacks SLH-DSA; on this machine both algorithms must run.

Manual inspection covers strict schemas, signing domains, HKDF labels, root
quorum, sequence evaluation, secret/public separation and the scope of the Git
diff. No browser or live deployment test applies to this isolated library.

Environment: Node.js `v26.9.0`, npm `12.0.2`, OpenSSL `3.5.5` (27 Jan 2026),
Python `3.14.7`, `cryptography==50.0.1`.

- `npm install`: exit 0; 5 packages audited, 0 vulnerabilities.
- `node tools/gen-vectors.js`: exit 0. After staging the generated vectors,
  `git diff --exit-code -- experimental/brth-layer4/vectors/` from repository
  root exited 0 with **empty output** after regeneration (byte-identical).
- `node --check` on all 19 JavaScript files in `src/`, `tools/` and `test/`:
  all exited 0.
- `git diff --cached --check`: exit 0.
- Staged-file inspection: all 29 changed files are inside
  `experimental/brth-layer4/`; existing carrier/mesh files are unchanged.

Final `npm install && npm test`: **exit 0**, 18 tests passed, 0 failed,
0 cancelled, 0 skipped, 0 todo. Both independent OpenSSL algorithm checks
ran (no skips), and the forced absent-OpenSSL noble fallback passed.

```text
ℹ tests 18
ℹ suites 0
ℹ pass 18
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 201710.822649
```

## Independent verification (Hermes, separate from Codex)

Re-run by the Hermes worker on this branch, not trusted from the implementation
report:

- `npm test` re-executed: **18/18 pass, 0 fail, 0 skipped**, ~188 s.
- `node tools/gen-vectors.js` re-executed, then `git status --short`: empty —
  committed vectors reproduce byte-identically.
- Vector independence: a throwaway Python/HKDF-SHA-512 + `cryptography`
  ML-DSA-87 re-derivation from the published test entropy reproduced the
  committed `mlPkHex` **and** recomputed `identity_id` as
  `"b1:" + base32(sha3_256(cjsonHex))` for both committed cases — matching
  `vectors/birth.json` exactly (`b1:n4xq6w26e76t5acvynw7dsf6c53pm6nc2detgqihszkcjqkvweja`,
  `b1:fstdyaokzqulhvx7ust7h6jcnj4vem3kc7fges3dh2ac5eo22dna`).
- Diff scope checked: every changed file is under `experimental/brth-layer4/`;
  the Punkti carrier/mesh sources are untouched (used read-only by the
  layering test).

