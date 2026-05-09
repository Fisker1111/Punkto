# Punkto Identity (v0.1)

> How a Punkto author proves who they are.

This document specifies how Punkto identities are generated, stored, recovered, and used to sign atoms. It is a companion to `punkto.md` (atom format) and `punkto.sync.md` (canonical bytes & atom_id), and is the contract that any compliant client, CLI, node, or library must satisfy if it wants to produce signatures that other Punkto implementations can verify.

The goal is **byte-for-byte determinism across implementations**. If two implementations follow this spec correctly, the same 12-word mnemonic will produce the same private key, the same public key, the same Author ID, and the same signature for the same input — regardless of language, OS, or device.

---

## 1. Why identity at all

A Punkto atom is anchored in 3D space with `punkto` and time with `t`. Without identity, anyone can write any text claiming to be anyone. Identity is what lets the network distinguish:

- *“This atom was authored by the same key that authored that other atom.”*
- *“This `f` field is a real claim, signed by someone holding the private key.”*
- *“These two atoms with the same content are duplicates of the same author’s post.”*

Identity is **not** about real-world names or KYC. It is about cryptographic continuity: a key controls a stream of signed atoms, and the network can verify that stream end-to-end.

---

## 2. Design principles

1. **One secret, one identity.** A single 12-word mnemonic is the only secret a user must back up. Everything else is derived deterministically.
2. **Local first.** Keys are generated on the user's device. No central authority issues identities. No server ever sees the private key.
3. **Portable.** The same mnemonic on any compliant implementation produces the same keypair. Identities move freely between devices, browsers, CLIs, and air-gapped boxes.
4. **Printable.** The mnemonic is plain English words and fits on a piece of paper. Cold storage is a notebook, not a hardware wallet.
5. **Verifiable offline.** Anyone with an atom and a public key can verify the signature without contacting any server.
6. **Forgettable.** Lose the mnemonic, lose the identity. There is no recovery system. This is by design.

---

## 3. Algorithm chain

```
  128-bit entropy            (16 random bytes)
        │
        ▼  (BIP39 + 4-bit SHA-256 checksum)
  12 BIP39 words             (the printable, paper-safe secret)
        │
        ▼  (PBKDF2-HMAC-SHA512, 2048 iters, salt="mnemonic"+passphrase)
  64-byte seed
        │
        ▼  (first 32 bytes)
  Ed25519 private key seed
        │
        ▼  (Ed25519 keygen)
  Ed25519 public key (32 bytes)
        │
        ▼  (SHA-256, then base32-geohash, take 12 chars)
  Author ID                  (e.g. "rvdme2w1m6j4")
```

Each arrow is a deterministic, well-defined transformation. Implementations must perform every step exactly as specified.

---

## 4. Mnemonic generation (BIP39)

### Inputs

- 128 bits of entropy from a cryptographically secure RNG (e.g. `secrets.token_bytes(16)` in Python, `crypto.getRandomValues(new Uint8Array(16))` in JavaScript, `/dev/urandom` directly, etc.).

### Steps

1. Compute `cs = sha256(entropy)[0] >> 4` — the top 4 bits of the first SHA-256 byte. This is the 4-bit checksum.
2. Append `cs` to `entropy` as the lowest 4 bits, producing a 132-bit value.
3. Split the 132 bits into 12 groups of 11 bits each, **most-significant group first**.
4. Each 11-bit group (range 0..2047) is an index into the BIP39 English wordlist.
5. The result is an ordered list of 12 lowercase English words.

### Wordlist

The **BIP39 English wordlist** (2048 words, version 1.0). Authoritative source:

> `https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt`

Implementations must use this exact wordlist. Other languages (Spanish, French, etc.) are NOT supported in v0.1 — English is the canonical wordlist for Punkto identities to keep the network unambiguous. (Future versions may add language indicators.)

### Validation

Given a 12-word mnemonic, an implementation re-derives `entropy` and the embedded `checksum`, then independently computes `expected = sha256(entropy)[0] >> 4`. If `checksum != expected`, the mnemonic is invalid (typo). Validation must run **before** any seed derivation.

---

## 5. Seed derivation (PBKDF2)

Follows BIP39 §5:

```
seed = PBKDF2(
    password   = utf8(" ".join(mnemonic_words)),
    salt       = utf8("mnemonic" + passphrase),
    iterations = 2048,
    hmac       = HMAC-SHA512,
    length     = 64 bytes,
)
```

- `mnemonic_words` are the 12 lowercase English words joined with **single ASCII spaces** (no punctuation, no extra whitespace).
- `passphrase` is an optional user-provided string. **In v0.1, the passphrase is the empty string.** Future versions may expose the BIP39 passphrase feature to users.
- The output is a 64-byte seed, deterministic.

This follows BIP39 exactly. Existing BIP39 libraries in any language produce identical bytes.

---

## 6. Keypair derivation (Ed25519)

From the 64-byte seed, take the **first 32 bytes** as the Ed25519 private key seed (called "sk" or "private key seed" in RFC 8032). The Ed25519 algorithm itself derives the public key from this seed via the standard procedure (RFC 8032 §5.1).

```
private_key_seed = seed[0:32]
private_key, public_key = ed25519_keygen(private_key_seed)   # RFC 8032
```

The **public key is exactly 32 bytes**. The **private key seed is exactly 32 bytes** (some libraries expose a 64-byte expanded form; the 32-byte seed is what should be stored / displayed).

### Encoding for display and transport

- **Public key**: Base64 (standard, with padding). 32 bytes encode to a 44-character string ending with `=`.  
  Example: `"/40gHG2DyuxX5C0CR7gHcdTWSqJfPzVnVGjBZlij6yk="`
- **Signature**: Base64 (standard, with padding). 64 bytes encode to an 88-character string ending with `==`.  
  Example: `"b2yp0ewV2GsKxTD7cBk8saiyrzyLeMzghG8WgaUXr4yYhamvWvTBH7LMzOe0Bp94ioJ+hPG6fU5+oihNOplBAw=="`
- **Private key seed**: Base64 (standard, with padding) **only when exporting to encrypted cold storage**. Never display, never transmit, never log.

Implementations MAY accept Base64-URL (no padding) on input as a convenience, but MUST emit standard Base64 (with padding) on output for canonical interoperability.

---

## 7. Author ID derivation

The Author ID is the short, human-readable handle for an identity. It is what appears in the `f` field of an atom and in the UI.

```
author_id = base32_geohash(sha256(public_key))[:12]
```

Where:

- `sha256(public_key)` is the SHA-256 digest (32 bytes) of the 32-byte public key.
- `base32_geohash(bytes)` encodes bytes using the **Punkti geohash alphabet** (5 bits per character):  
  `0123456789bcdefghjkmnpqrstuvwxyz`  
  This is the same alphabet used by Punkto coordinates (`p:u07qskyuhbus`...). Using it for Author IDs gives the system visual consistency: a Punkto coordinate and a Punkto Author ID look like they belong to the same world.
- The encoding is most-significant-bit first, padded with zero bits on the right if the input is not a multiple of 5 bits. (For a 256-bit SHA-256 input, that's 51 full chars plus 1 bit; we only take the first 12 chars, so padding is irrelevant in v0.1.)
- Take the first **12 characters** of the resulting string.

### Properties

- **Length**: 12 characters, fixed.
- **Alphabet**: 32 symbols, lowercase only.
- **Collision resistance**: 60 bits — enough for billions of users without collision in practice. (At ~10⁹ keys, birthday-bound collision probability is ~0.4%. Acceptable for v0.1; v0.2 may extend to 16 chars.)
- **Visually compatible** with Punkto coordinates, so a UI can show "author from `rvdme2w1m6j4` posted at `p:u07qskyuhbus`" without alphabet mismatch.
- **Prefix-matchable**: a UI may show a shortened form (e.g. first 6 chars `rvdme2`) for compactness, since the alphabet is unambiguous and prefix-stable.

### Reverse lookup

An Author ID alone does **not** allow recovery of the public key. The public key must be transmitted alongside any atom that wants its signature verified (typically as a `pubkey` field on the atom, or via a published roster).

---

## 8. Signing an atom

Follows `punkto.sync.md` §3 (canonical atom bytes):

```
canonical_bytes = utf8(json_encode_canonical(atom_without_sig_field))
signature       = ed25519_sign(private_key, canonical_bytes)
atom["sig"]     = base64(signature)
```

Where `json_encode_canonical` means:

1. Remove the `sig` field if present (it is excluded from the signed bytes — it cannot sign itself).
2. Sort all keys lexicographically at every level of nesting.
3. Emit minified JSON: no whitespace between tokens, separators `:` and `,`.
4. Encode the result as UTF-8.

This matches the canonical byte rules used to compute `atom_id`. **Signing and atom_id share the same canonical-bytes definition**, so they are consistent and a verifier can compute both from a single byte sequence.

### What to put in the atom

For a verifier to check the signature without external lookups, the atom should carry both:

- `sig`: the base64-encoded signature (64-byte Ed25519 signature → 88 chars)
- `pubkey`: the base64-encoded public key (32 bytes → 44 chars)

The `f` field should equal the Author ID derived from `pubkey`. If `f` and the derived Author ID disagree, the atom is malformed; verifiers SHOULD reject it. (A relay MAY still store the atom for diagnostics but flag it.)

For implementations that maintain a separate roster of `author_id → pubkey`, the `pubkey` field on every atom is redundant and may be omitted; the verifier looks up by `f`. This is a permissible optimization for trusted private deployments. In the public network, **always include `pubkey`** so verification works without out-of-band lookup.

---

## 9. Verifying an atom

Given an atom with `sig` and `pubkey`:

1. Decode `sig` from base64 → 64 bytes. Reject if length ≠ 64.
2. Decode `pubkey` from base64 → 32 bytes. Reject if length ≠ 32.
3. Recompute `canonical_bytes` from the atom **with `sig` removed** (other fields kept exactly as received, sorted).
4. Run `ed25519_verify(pubkey, signature, canonical_bytes)`. RFC 8032 §5.1.7.
5. Optionally, recompute `expected_author_id = base32_geohash(sha256(pubkey))[:12]` and compare to `atom["f"]`. If they disagree, treat the atom as malformed.

Verification is offline. A verifier needs only the atom itself and standard cryptographic libraries.

---

## 10. Test vectors

These vectors are **canonical** — every compliant implementation MUST produce these exact bytes from these inputs. They are derived from the reference implementation `tools/punkto-key.py` and verified end-to-end (sign + verify + tamper).

### Vector 1

```
Mnemonic (12 words):
  accident race bird another host differ nurse concert flame very guide basic

Entropy (16 bytes, hex):
  01760c5a04c6e07ba5e175585e5d9e09

Seed (64 bytes, hex):  (PBKDF2-HMAC-SHA512, 2048 iters, salt="mnemonic")
  (computed by implementation; first 32 bytes used as Ed25519 seed)

Public key (base64):
  /40gHG2DyuxX5C0CR7gHcdTWSqJfPzVnVGjBZlij6yk=

Author ID (12 chars):
  rvdme2w1m6j4
```

### Atom signing example (using Vector 1)

Input atom (canonical, sig field absent):

```json
{"f":"rvdme2w1m6j4","pubkey":"/40gHG2DyuxX5C0CR7gHcdTWSqJfPzVnVGjBZlij6yk=","punkto":"p:u07qskyuhbus","t":1778400000000,"x":"first signed atom on Punkto"}
```

Signature (base64):

```
b2yp0ewV2GsKxTD7cBk8saiyrzyLeMzghG8WgaUXr4yYhamvWvTBH7LMzOe0Bp94ioJ+hPG6fU5+oihNOplBAw==
```

`atom_id` (full SHA-256, 64 hex chars, computed over canonical bytes excluding sig):

```
72f9302266743ddeed963c8d13f06c1faea40842dd07498d865826a3286e7826
```

Final atom (with sig):

```json
{"f":"rvdme2w1m6j4","pubkey":"/40gHG2DyuxX5C0CR7gHcdTWSqJfPzVnVGjBZlij6yk=","punkto":"p:u07qskyuhbus","sig":"b2yp0ewV2GsKxTD7cBk8saiyrzyLeMzghG8WgaUXr4yYhamvWvTBH7LMzOe0Bp94ioJ+hPG6fU5+oihNOplBAw==","t":1778400000000,"x":"first signed atom on Punkto"}
```

A compliant implementation must accept this atom and output `OK` from verification, and reject any single-byte tampering of any field other than `sig`.

---

## 11. Storage model

Where implementations are expected to put each piece:

| Item | Location | Encryption | Sensitivity |
|---|---|---|---|
| Mnemonic (12 words) | Paper, password manager, encrypted cold storage | n/a (paper) or vault | 🔴 Secret — bearer credential |
| Private key seed (32 bytes) | App's local storage (IndexedDB, file in app data dir) | At-rest encryption recommended (passphrase, OS keystore) | 🔴 Secret |
| Public key (32 bytes) | App, atoms (`pubkey` field), peer rosters | None needed | 🟢 Public |
| Author ID (12 chars) | App, atoms (`f` field), UI everywhere | None needed | 🟢 Public |

### Import / Export contract

A compliant client MUST support both directions:

- **Export**: produce a portable JSON object containing `version`, `author_id`, `pubkey`, and `mnemonic`. Optionally `entropy_hex` for diagnostics. The user is warned that this object contains the secret mnemonic.
- **Import**: accept either a 12-word string or the JSON object above. After import, re-derive everything and confirm `author_id` matches.

Export format (canonical):

```json
{
  "version": "punkto-identity-v0.1",
  "author_id": "rvdme2w1m6j4",
  "pubkey": "/40gHG2DyuxX5C0CR7gHcdTWSqJfPzVnVGjBZlij6yk=",
  "mnemonic": ["accident","race","bird","another","host","differ","nurse","concert","flame","very","guide","basic"]
}
```

---

## 12. Security notes

- **Mnemonic is bearer**: anyone holding the 12 words IS the identity. Treat with the same caution as a password manager master key or a hardware wallet seed phrase.
- **No central recovery**: there is no "forgot password". Lose the mnemonic and the associated paper, and the identity is unrecoverable. This is intentional.
- **No revocation in v0.1**: if a key is compromised, the user generates a new identity. Old atoms remain attributed to the old key. v0.2 will introduce signed revocation atoms to publicly mark a key as no longer authoritative.
- **No key rotation in v0.1**: same as above.
- **Stored private key encryption**: the spec does not mandate at-rest encryption of the stored private key seed, but strongly recommends it for shared-device contexts (browsers, multi-user laptops). The mnemonic remains the canonical backup either way.
- **Side channels**: implementations should use constant-time Ed25519 from a vetted library (`cryptography` in Python, `WebCrypto` or `tweetnacl` in JS, `crypto/ed25519` in Go, etc.). Do NOT roll your own Ed25519.
- **RNG quality**: the 16 bytes of initial entropy MUST come from a cryptographic RNG. Predictable RNGs make all derived keys predictable.

---

## 13. Compatibility with other specs

- **`punkto.md`**: Author ID is what populates the `f` field of an atom. The `f` field's format is otherwise free-form, but for identities generated under this spec, `f` MUST equal the derived Author ID.
- **`punkto.sync.md` §3**: canonical_atom_bytes (sorted keys, no whitespace, UTF-8, sig excluded) is the byte sequence Ed25519 signs. atom_id is SHA-256 of the same sequence. Sign and atom_id are computed from the identical bytes — there is no second canonicalization.
- **`punkto.relay.md`**: relay v0.1 stores `sig` and `pubkey` if present but does not verify in v0.1. `punkto-relay v0.2+` will verify and reject invalid signatures when `PUNKTO_REQUIRE_SIG=true` is set.
- **`punkto.ui.md`**: clients are expected to handle key generation, mnemonic display, paper print, import/export, and at-rest storage. The user must never have to think about Ed25519 or PBKDF2; they think about *"my 12 words"*.

---

## 14. Reference implementation

The reference implementation is `tools/punkto-key.py` in this repository — a single-file Python 3.8+ script (~300 lines) using only `cryptography` and stdlib. It performs every step in this spec, includes self-tests against the vectors above, and is the source of truth for byte-level interpretation when reading this document is ambiguous.

Usage:

```bash
pip install cryptography
python3 tools/punkto-key.py new                          # mint identity
python3 tools/punkto-key.py import w1 w2 ... w12         # restore identity
python3 tools/punkto-key.py sign  <atom.json>            # sign an atom
python3 tools/punkto-key.py verify <atom.json>           # verify an atom
```

A browser/JavaScript reference implementation will accompany the PWA's identity UX (deferred to v0.2).

---

## 15. Non-goals (v0.1)

- Multi-language BIP39 wordlists (English only)
- BIP39 passphrase support (empty passphrase only)
- Hardware wallet integration
- Hierarchical deterministic key derivation (BIP32) — every identity is its own root, no child keys
- Key rotation, signed revocation, or key history
- Identity attestation ("this Author ID is also @somebody on Twitter")
- Web of trust signatures across identities

All of these are reasonable v0.2 / v0.3 explorations.

---

## 16. Changelog

- **v0.1** (initial) — Ed25519, BIP39 12-word mnemonic, PBKDF2-HMAC-SHA512 (2048 iters), Author ID = base32_geohash(sha256(pubkey))[:12], canonical bytes match `punkto.sync.md` §3, single test vector, reference implementation `tools/punkto-key.py`.

---

## 17. Guiding idea

> A Punkto identity is twelve printable words.
>
> Everything else — keys, signatures, IDs — is derivable from those words on any device, in any language, forever.
