# BRTH — Layer-4 Persistent Actor Identity

**Status:** Founder review draft (proposal, not frozen)
**Layer:** Punkti Layer 4 (above the Punkti Layer-3 carrier)
**Version:** `brth/1`
**Scope:** identity continuity, authority, recovery, attestations. No Punkti Layer-3 change.

> BRTH proves **continuity of control**. It does not prove personhood, truth,
> legal identity or good behaviour.

---

## 0. Design position

| Question | BRTH answer |
|---|---|
| What persists? | An `IdentityID`, derived from an immutable, deterministic *Birth* object. |
| What changes? | Operational keys, root keys, model/runtime metadata, claims, attestations. |
| What authorizes change? | An append-only, hash-chained, signed **authority log**. |
| What is the root? | A 24-word private recovery secret that deterministically regenerates the root keypairs. |
| Who decides what an actor *is*? | Third parties, through signed attestations. BRTH only carries them. |

Four things are kept strictly separate (acceptance item 8):

1. **Identity continuity** — `IdentityID` + Birth + authority-log hash chain.
2. **Personhood / legal identity** — attestations issued by external authorities.
3. **Reputation** — derived by consumers from signed history and attestations; never
   part of identity state, never a single global score.
4. **Current authority** — *derived* from the authority log: which keys are valid now,
   with which scopes, until when.

No field in the Birth or in `IdentityID` encodes human/AI/org/sensor/robot/object,
a name, a model, a machine, an operator or a jurisdiction. Those are claims and
attestations.

---

## 1. Actors

Any of these is the *same* root mechanism with different claims/attestations:

- human, AI instance, organization, sensor, robot, physical object.

An AI actor is explicitly **not** its model family/version, not its runtime/machine,
not an operator claim and not a replaceable operational key. It may change machine,
model version or operational key while keeping its `IdentityID`, through an explicit
recorded succession.

---

## 2. Primitives

| Name | Definition |
|---|---|
| `CJSON` | BRTH canonical JSON (§3) |
| `H(x)` | SHA3-256 over raw bytes |
| `HKDF` | HKDF-SHA-512 (RFC 5869) |
| Root signature suite | **ML-DSA-87** (FIPS 204) and **SLH-DSA-SHAKE-256s** (FIPS 205), 2-of-2 |
| Operational signature suite | ML-DSA-87 (required), SLH-DSA-SHAKE-256s (optional co-signature) |
| `b64u` | RFC 4648 §5 base64url, no padding |
| `b32` | RFC 4648 §6 base32, lowercase, no padding |

All binary fields in BRTH objects are `b64u` strings. Integers are JSON integers;
floats are forbidden everywhere.

---

## 3. `CJSON` — canonical encoding

Rules (deliberately small enough to re-implement independently):

1. UTF-8, no BOM, no whitespace between tokens.
2. Object member names sorted ascending by Unicode code point.
3. Strings are JSON strings with exactly the escapes required by RFC 8259
   (`\"`, `\\`, `\b`, `\f`, `\n`, `\r`, `\t`, `\u00XX` for C0 controls).
   All other characters appear literally as UTF-8.
4. Non-ASCII strings MUST be NFC-normalized before encoding; lone surrogates rejected.
5. Numbers: integers only, no leading `+`, no leading zero (except `0`), no `-0`,
   range `-2^53+1 .. 2^53-1`. Floats, exponents and `NaN` are invalid.
6. Booleans and `null` only as literals.
7. Arrays preserve order; duplicate object keys are invalid.
8. The digest/identifier of an object is always `H(CJSON(object))`.

---

## 4. Recovery phrase and root derivation

### 4.1 Phrase

- 256 bits from a CSPRNG, encoded as **BIP-39 English, 24 words** (8-bit checksum).
- BIP-39 is used **only as a human transcription format**. No PBKDF2 wallet seed, no
  optional passphrase. The canonical secret is the 32-byte entropy itself.

### 4.2 Root keys

```text
root_entropy = bip39_decode(words)                      # 32 bytes
prk          = HKDF-Extract(salt = UTF8("BRTH/1/root/salt"), ikm = root_entropy)

ml_seed   = HKDF-Expand(prk, UTF8("BRTH/1/root/ML-DSA-87"), 32)
slh_seed  = HKDF-Expand(prk, UTF8("BRTH/1/root/SLH-DSA-SHAKE-256s"), 96)
```

- `ML-DSA-87` keypair is the FIPS 204 keygen from the 32-byte seed `ml_seed`
  (deterministic `KeyGen` with `xi = ml_seed`).
- `SLH-DSA-SHAKE-256s` keypair is the FIPS 205 keygen from the 96-byte seed
  `slh_seed` split as `SK.seed ‖ SK.prf ‖ PK.seed` (3 × 32 bytes).

Both derivations are deterministic: the same 24 words always yield the same root
public keys, on any implementation, offline.

Root private material MUST be treated as bearer secret. It MUST never appear in a
BRTH object, atom payload, log, attestation or QR intended for publication.

---

## 5. Birth object and IdentityID

The Birth is fully deterministic from the recovery phrase and fixed constants. It
contains no timestamp, name, server, operator or random value.

```json
{
  "type": "brth.birth",
  "v": 1,
  "suite": "BRTH-1",
  "root": {
    "threshold": 2,
    "keys": [
      { "alg": "ML-DSA-87", "pk": "<b64u 2592 bytes>" },
      { "alg": "SLH-DSA-SHAKE-256s", "pk": "<b64u 64 bytes>" }
    ]
  }
}
```

```text
identity_digest = H(CJSON(birth))
identity_id     = "b1:" + b32(identity_digest)        # 52 chars after the prefix
```

Properties:

- 256-bit content-derived identifier; no registry, no name authority, no collision
  authority other than the hash.
- Identical for the same words on every implementation.
- Unchanged by key rotation, succession, model change, machine change, operator
  change, attestation, reputation or time.
- Protocol comparisons use the full `b1:` identifier. UIs may show a short
  fingerprint and MUST mark it as a fingerprint.

---

## 6. Authority log

An identity's state is *derived* by replaying an append-only log of signed events.
The Birth is never edited; no event is ever deleted or rewritten.

### 6.1 Event envelope

```json
{
  "type": "brth.event",
  "v": 1,
  "id": "b1:…",
  "seq": 1,
  "prev": "<b64u H(CJSON(previous event))>" | null,
  "op": "authorize",
  "iat": 1760000000,
  "body": { },
  "sigs": [ { "alg": "ML-DSA-87", "kid": "k:…", "sig": "<b64u>" } ]
}
```

- `seq` starts at 1 and increases by exactly 1. `prev` is `null` for `seq 1` and
  otherwise the hash of the immediately preceding event **as transmitted,
  including its `sigs`** (byte-exact chain).
- `iat` is a signed Unix-seconds integer. It is *evidence*, not a trusted clock;
  BRTH never claims global ordering, freshness or that an actor was online.
- Signing bytes = `CJSON(event without "sigs")`.
- `sigs` is ordered; duplicates of the same `kid` are invalid.

### 6.2 Operations

| `op` | Authority required | Body |
|---|---|---|
| `authorize` | root 2-of-2, or an active key with scope `authority` | `{"key":{alg,pk},"scopes":[…],"not_after":int|null}` |
| `revoke` | root 2-of-2, or scope `authority` | `{"kid":"k:…","reason":str}` |
| `succeed` | root 2-of-2, or scope `authority` | `{"from":["k:…"],"to":[{alg,pk,scopes,not_after}],"reason":str}` |
| `root.rotate` | **root 2-of-2 only** | `{"root":{threshold,keys},"reason":str}` |
| `claim.set` | root, or scope `claim` | `{"claims":{…}}` |
| `claim.del` | root, or scope `claim` | `{"names":[str]}` |

Scopes are `sign`, `claim`, `authority`. `authority` may never be self-granted:
a `succeed` event cannot widen scopes of the key that signs it.

### 6.3 Key identifiers

```text
kid = "k:" + b32(H(UTF8(alg) ‖ 0x00 ‖ pk_bytes))
```

### 6.4 Derived state

Replay rules, in `seq` order:

1. `prev` MUST equal the hash of the previously accepted event; otherwise the log is
   `BROKEN` at that point and no later event is applied.
2. Signatures MUST verify against a key that is *valid for that operation at that
   sequence position*: authorized by an earlier event, not revoked earlier, not
   expired at `iat`, and holding a sufficient scope.
3. Root operations MUST satisfy the root policy in force *before* the event,
   threshold `2` over distinct algorithms, each signature from a key in that policy.
4. `authorize`/`succeed` add keys; `revoke` removes them; `root.rotate` replaces the
   root policy.
5. `claim.set` merges the given claim names; `claim.del` removes them. Claims are
   self-asserted and never authoritative about facts.
6. Two different accepted events claiming the same `seq` and `prev` constitute a
   **fork**. The state is `CONFLICTED`; consumers MUST NOT silently pick a branch.
   Fork resolution is out of scope for `brth/1` and must be explicit in a later
   revision (see §11).

Derived state exposes: current root policy, active keys with scopes and expiry,
claims, `seq` head, chain hash, and status `OK` / `CONFLICTED` / `BROKEN`.

### 6.5 Historical validity

A signature made by a key that was valid at the time remains valid historical
evidence after revocation. Revocation stops *future* authority; it does not erase
the past. Consumers state which sequence position they evaluated.

---

## 7. Attestations

Attestations are how the world says things *about* an actor. They never change the
subject's `IdentityID`, root, keys or continuity.

```json
{
  "type": "brth.attest",
  "v": 1,
  "subject": "b1:…",
  "issuer": "b1:…",
  "claim": { "actor.kind": "human", "legal.name": "…", "scheme": "mitid" },
  "iat": 1760000000,
  "ref": "<b64u H(CJSON(attested object))>" | null,
  "sigs": [ { "alg": "ML-DSA-87", "kid": "k:…", "sig": "<b64u>" } ]
}
```

- Verified only against the **issuer's** authority log at `iat`; an attestation is
  exactly as trustworthy as the issuer, and BRTH makes no claim beyond that.
- `actor.kind`, `human`, `ai`, `model.*`, `runtime.*`, `operator.*`,
  `organization.*`, `mitid-verified` are all attestation/claim vocabulary, never
  root mechanisms and never part of `IdentityID`.
- Consumers MUST display self-claims and third-party attestations differently.

---

## 8. Recovery

Offline, from paper only:

1. Enter 24 words; validates BIP-39 checksum.
2. Recover `root_entropy`, derive both root keypairs (§4).
3. Rebuild Birth and recompute `identity_id` (§5) — must match the expected ID.
4. Fetch public authority-log head (public data; any mirror).
5. Generate a fresh operational key; build `authorize` (or `succeed`) with
   `prev` = current head.
6. Sign with **both** root families (2-of-2).
7. Export only the event and signatures; erase root private material; power down.

The words alone reconstruct root authority and the Birth. The *latest head* is
public data and is required only to append correctly; it is never secret.

---

## 9. Carriage over Punkti Layer 3

BRTH is pure Layer 4. A Punkti node that has never heard of BRTH MUST transport
BRTH atoms unchanged.

- A BRTH object travels in the Punkti atom's opaque `x` string as:

```text
x = "brth/1:" + CJSON(brth_object)
```

- Punkti Layer 3 MUST treat `x` as an opaque UTF-8 string: no parsing, no
  normalization, no re-serialization, no field inspection.
- BRTH MUST NOT require any Punkti field, validation state, reference vocabulary,
  algorithm profile or synchronization behavior to change.
- The carrier may report `UNVERIFIABLE-alg` for BRTH-specific signatures. That is
  not a rejection and MUST NOT cause payload loss.
- Receipt is proven by byte equality of the canonical atom bytes and of `x` before
  and after transport, including through nodes that do not implement BRTH.

BRTH deliberately does not reuse the Punkti envelope signature field for its own
authority semantics: Punkti provenance and BRTH authority are different questions.

---

## 10. Security invariants

Explicitly addressed by `brth/1`:

| Threat | Handling |
|---|---|
| Recovery-phrase theft | Bearer secret; no protocol defense once fully leaked; published ID does not reveal it |
| Weak randomness | 256-bit CSPRNG requirement; test vectors pin derivation |
| Algorithm downgrade | Algorithms are explicit, case-sensitive, never inferred; root policy is 2 distinct families |
| Key substitution | Every key is bound by `kid` into a signed chained event |
| One root family broken | 2-of-2 across ML-DSA and SLH-DSA; a single-family break is not sufficient |
| Device/operational key compromise | `revoke`/`succeed` from root; log is append-only |
| Replay of old events | `seq`/`prev` chain; duplicate or misplaced events rejected |
| Forked authority | Detected and surfaced as `CONFLICTED`, never silently resolved |
| Malicious relay withholding/reordering | Log is self-authenticating; partial logs are reported as partial, never as complete |
| Identifier collision | 256-bit hash; no truncation in protocol comparisons |
| Ambiguous encodings | Single `CJSON` profile; floats and duplicate keys forbidden |
| Parser differentials | Strict field sets, exact type checks, no unknown fields |
| Recovery material leaking | Root bytes never enter any BRTH object; test asserts absence |
| Future algorithm deprecation | Root rotation is a first-class event; `suite`/`alg` are explicit |

Explicit non-guarantees: no truth, no personhood, no global ordering, no freshness
guarantee, no protection after full phrase compromise, no fork resolution.

---

## 11. Deliberately out of scope for `brth/1`

- Fork *resolution* policy (detection is in scope; resolution is a separate decision).
- Revocation transparency/gossip beyond the append-only log.
- Reputation formulas and trust scores.
- Namespace/name uniqueness.
- Encryption of atoms.
- Any change to Punkti Layer 3, frozen PR #111, deployment or protocol freeze.

---

## 12. Acceptance evidence

This proposal is accompanied by an isolated reference implementation and tests
covering: human + AI actors from clean state, operational key authorization,
revocation and succession, 24-word deterministic recovery, AI runtime/model change
without `IdentityID` change, claim/attestation separation, adversarial log attacks,
deterministic vectors, real dual-PQ verification cross-checked against an
independent OpenSSL 3.5 implementation, and byte-for-byte carriage through the
existing Punkti Mesh carrier.

Nothing here is frozen; implementation lives in `experimental/brth-layer4/` only.
