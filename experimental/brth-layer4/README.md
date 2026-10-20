# BRTH Layer-4 reference implementation

An isolated, executable implementation of the **`brth/1` review draft** in
[BRTH_LAYER4_SPEC.md](docs/BRTH_LAYER4_SPEC.md). This is a proposal, not a frozen
protocol or production identity wallet. It changes no Punkti carrier, app,
relay, server or deployment code.

## Run

Use Node.js 26. The only direct npm dependency is pinned to
`@noble/post-quantum@0.7.1`; the lockfile pins its transitive dependencies.
Python 3 with `cryptography` is required for the existing carrier proof.
OpenSSL 3.5 with ML-DSA-87 and SLH-DSA-SHAKE-256s provides independent
cross-checks and faster SLH signing.

```sh
cd experimental/brth-layer4
npm install && npm test
node tools/gen-vectors.js
git diff --exit-code -- vectors/
```

Installation downloads dependencies. The implementation, vector generation and
tests make no network calls. The BIP-39 English wordlist is bundled. Tests use
published test entropy, explicit timestamps and deterministic signatures.
The slower tests deliberately exercise noble SLH signing, including an absent
OpenSSL binary. Allow several minutes for the complete suite.

## API and local representations

`require('./src')` exports the required APIs, mnemonic helpers, and root signer
adapters. Binary inputs/outputs are `Uint8Array`/`Buffer`; public wire fields
are unpadded base64url. Signers are `{alg, pk, sk}` with binary key material.
ML private keys may be 32-byte keygen seeds or expanded noble secret keys;
SLH private keys are the 128-byte FIPS private encoding. OpenSSL's ML import
bridge takes the 32-byte seed.

```js
const brth = require('./src');
const words = brth.newWords(); // CSPRNG; keep private, never log or publish
const roots = brth.deriveRootKeys(brth.wordsToEntropy(words));
const birth = brth.buildBirth(roots);
const identityId = brth.identityIdOf(birth);
const log = brth.newLog(birth);
```

- `encode`, `decode`, `digest`: canonical JSON and SHA3-256. `decode` accepts
  bytes only and rejects any byte sequence other than the canonical encoding,
  including duplicate members. Encoding normalizes strings and member names to
  NFC, rejects normalization collisions, and orders names by Unicode code point.
  C0 hexadecimal escapes use uppercase digits, as `\u00XX` in the draft.
  Duplicate members already discarded by an external JSON parser cannot be
  recovered: ingest wire bytes with `decode`, not `JSON.parse`.
- `buildBirth(roots)` accepts the result of `deriveRootKeys`, or the two public
  `{alg, pk}` records. Birth has no identity metadata or private material.
- A log is `{birth, events}`. `append(log, op, body, signers, {iat})` validates
  and appends atomically; failed appends leave the log unchanged. The explicit
  fifth argument supplies the signed timestamp omitted from the task's short
  API sketch. No clock is read implicitly.
- `verifyEvent(event)` validates the standalone envelope, operation body and
  signature encodings. An event contains key identifiers, not verification
  keys, so **cryptographic authority verification requires `deriveState(log)`**.
  `signEvent` constructs a signed event without claiming authority; `append`
  and replay enforce the previous state, complete quorum and chain.
- `deriveState(log, {untilSeq})` evaluates a sequence prefix. Returned `seq`
  identifies the historical evaluation point. `keys` is a key-ID-indexed object,
  with expiry retained for checks against a signed `iat`; `revoked` tracks
  predecessor IDs for succession after explicit revocation. `partial: true`
  always warns that a supplied public log cannot prove it is the latest global
  history. Missing requested history is `BROKEN`. Valid competing events produce
  `CONFLICTED` and retain the last uncontested state. Exact duplicate records
  are rejected as replay. Fork resolution is not implemented.
- All supplied signatures must verify and be authorized. Root authorization is
  always both families; operational authorization requires ML-DSA and may add
  an authorized SLH co-signature. A signing operational key cannot increase its
  own scopes or extend its own expiry. Succession may name an already revoked
  predecessor. Root rotation uses the policy before the rotation event.
- `buildAttestation(input, signers)` and `verifyAttestation(obj, issuerLog,
  {atIat})` use only issuer authority. The optional `atIat` must equal the signed
  timestamp. Verification returns the evaluated `seq`. Because signed times
  are untrusted, regressing issuer timestamps make time-based evaluation
  ambiguous and are rejected; equal timestamps include all events at that
  second. Sequence replay itself does not impose timestamp monotonicity.
- `recoverFromWords(words, {head, iat})` takes the public **log** as `head`, or
  `null` for an empty history. This allows checking forks, identity and current
  root policy before signing. It returns the requested Birth, ID, root keys and
  recovery event, plus the fresh `operationalKey` for local custody. Only publish
  `recoveryEvent`. For deterministic tests only, `operationalSeed` can supply a
  fixed 32-byte seed; normal recovery uses a CSPRNG. Original words rebuild the
  original Birth after root rotation but cannot authorize under a replaced
  root policy. Recovery rejects that case.

These choices fill in local API details; they introduce no additional BRTH wire
fields. `src/format.js` supplies common strict schema helpers; `src/mnemonic.js`
implements BIP-39 transcription without PBKDF2 or a passphrase.

## Layering proof

`test/layering_runner.py` imports the real
`../punkti-v0.6-mesh/src/carrier.py` and `mesh.py`, with bytecode writing disabled.
Node constructs a Birth and a signed AI assertion, wraps each as
`x = "brth/1:" + CJSON(object)`, and signs the outer `punkti/0.6` atom with a
separate deterministic Ed25519 fixture using Node crypto.

The runner checks the carrier's canonical body and complete framed record,
parses them, stores the record in a real mesh `Node`, serializes a paginated
transport response, and admits it to another real `Node`. The complete record,
canonical body and UTF-8 `x` must remain byte-identical. Invalid BRTH text also
round-trips as opaque carrier payload. This tests actual store/transport
serialization without opening sockets or contacting peers. It does not claim
an HTTP/network deployment test.

## Evidence and limits

| Property | Evidence |
|---|---|
| Exact canonical encoding and mnemonic checksum | `test/cjson.test.js` |
| Deterministic roots, Birth and ID | `test/vectors.test.js`, `vectors/*.json` |
| Human/AI continuity, scopes, succession, root rotation, attacks | `test/authority.test.js` |
| Historical attestation authority and paper recovery | `test/attest-recover.test.js` |
| Independent PQ implementations and noble fallback | `test/pq.test.js` |
| Existing carrier and mesh byte preservation | `test/layering.test.js` |

See [EVIDENCE.md](EVIDENCE.md) for commands, measured results and the acceptance
mapping, and [vectors/README.md](vectors/README.md) for regeneration.

The threat model and non-guarantees are in specification §§10–11. BRTH proves
continuity of control, not personhood, truth, legal identity, reputation or
freshness. Claims remain self-assertions; third-party attestations are separate
objects and change no subject state. No global reputation or trust score exists.

Recovery phrases and private keys are bearer secrets. This reference returns
private buffers for local use and does not promise secure deletion in a
JavaScript garbage-collected runtime. OpenSSL operations use private temporary
files under ignored `.tmp/`, removed in `finally`. Only published test-derived
public vectors are committed; the fixtures must never secure a real identity.
