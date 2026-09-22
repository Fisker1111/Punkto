# Punkti 0.6 — Identity Root and Birthstone Proposal

**Status:** Draft for peer review  
**Scope:** Protocol design only — no Punkto application/runtime changes  
**Compatibility:** Intentionally breaking before v1.0  
**Target:** Punkti 0.6

> Punkto is frozen on the current Punkti 0.5 identity model while this proposal is reviewed. A later, separate change may migrate Punkto to an accepted Punkti 0.6 specification.

---

## 1. Motivation

Punkti 0.5 proved that a human-readable recovery phrase can deterministically create an identity and sign public atoms. The current model, however, makes the identity effectively equal to one Ed25519 public key. That creates long-term problems:

- replacing the signing algorithm replaces the identity;
- Ed25519 is not designed to resist a sufficiently capable cryptographic quantum computer;
- a 12-word / 128-bit recovery phrase is weaker than necessary for a root intended to survive decades;
- the short Author ID is not suitable as a permanent global identity namespace;
- root authority, recovery authority and everyday device signing are not separated;
- there is no protocol-native key succession model.

Punkti has no meaningful installed user base yet. This is the least expensive point at which to make breaking identity changes.

## 2. Design goals

Punkti 0.6 identity MUST satisfy:

1. **Paper recovery.** The 24-word recovery phrase, the public spec and an offline computer MUST be sufficient to reconstruct the same root identity without any server, Foundation, cloud provider or application.
2. **Identity is not a signing key.** The permanent identity MUST survive replacement of devices, keys and algorithms.
3. **Post-quantum-resistant root.** Use 256-bit random root entropy and standardized post-quantum signature families.
4. **Algorithm agility.** Key/signature objects MUST identify algorithms and parameter sets explicitly.
5. **Offline root, disposable operational keys.** Root material SHOULD normally stay offline; ordinary atoms SHOULD use replaceable authorized keys.
6. **Public verification.** Birthstones and identity events are public and independently verifiable.
7. **App independence.** Punkti identity MUST not depend on Punkto or any particular application.
8. **Minimum permanent core.** Names, avatars, profiles, reputation, credentials and app data are child atoms, not Birthstone fields.

Punkti proves provenance and continuity. It does not prove truth.

## 3. Terminology

- **Recovery Phrase:** 24 human-readable words; bearer-secret recovery material.
- **Root Entropy:** 256 random bits encoded by the Recovery Phrase.
- **Root Authority:** cryptographic authority deterministically derived from Root Entropy.
- **Birthstone:** first immutable public object of an identity, committing to its initial Root Authority policy.
- **Identity ID:** permanent content-derived identifier of the deterministic Birthstone core.
- **Operational Key:** replaceable key authorized to sign ordinary atoms or perform an explicit role.
- **Identity Event:** immutable signed atom that changes derived current identity state without rewriting history.

## 4. Recovery Phrase v1

A compliant implementation MUST generate 256 bits using a cryptographically secure random number generator. Humans MUST NOT choose the words.

The initial proposal uses the BIP-39 English 2048-word list and checksum encoding: 256 bits entropy + 8 checksum bits = 24 words.

Punkti uses BIP-39 only as a mature human transcription format. **Punkti 0.6 does not use BIP-39 PBKDF2 wallet-seed derivation as the identity root.** The canonical Punkti Root Entropy is the recovered 32-byte entropy value itself.

Punkti 0.6 MUST NOT require or silently apply an extra mnemonic passphrase. The 24 written words alone recover the root identity.

## 5. Root derivation v1

All root material MUST be deterministically derived from Root Entropy with a standard domain-separated KDF.

Proposed: **HKDF-SHA-512**.

Conceptually:

```text
root_entropy = decode_recovery_phrase(words)   # exactly 32 bytes
root_prk = HKDF-Extract(
  salt = SHA-512("Punkti/0.6/root/v1"),
  IKM  = root_entropy
)

ml_dsa_seed = HKDF-Expand(root_prk, "Punkti/0.6/root/ML-DSA-87", 32)

slh_sk_seed = HKDF-Expand(root_prk, "Punkti/0.6/root/SLH-DSA-SHAKE-256s/SK.seed", 32)
slh_sk_prf  = HKDF-Expand(root_prk, "Punkti/0.6/root/SLH-DSA-SHAKE-256s/SK.prf", 32)
slh_pk_seed = HKDF-Expand(root_prk, "Punkti/0.6/root/SLH-DSA-SHAKE-256s/PK.seed", 32)
```

Exact bytes, labels, encoding and KDF construction MUST be frozen by normative test vectors before acceptance. Root private material can be rederived offline and erased afterward.

## 6. Proposed Root Authority suite

Initial Birthstones SHOULD commit to two independent NIST post-quantum signature families:

1. **ML-DSA-87** (FIPS 204, category 5)
2. **SLH-DSA-SHAKE-256s** (FIPS 205, category 5)

ML-DSA is the practical PQ signature family; SLH-DSA is hash-based and rests on substantially different assumptions. Root operations are rare, so large SLH-DSA signatures are acceptable there.

Proposed initial root-management policy: **2-of-2**. Both root families authorize high-authority transitions such as root-policy replacement or emergency re-establishment of operational authority.

Ordinary public atoms SHOULD NOT require both root signatures. The operational signing suite is intentionally outside this proposal.

## 7. Birthstone Core

The Birthstone Core MUST be fully deterministic from the Recovery Phrase / Root Entropy and fixed Punkti 0.6 constants.

A random timestamp, human name, server identifier or other external value MUST NOT be part of the permanent identity commitment, because the 24 words alone would then be insufficient to recreate the identity.

Conceptual object:

```json
{
  "type": "punkti.identity.birthstone",
  "version": "0.6",
  "root_kdf": "HKDF-SHA-512-v1",
  "root_policy": {
    "threshold": 2,
    "keys": [
      {"alg": "ML-DSA-87", "pub": "<canonical public-key encoding>"},
      {"alg": "SLH-DSA-SHAKE-256s", "pub": "<canonical public-key encoding>"}
    ]
  }
}
```

Rules:

- exactly one Birthstone defines one identity;
- it is public and immutable;
- it never contains the Recovery Phrase or Root Entropy;
- it MUST NOT contain names, avatars, profiles, locations or nondeterministic attributes;
- copies are equivalent regardless of database, relay, archive or app;
- control is demonstrated by signatures satisfying its root policy.

> The Birthstone anchors the identity. It does not contain the person's life.

## 8. Permanent Identity ID

The Identity ID MUST derive from the canonical Birthstone Core, not any single public key.

Proposed:

```text
birthstone_bytes = canonical_encode(BirthstoneCore)
identity_digest  = SHA3-256(birthstone_bytes)
identity_id      = "i:" + canonical_base32(identity_digest)
```

Properties:

- full 256-bit identifier;
- stable across operational-key changes;
- recreated from the 24 words;
- no global naming registry;
- UIs may display a short fingerprint, but protocol comparisons MUST use the full ID.

Human names such as `Fisker` are ordinary signed attributes and need not be globally unique.

## 9. Forward-only identity state

Identity state is derived from immutable public events. Nothing edits the Birthstone or rewrites history.

Candidate events:

```text
identity.key.authorize
identity.key.revoke
identity.root.rotate
identity.profile.set
identity.name.set
identity.link.legacy
```

Conceptual flow:

```text
Birthstone
    ↓
root authorizes device key A
    ↓
A signs public atoms
    ↓
root revokes A and authorizes B
    ↓
B signs public atoms
```

Old atoms remain valid historical statements from keys valid at that time.

Punkti MUST define anti-replay, succession and conflicting/forked identity-management-event semantics before implementation.

## 10. Offline recovery

A compliant recovery flow SHOULD support:

1. Boot a trusted offline machine, e.g. Raspberry Pi.
2. Enter the 24 words.
3. Validate checksum.
4. Recover the 32-byte Root Entropy.
5. Derive Root Authority keypairs.
6. Reconstruct Birthstone Core.
7. Recompute/display permanent Identity ID.
8. Generate/import a new public operational key.
9. Sign the required public authorization/recovery event under root policy.
10. Export only public event/signatures.
11. Erase transient root private material and power down.

The words reconstruct root authority and Birthstone, not necessarily the latest public history. Latest public identity state may be needed to create a correctly linked succession event; that state is public, not secret.

## 11. QR and paper

Punkti MUST clearly distinguish public identity material from secret recovery material.

**Public identity QR** may contain the full Identity ID, optionally the Birthstone, and optional discovery hints. It MUST NOT contain Root Entropy.

**Secret recovery QR** may encode the same 256-bit Root Entropy as the words but MUST be unmistakably marked as a bearer secret. Photographing it is equivalent to copying the 24 words.

The 24 words remain the canonical human-writeable fallback. Recovery MUST NOT require QR recognition, a vendor app or network access.

## 12. Extensible objects / offspring

The Birthstone is intentionally minimal. Rich attributes are signed child atoms referencing the Identity ID: names, avatars, contact endpoints, credentials, organization memberships, reputation/vouches, game identities, agent authority, wallets/payment offspring, and future application-specific objects.

This gives MongoDB-like schema extensibility at the object layer without turning the permanent root into an unbounded mutable document.

## 13. Public atoms

Punkti's default remains **public signed atoms**. A signature proves provenance and integrity, not truth and not secrecy. Encryption may be a higher-layer convention but is not required by Punkti identity.

## 14. Migration from 0.5

There is intentionally no requirement to preserve the 0.5 identity construction as the permanent 0.6 identity. There is no meaningful external user base; take the breaking change now.

For historical provenance, an existing 0.5 Ed25519 identity MAY publish a one-way signed `identity.link.legacy` atom pointing to the new 0.6 Identity ID. This does not make the old key the security root of the new identity.

Punkto remains frozen on 0.5 until a separate migration PR is approved.

## 15. Canonical serialization — hard-change review item

0.5 uses simplified sorted/minified JSON. Before 0.6 is frozen, review adopting a formally specified cross-language canonicalization standard such as RFC 8785 JCS for identity objects and potentially all 0.6 atoms.

This is deliberately unresolved because canonical bytes become extremely expensive to change after independent implementations and permanent signatures exist.

## 16. Security invariants

The final design MUST explicitly address:

- Recovery Phrase theft;
- weak/randomness failures;
- algorithm downgrade;
- key substitution;
- compromise of one root signature family;
- device compromise;
- replay of old authorization events;
- conflicting/forked root transitions;
- malicious relays withholding/reordering events;
- identifier collisions;
- ambiguous canonical encodings;
- parser differentials;
- future algorithm deprecation;
- accidental publication of recovery material.

No protocol can protect an identity after an attacker obtains the full Recovery Phrase unless authority had already been changed by a separately defined mechanism.

## 17. Open peer-review questions

1. Is 24-word / 256-bit root entropy the right long-term tradeoff?
2. Use BIP-39 only for transcription, or define a Punkti word encoding?
3. HKDF-SHA-512 or a SHA-3-family KDF such as KMAC?
4. Are ML-DSA-87 + SLH-DSA-SHAKE-256s appropriate root parameter sets?
5. Is 2-of-2 root authorization the right policy?
6. SHA3-256 Identity ID or an algorithm-tagged/multihash construction?
7. Which canonical serialization should 0.6 freeze?
8. How are identity-management forks resolved without central authority?
9. What minimum data must an ordinary atom carry for independent verification?
10. Should operational keys be independently generated, root-derived, or support both?
11. How does a future crypto break safely rotate root policy?
12. How do UX/protocol encodings make public Identity QR and secret Recovery QR impossible to confuse?

## 18. Acceptance gate

Do not move this proposal directly into production code.

Before implementation:

- independent cryptographic review;
- distributed/protocol review;
- interoperability/implementability review;
- adversarial/abuse review;
- normative byte-level test vectors;
- clean-room deterministic recovery in at least two independent implementations;
- offline recovery demonstration from 24 words;
- frozen canonical encodings and algorithm identifiers.

At least three independent reviewers/systems should review the same draft without inheriting each other's conclusions.

## 19. Guiding principle

> **Paper + public specification + mathematics must be enough to recover control of a Punkti identity.**

Applications may disappear. Companies may disappear. The Foundation may disappear. Signing algorithms may be replaced. The identity must not depend on any of them.
