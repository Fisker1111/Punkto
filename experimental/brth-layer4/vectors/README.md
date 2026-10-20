# BRTH deterministic golden vectors

**TEST-ONLY-NOT-A-SECRET.** These fixtures use the published BIP-39 256-bit
all-zero and all-one test cases. They must never be used for a real identity.
The input cases are named, rather than embedding entropy or recovery words in
public BRTH objects or vector JSON. Test code reconstructs the published inputs.

- `root.json`: exact ML-DSA-87 (2592-byte) and SLH-DSA-SHAKE-256s (64-byte)
  public keys after BRTH's HKDF-SHA-512 derivation.
- `birth.json`: exact canonical Birth bytes as hex, and full SHA3-256/base32
  IdentityID. No timestamps, private keys, entropy or recovery phrases.

From `experimental/brth-layer4/`:

```sh
node tools/gen-vectors.js
git diff --exit-code -- vectors/
```

Generation is offline and deterministic. The suite compares both published
inputs against these committed bytes. Independent OpenSSL checks cover both
FIPS key encodings and both signature verification directions.

The bundled English BIP-39 list comes from `@scure/bip39@2.0.1`,
`wordlists/english.js`; its MIT license is in `src/wordlist-LICENSE`.
It is data only; the implementation does not depend on that package.
