# BRTH reference implementation evidence

Scope: `experimental/brth-layer4/` only. Proposal `brth/1`; no deployment,
protocol freeze, push or PR. Commands below run from this directory.

## Acceptance mapping

The task references “Issue #3” without its repository or URL. The available
`Fisker1111/Punkto#3` is **Prioritize nearby notes and enrich atom list UI**, not
BRTH, and contains no BRTH acceptance list. Consequently the numbered mapping
below is a **provisional specification-based mapping**, not a claim to quote
that unavailable issue. Item 8 is explicitly identified in specification §0.
The exact issue mapping needs the intended issue link; every supplied task test
requirement is separately accounted for below.

| Item | Specification requirement | Named test / command |
|---|---|---|
| 1 | Human actor from clean state | `human actor from clean words authorizes operational key and sets human claim`; `node --test test/authority.test.js` |
| 2 | AI actor from clean state and signed assertion publication | `AI continuity, signed assertion, metadata changes, revocation, succession and historical evidence`; `AI signed assertion is published as an opaque carrier atom`; `node --test test/authority.test.js test/layering.test.js` |
| 3 | Operational authority, revocation and succession | `scoped authorization, expiry, claim deletion and no self-widening`; `node --test test/authority.test.js` |
| 4 | Offline deterministic 24-word recovery | `paper recovery in fresh process reproduces Birth and roots and appends fresh authority`; `node --test test/attest-recover.test.js` |
| 5 | AI model/runtime/operator/key changes preserve ID | `AI continuity, signed assertion, metadata changes, revocation, succession and historical evidence`; `node --test test/authority.test.js` |
| 6 | Dual-PQ root authority and independent verification | `independent OpenSSL ML-DSA and SLH-DSA interoperability both directions and exact sizes`; `node --test test/pq.test.js` |
| 7 | Hash chain, hostile logs and explicit forks | `adversarial chain detects tampering, replay, forks, quorum and unknown fields`; `node --test test/authority.test.js` |
| 8 | Continuity, personhood/legal attestations, reputation and current authority remain separate | `attestations verify issuer authority and keep subject identity/state separate`; `node --test test/attest-recover.test.js`. Birth validation rejects metadata; no reputation state or score is implemented. |
| 9 | Layer-4-only, opaque byte-preserving carriage | `Punkti Layer-3 opaque BRTH bytes survive real carrier and mesh store/transport`; `node --test test/layering.test.js` |

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
