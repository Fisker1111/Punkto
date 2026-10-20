# Codex task — BRTH Layer-4 reference implementation + evidence

You are implementing the proposal in `docs/BRTH_LAYER4_SPEC.md` (same directory,
authoritative). Read it fully before writing code. Implement ONLY `brth/1` as
specified. Do not redesign, do not extend scope, do not touch anything outside
`experimental/brth-layer4/`.

## Base / isolation

- Repository: `/home/hermes/.hermes/kanban/workspaces/t_6c8111f8/punkto`
- Branch (already checked out): `proposal/brth-layer4`
- Nothing outside `experimental/brth-layer4/` may change. No Punkti core edits,
  no deployment, no protocol freeze, no PR #111 changes.

## Toolchain (already verified on this machine, use exactly this)

- Node.js v26.
- `@noble/post-quantum@0.7.1` — deterministic FIPS 204 / FIPS 205 keygen:
  - `ml_dsa87.keygen(seed32)` → `{secretKey, publicKey}` (pk 2592 bytes)
  - `slh_dsa_shake_256s.keygen(seed96)` → `{secretKey 128, publicKey 64}`
  - signing API order is `sign(message, secretKey)`, `verify(sig, message, pk)`
  - ML-DSA options `{ extraEntropy: false }` for deterministic signatures.
  - Import paths: `@noble/post-quantum/ml-dsa.js`, `.../slh-dsa.js`.
- OpenSSL 3.5.5 CLI has native `ML-DSA-87` and `SLH-DSA-SHAKE-256s`
  (OIDs `2.16.840.1.101.3.4.3.19` and `...3.30`). Use it as the **independent
  implementation** for cross-checks and as the fast SLH-DSA signer.

Verified facts you may rely on (do not re-derive from scratch):

- `cryptography` Python 3.14 `cryptography==50.0.1` exposes
  `mldsa.MLDSA87PrivateKey.from_seed_bytes(seed32)` and produces the **same**
  public key as noble for the same seed.
- An SLH-DSA private key can be imported by OpenSSL as DER:
  `SEQUENCE { INTEGER 0, SEQUENCE { OID 2.16.840.1.101.3.4.3.30 },
   OCTET STRING(128-byte FIPS 205 sk = seed‖prf‖pubseed‖root) }`.
  OpenSSL derives exactly noble's 64-byte public key from it.
- Public key DER: `SEQUENCE { SEQUENCE{OID}, BIT STRING(0x00 ‖ 64-byte pk) }`.
- `openssl pkeyutl -sign|-verify -rawin` with that DER works; noble verifies
  OpenSSL's SLH signature and OpenSSL verifies noble's. OpenSSL sign ≈ 3.2 s,
  noble sign ≈ 35 s, verification is milliseconds. Use OpenSSL for SLH signing
  in tests to keep the suite fast, but the implementation MUST also work with
  noble as fallback when OpenSSL is absent (use noble then, slower).

## Deliverables (all under `experimental/brth-layer4/`)

```
package.json            (private, type: commonjs, deps pinned @noble/post-quantum 0.7.1)
src/cjson.js            canonical encoding + strict validator
src/keys.js             root derivation, keygen, sign/verify, kid
src/birth.js            Birth object + IdentityID
src/authority.js        event construction, append, replay/derive state
src/attest.js           attestation object + verification against issuer log
src/recover.js          phrase -> root -> birth -> recovery event
src/index.js            public API exports
tools/pq-openssl.js     DER builders + openssl sign/verify bridge + capability probe
tools/gen-vectors.js    regenerates vectors/*.json deterministically
test/*.test.js          node:test suite (node --test)
vectors/*.json          committed deterministic golden vectors
vectors/README.md       what each vector pins and how to regenerate
README.md               how to run, threat model pointer, evidence table
EVIDENCE.md             per-acceptance-item evidence with exact commands/results
```

Add `.gitignore` for `node_modules/`.

## Required API (keep it small and testable)

```js
// cjson.js
encode(value) -> Buffer            // throws on floats, duplicate keys, bad types
decode(buf) -> value               // strict: rejects non-canonical input
digest(value) -> Buffer            // SHA3-256(encode(value))

// keys.js
deriveRootKeys(entropy32) -> { ml: {pk, skSeed}, slh: {pk, sk}, kid(pk,alg) }
kidOf(alg, pkBytes) -> "k:..."
keyId(alg, pk) -> ...
sign(alg, sk, msgBytes, {deterministic}) -> sigBytes
verify(alg, pk, msgBytes, sigBytes) -> bool

// birth.js
buildBirth(rootPublicKeys) -> birthObject
identityIdOf(birth) -> "b1:..."
validateBirth(obj) -> {ok, errors}

// authority.js
newLog(birth) -> Log
append(log, op, body, signers) -> event        // validates authority + chain
deriveState(log, {untilSeq}) -> {status, root, keys, claims, seq, headHash, fork}
verifyEvent(event) -> {ok, errors}
signEvent(eventWithoutSigs, signers) -> event

// attest.js
buildAttestation({subject, issuer, claim, iat, ref}, signers) -> obj
verifyAttestation(obj, issuerLog, {atIat}) -> {ok, reasons}

// recover.js
recoverFromWords(words, {head, iat}) -> {birth, identityId, rootKeys, recoveryEvent}
```

Keep functions pure where possible. No global mutable state. All object
validation must reject unknown fields and wrong types.

## Tests — must all pass and be deterministic

Use `node:test`. Fixed seeds/words. No network. No wall-clock dependence
(pass `iat` explicitly). Every test prints nothing unless it fails.

1. **cjson**: key ordering, NFC, escapes, integer-only, reject float/duplicate
   key/NaN/unknown; round-trip `decode(encode(x))`.
2. **mnemonic**: fixed entropy → 24 known words → back; reject bad checksum and
   23/25 words. Include the BIP-39 English wordlist in
   `src/wordlist-en.js` (2048 words) so tests run offline.
3. **root vectors**: fixed entropies → exact `pk` hex for ML-DSA-87 and
   SLH-DSA-SHAKE-256s; assert against committed `vectors/root.json`.
4. **birth/id vectors**: fixed entropy → exact `CJSON(birth)` hex and
   `identity_id`; committed `vectors/birth.json`.
5. **human actor from clean state**: new 24 words → birth → authorize op key
   (root 2-of-2) → `claim.set` `actor.kind=human` → state OK.
6. **AI actor from clean state**: new 24 words → birth → authorize op key →
   claims `actor.kind=ai`, `model.family`, `model.version`, `runtime`,
   `operator` → publish signed assertion atom → state OK.
7. **AI continuity**: change `model.version`, `runtime`, and `operator` claims,
   then `succeed` to a brand-new operational key after revoking the old one.
   Assert: `IdentityID` identical at every step, old key rejected afterwards,
   chain still `OK`, historical pre-revocation signature still verifies.
8. **succession + revocation**: revoke then attempt to sign → rejected; `succeed`
   `from`/`to` semantics; a key cannot widen its own scopes (`authority`).
9. **root rotation**: new root policy signed by old 2-of-2; afterwards old roots
   cannot rotate again; `IdentityID` unchanged.
10. **recovery**: same 24 words in a fresh module instance → identical birth
    bytes, identical `identity_id`, identical root public keys. Then recovery
    authorizes a fresh key against the existing head; resulting state verifies.
    Also assert the 24 words / entropy bytes appear nowhere in any produced
    BRTH object or vector.
11. **attestations**: issuer log verifies attestation; tampered claim fails;
    attestation from an unauthorized issuer key fails; attestation does not
    change subject `identity_id` or state.
12. **adversarial log**: tampered event body, broken `prev`, duplicate `seq`,
    replay of an old event, two events with same `seq`+`prev` → `CONFLICTED`,
    1-of-2 root quorum rejected, signature by unauthorized key rejected,
    unknown `op` rejected, unknown field rejected.
13. **Punkti layering (byte-for-byte)**: import the real carrier from
    `../punkti-v0.6-mesh/src/carrier.py` (it is on this branch) via a small
    Python runner `test/layering_runner.py` invoked from a `node:test` case:
    build a BRTH birth in Node, put `x = "brth/1:" + CJSON(birth)`, build a
    `punkti/0.6` atom with `alg=ed25519` (generate an Ed25519 key with node
    `crypto`), canonicalize, parse back with the Python carrier, assert:
    - `x` byte-identical and prefix intact,
    - carrier never parses BRTH (payload remains opaque),
    - atom round-trips through the mesh store/transport with the same bytes.
    If the mesh API needs `h`/refs, use `h=""` and `refs=[]`.
14. **cross-implementation PQ**: ML-DSA-87 noble↔OpenSSL both directions
    (same seed ⇒ same pk; each verifies the other's signature). SLH-DSA-SHAKE-256s
    noble↔OpenSSL both directions. Skip with a clear message only if the
    `openssl` binary lacks SLH-DSA; otherwise it is a hard failure.
15. **large/slow check**: SLH-DSA root signature verifies through the OpenSSL
    bridge; assert signature length 29792 and ML-DSA signature length 4627,
    pk lengths 2592 / 64.

## Constraints

- Deterministic: pin every seed, word list, `iat`.
- No secrets committed: only test vectors derived from *documented published*
  test seeds; never a real recovery phrase. Mark vector seeds as
  `TEST-ONLY-NOT-A-SECRET`.
- No network calls.
- `npm test` must run `node --test test/`.
- Keep code readable and small; no frameworks beyond `node:test`.
- Fail loudly on invalid input; never silently coerce.

## Definition of done

- `npm install && npm test` passes with all tests green (report exact counts).
- `node tools/gen-vectors.js` reproduces committed vectors byte-identically
  (report the diff is empty).
- `EVIDENCE.md` maps acceptance items 1–9 from Issue #3 to a named test and the
  command that shows it.
- `README.md` explains the run and the layering proof.
- Commit everything on `proposal/brth-layer4` with a focused message, do NOT push,
  do NOT open a PR, and report the exact commit SHA plus the test summary.
