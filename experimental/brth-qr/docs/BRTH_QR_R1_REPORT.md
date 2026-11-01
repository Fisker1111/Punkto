# BRTH one-QR offline Q-day Birthstone — R1 measured report

## 1. Scope, layering and non-goals

This is a Layer 4 packaging research result, not a protocol freeze, production
wallet, migration, deployment, server integration or Layer 3 change. All new
tracked candidates are under `experimental/brth-qr/`; the existing Layer 4
implementation is imported unchanged. Existing production Ed25519 signatures
remain **NON-post-quantum**. No Falcon or other non-NIST scheme is used.

This report tests one ordinary QR Model 2 symbol up to version 40 at fixed
L/M/Q/H error correction. It does not claim universal impossibility across other
barcodes, multiple symbols, arbitrary compression, other future algorithms or
100 years of physical survival. No DNS, Punkti node, server, registry or second
lookup participates in reconstruction of the original root/Birth.

## 2. Audit of the closed CEO-OS #3 reference

The audit evidence is the local committed implementation, not a fresh retrieval
of the issue. Concrete sources under `experimental/brth-layer4/`:

| Source | What it implements or demonstrates |
|---|---|
| `docs/BRTH_LAYER4_SPEC.md` §§3–8 | CJSON, 24-word transcription, root derivation, immutable Birth, authority and recovery |
| `src/mnemonic.js` | BIP-39 English, 256-bit entropy plus checksum; no wallet PBKDF2/passphrase |
| `src/keys.js` | HKDF-SHA-512 domain-separated seeds, ML-DSA-87 and SLH-DSA-SHAKE-256s keygen/sign/verify |
| `src/birth.js`, `src/cjson.js`, `src/format.js` | Fixed root suite/quorum/order, canonical bytes, full content-derived ID |
| `src/authority.js` | Append-only signed hash chain; prior-state authority; revoke/succeed/root.rotate; fork detection |
| `src/recover.js` | Original words reconstruct original Birth; current public log required to append; rejects replaced root policy |
| `test/pq.test.js`, `tools/pq-openssl.js` | Independent noble ↔ OpenSSL 3.5.5 public keys/signatures, both families, tampering and fallback |
| `test/vectors.test.js`, `vectors/root.json`, `vectors/birth.json` | Deterministic published-input public keys, canonical Birth and ID |
| `test/authority.test.js`, `test/attest-recover.test.js` | Human/AI continuity, succession/rotation, historical authority and recovery |
| `EVIDENCE.md` | Prior run: 18 passed, 0 failed, 0 skipped; independent cross-check record |

#3 proved the deterministic chain **24 words → entropy → HKDF-SHA-512 →
ML-DSA-87 + SLH-DSA-SHAKE-256s roots → canonical Birth →
`IdentityID = "b1:" + base32(SHA3-256(CJSON(Birth)))`**. The log enforces
2-of-2 dual-family root quorum; revoke, succeed and root.rotate preserve the
original IdentityID. Log forks remain explicit, and a supplied log is partial
rather than proof of global freshness. Original words do not regain authority
after roots have been replaced.

#3 did **not** solve the physical one-QR package or the distinction between a
private recovery backup and a publicly displayed verification descriptor.
A root public key is not a signature; identity content addressing is not proof
of a person's name or possession of its private keys.

This run independently measures root public keys of 2592 and 64 bytes, and
verified signatures of 4627 and 29792 bytes. The canonical Birth is
3683 bytes. Section 4 contains all actual parameter-set outputs;
section 7 contains the independent OpenSSL checks. The current unchanged-suite run also passed **18 tests, 0 failed, 0 skipped**,
Its actual command/output is recorded in
`out/validation.txt`; these are results of this run, not merely the historical
#3 counts above.

## 3. Threat model

| Attacker capability | Consequence and boundary |
|---|---|
| Harvest public records now; obtain future quantum computation | These are signatures, not encrypted messages: the direct risk is future forgery. There is no confidentiality claim or encryption layer to decrypt. Publishing the private capsule compromises authority immediately, without a quantum computer. |
| Replace every byte of a displayed QR | A dual descriptor detects key edits against its retained Birth digest, but an attacker can replace both keys and digest with a new internally consistent identity. With no previously trusted expected full ID or trusted physical provenance, one QR cannot establish which actor was intended. |
| Break an algorithm during 100+ years of offline storage | The static QR cannot fetch or prove later succession. Existing BRTH root.rotate supports replacement keys only in its currently fixed suite; genuinely new algorithms require a later protocol revision and retained authenticated transition history. No century-long security guarantee is made. |
| Steal private words/capsule, or compromise an operational key | Both private forms carry the same bearer root authority. Operational revoke/succeed can preserve ID through the public log; full root compromise defeats this custody design. Old words alone cannot authorize after root rotation. |
| Read a public QR or substitute stale public history | Public descriptors reveal only public roots and a digest, not the root secret. They cannot prove current authority, revocation status or log completeness. The private backup and public verification scenarios are separate designs. |

**Hard rule: a publicly displayed QR must NOT expose the private root signing
seed or entropy.** Private backups are private-only; neither signatures nor QR
error correction makes public exposure safe. Both constructions inherit the
unchanged BRTH dual-family assumptions, SHA3-256 content binding, HKDF-SHA-512,
256-bit entropy quality, correct implementations and secure private custody.

## 4. Real one-QR byte and character budget

Regenerate with `python3 tools/measure_qr.py` using the interpreter selected in
README. Sources: `out/measurements.json` and `out/measurements.md`. Encoder:
segno 1.6.6; decoders: OpenCV 5.0.0 and zxing-cpp 3.1.1; Python: 3.14.9.

Capacities below are encoder-measured binary-search boundaries: each limit
encodes at version 40 and limit+1 is rejected. EC boosting is disabled. Numeric
and alphanumeric limits count digits/characters; byte limits count octets.
Payloads use byte mode except uppercase unpadded base32, explicitly measured
in alphanumeric mode. Padded base64 uses byte mode. Binary payloads have no
text character representation (N/A), and raw bytes distinguish source bytes
from the size after textual encoding. Alphanumeric shortfalls are ASCII bytes
and equivalently characters, not a claim about byte-mode capacity.

Every parameter set below uses real keygen, real signing and successful
verification. Smaller parameter sets are **size comparisons only**. Every
feasible payload/EC case is rendered to a real PNG in memory and compared
byte-for-byte independently with OpenCV's `detectAndDecodeBytes` and zxing-cpp's
`read_barcodes` result `.bytes`; each decoder tries two raster scales when necessary.
All attempts are retained in JSON. `decode_cvp2` (the specified field name) records
cv2, `decode_zxingcpp` records zxing-cpp, and `decode_ok` is their logical OR. Infeasible cases cannot
produce a version ≤40 symbol: their decode result is explicitly **not encodable**,
not an invented successful round trip. No case is dropped.

Measured totals: **288 payload/EC cases, 98 fit, 98 successful
PNG decodes by at least one decoder, 0 cases read by neither decoder,
190 infeasible**. OpenCV decoded **55**
cases byte-identically; zxing-cpp decoded **98**.
A failure by one decoder is a limitation of that decoder, not a QR capacity limit
or evidence that the payload is unreadable. PNG success does not establish
reliable scanning on physical paper. No printer/camera durability trial was run.

The exact arithmetic table includes the smallest ML-DSA parameter set:
ML-DSA-44 raw PK+signature is already larger than one v40-L symbol, even before
metadata. The smallest SLH parameter set is also shown. These are lower bounds
for these uncompressed public-key-plus-signature packages, not all conceivable
cryptographic constructions. Every **INFASIBLE** row below repeats its exact
measured shortfall.

| Mode | v40-L | v40-M | v40-Q | v40-H |
|---|---:|---:|---:|---:|
| byte | 2953 | 2331 | 1663 | 1273 |
| alphanumeric | 4296 | 3391 | 2420 | 1852 |
| numeric | 7089 | 5596 | 3993 | 3057 |

| Algorithm | PK bytes | Sig bytes | PK base64 | PK base32 | Sig base64 | Sig base32 |
|---|---:|---:|---:|---:|---:|---:|
| ML-DSA-44 | 1312 | 2420 | 1752 | 2100 | 3228 | 3872 |
| ML-DSA-65 | 1952 | 3309 | 2604 | 3124 | 4412 | 5295 |
| ML-DSA-87 | 2592 | 4627 | 3456 | 4148 | 6172 | 7404 |
| SLH-DSA-SHAKE-128s | 32 | 7856 | 44 | 52 | 10476 | 12570 |
| SLH-DSA-SHAKE-192s | 48 | 16224 | 64 | 77 | 21632 | 25959 |
| SLH-DSA-SHAKE-256s | 64 | 29792 | 88 | 103 | 39724 | 47668 |
| SLH-DSA-SHAKE-128f | 32 | 17088 | 44 | 52 | 22784 | 27341 |
| SLH-DSA-SHAKE-256f | 64 | 49856 | 88 | 103 | 66476 | 79770 |

| Algorithm | PK + signature | v40-L bytes | Exact shortfall bytes |
|---|---:|---:|---:|
| ML-DSA-44 | 1312 + 2420 = 3732 | 2953 | 779 |
| ML-DSA-65 | 1952 + 3309 = 5261 | 2953 | 2308 |
| ML-DSA-87 | 2592 + 4627 = 7219 | 2953 | 4266 |
| SLH-DSA-SHAKE-128s | 32 + 7856 = 7888 | 2953 | 4935 |
| SLH-DSA-SHAKE-192s | 48 + 16224 = 16272 | 2953 | 13319 |
| SLH-DSA-SHAKE-256s | 64 + 29792 = 29856 | 2953 | 26903 |
| SLH-DSA-SHAKE-128f | 32 + 17088 = 17120 | 2953 | 14167 |
| SLH-DSA-SHAKE-256f | 64 + 49856 = 49920 | 2953 | 46967 |

| Payload | Mode | EC | Raw bytes | Payload bytes | Encoded characters | Version | Modules/side | Verdict | Shortfall bytes | PNG decode |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| recovery-24-words | byte | L | 187 | 187 | 187 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| recovery-24-words | byte | M | 187 | 187 | 187 | 10 | 57 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| recovery-24-words | byte | Q | 187 | 187 | 187 | 12 | 65 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| recovery-24-words | byte | H | 187 | 187 | 187 | 14 | 73 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | L | 37 | 37 | N/A | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | M | 37 | 37 | N/A | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | Q | 37 | 37 | N/A | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-raw | byte | H | 37 | 37 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | L | 37 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | M | 37 | 52 | 52 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | Q | 37 | 52 | 52 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base64 | byte | H | 37 | 52 | 52 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | L | 37 | 60 | 60 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | M | 37 | 60 | 60 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | Q | 37 | 60 | 60 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| private-capsule-base32 | alphanumeric | H | 37 | 60 | 60 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| public-single-descriptor-raw | byte | L | 2629 | 2629 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| public-single-descriptor-raw | byte | M | 2629 | 2629 | N/A | N/A | N/A | INFASIBLE | 298 | not encodable |
| public-single-descriptor-raw | byte | Q | 2629 | 2629 | N/A | N/A | N/A | INFASIBLE | 966 | not encodable |
| public-single-descriptor-raw | byte | H | 2629 | 2629 | N/A | N/A | N/A | INFASIBLE | 1356 | not encodable |
| public-single-descriptor-base64 | byte | L | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 555 | not encodable |
| public-single-descriptor-base64 | byte | M | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 1177 | not encodable |
| public-single-descriptor-base64 | byte | Q | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 1845 | not encodable |
| public-single-descriptor-base64 | byte | H | 2629 | 3508 | 3508 | N/A | N/A | INFASIBLE | 2235 | not encodable |
| public-single-descriptor-base32 | alphanumeric | L | 2629 | 4207 | 4207 | 40 | 177 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| public-single-descriptor-base32 | alphanumeric | M | 2629 | 4207 | 4207 | N/A | N/A | INFASIBLE | 816 | not encodable |
| public-single-descriptor-base32 | alphanumeric | Q | 2629 | 4207 | 4207 | N/A | N/A | INFASIBLE | 1787 | not encodable |
| public-single-descriptor-base32 | alphanumeric | H | 2629 | 4207 | 4207 | N/A | N/A | INFASIBLE | 2355 | not encodable |
| public-dual-descriptor-raw | byte | L | 2693 | 2693 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| public-dual-descriptor-raw | byte | M | 2693 | 2693 | N/A | N/A | N/A | INFASIBLE | 362 | not encodable |
| public-dual-descriptor-raw | byte | Q | 2693 | 2693 | N/A | N/A | N/A | INFASIBLE | 1030 | not encodable |
| public-dual-descriptor-raw | byte | H | 2693 | 2693 | N/A | N/A | N/A | INFASIBLE | 1420 | not encodable |
| public-dual-descriptor-base64 | byte | L | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 639 | not encodable |
| public-dual-descriptor-base64 | byte | M | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 1261 | not encodable |
| public-dual-descriptor-base64 | byte | Q | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 1929 | not encodable |
| public-dual-descriptor-base64 | byte | H | 2693 | 3592 | 3592 | N/A | N/A | INFASIBLE | 2319 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | L | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 13 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | M | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 918 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | Q | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 1889 | not encodable |
| public-dual-descriptor-base32 | alphanumeric | H | 2693 | 4309 | 4309 | N/A | N/A | INFASIBLE | 2457 | not encodable |
| root-dual-public-keys-raw | byte | L | 2656 | 2656 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| root-dual-public-keys-raw | byte | M | 2656 | 2656 | N/A | N/A | N/A | INFASIBLE | 325 | not encodable |
| root-dual-public-keys-raw | byte | Q | 2656 | 2656 | N/A | N/A | N/A | INFASIBLE | 993 | not encodable |
| root-dual-public-keys-raw | byte | H | 2656 | 2656 | N/A | N/A | N/A | INFASIBLE | 1383 | not encodable |
| root-dual-public-keys-base64 | byte | L | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 591 | not encodable |
| root-dual-public-keys-base64 | byte | M | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 1213 | not encodable |
| root-dual-public-keys-base64 | byte | Q | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 1881 | not encodable |
| root-dual-public-keys-base64 | byte | H | 2656 | 3544 | 3544 | N/A | N/A | INFASIBLE | 2271 | not encodable |
| root-dual-public-keys-base32 | alphanumeric | L | 2656 | 4250 | 4250 | 40 | 177 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| root-dual-public-keys-base32 | alphanumeric | M | 2656 | 4250 | 4250 | N/A | N/A | INFASIBLE | 859 | not encodable |
| root-dual-public-keys-base32 | alphanumeric | Q | 2656 | 4250 | 4250 | N/A | N/A | INFASIBLE | 1830 | not encodable |
| root-dual-public-keys-base32 | alphanumeric | H | 2656 | 4250 | 4250 | N/A | N/A | INFASIBLE | 2398 | not encodable |
| canonical-birth-raw | byte | L | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 730 | not encodable |
| canonical-birth-raw | byte | M | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 1352 | not encodable |
| canonical-birth-raw | byte | Q | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 2020 | not encodable |
| canonical-birth-raw | byte | H | 3683 | 3683 | N/A | N/A | N/A | INFASIBLE | 2410 | not encodable |
| canonical-birth-base64 | byte | L | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 1959 | not encodable |
| canonical-birth-base64 | byte | M | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 2581 | not encodable |
| canonical-birth-base64 | byte | Q | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 3249 | not encodable |
| canonical-birth-base64 | byte | H | 3683 | 4912 | 4912 | N/A | N/A | INFASIBLE | 3639 | not encodable |
| canonical-birth-base32 | alphanumeric | L | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 1597 | not encodable |
| canonical-birth-base32 | alphanumeric | M | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 2502 | not encodable |
| canonical-birth-base32 | alphanumeric | Q | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 3473 | not encodable |
| canonical-birth-base32 | alphanumeric | H | 3683 | 5893 | 5893 | N/A | N/A | INFASIBLE | 4041 | not encodable |
| ML-DSA-44-pk-raw | byte | L | 1312 | 1312 | N/A | 26 | 121 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-raw | byte | M | 1312 | 1312 | N/A | 30 | 137 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-raw | byte | Q | 1312 | 1312 | N/A | 36 | 161 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-raw | byte | H | 1312 | 1312 | N/A | N/A | N/A | INFASIBLE | 39 | not encodable |
| ML-DSA-44-pk-base64 | byte | L | 1312 | 1752 | 1752 | 31 | 141 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base64 | byte | M | 1312 | 1752 | 1752 | 35 | 157 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base64 | byte | Q | 1312 | 1752 | 1752 | N/A | N/A | INFASIBLE | 89 | not encodable |
| ML-DSA-44-pk-base64 | byte | H | 1312 | 1752 | 1752 | N/A | N/A | INFASIBLE | 479 | not encodable |
| ML-DSA-44-pk-base32 | alphanumeric | L | 1312 | 2100 | 2100 | 27 | 125 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base32 | alphanumeric | M | 1312 | 2100 | 2100 | 31 | 141 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base32 | alphanumeric | Q | 1312 | 2100 | 2100 | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-pk-base32 | alphanumeric | H | 1312 | 2100 | 2100 | N/A | N/A | INFASIBLE | 248 | not encodable |
| ML-DSA-44-signature-raw | byte | L | 2420 | 2420 | N/A | 36 | 161 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-signature-raw | byte | M | 2420 | 2420 | N/A | N/A | N/A | INFASIBLE | 89 | not encodable |
| ML-DSA-44-signature-raw | byte | Q | 2420 | 2420 | N/A | N/A | N/A | INFASIBLE | 757 | not encodable |
| ML-DSA-44-signature-raw | byte | H | 2420 | 2420 | N/A | N/A | N/A | INFASIBLE | 1147 | not encodable |
| ML-DSA-44-signature-base64 | byte | L | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 275 | not encodable |
| ML-DSA-44-signature-base64 | byte | M | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 897 | not encodable |
| ML-DSA-44-signature-base64 | byte | Q | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 1565 | not encodable |
| ML-DSA-44-signature-base64 | byte | H | 2420 | 3228 | 3228 | N/A | N/A | INFASIBLE | 1955 | not encodable |
| ML-DSA-44-signature-base32 | alphanumeric | L | 2420 | 3872 | 3872 | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-44-signature-base32 | alphanumeric | M | 2420 | 3872 | 3872 | N/A | N/A | INFASIBLE | 481 | not encodable |
| ML-DSA-44-signature-base32 | alphanumeric | Q | 2420 | 3872 | 3872 | N/A | N/A | INFASIBLE | 1452 | not encodable |
| ML-DSA-44-signature-base32 | alphanumeric | H | 2420 | 3872 | 3872 | N/A | N/A | INFASIBLE | 2020 | not encodable |
| ML-DSA-44-pk-signature | byte | L | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 779 | not encodable |
| ML-DSA-44-pk-signature | byte | M | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 1401 | not encodable |
| ML-DSA-44-pk-signature | byte | Q | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 2069 | not encodable |
| ML-DSA-44-pk-signature | byte | H | 3732 | 3732 | N/A | N/A | N/A | INFASIBLE | 2459 | not encodable |
| ML-DSA-65-pk-raw | byte | L | 1952 | 1952 | N/A | 32 | 145 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-raw | byte | M | 1952 | 1952 | N/A | 37 | 165 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-raw | byte | Q | 1952 | 1952 | N/A | N/A | N/A | INFASIBLE | 289 | not encodable |
| ML-DSA-65-pk-raw | byte | H | 1952 | 1952 | N/A | N/A | N/A | INFASIBLE | 679 | not encodable |
| ML-DSA-65-pk-base64 | byte | L | 1952 | 2604 | 2604 | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-base64 | byte | M | 1952 | 2604 | 2604 | N/A | N/A | INFASIBLE | 273 | not encodable |
| ML-DSA-65-pk-base64 | byte | Q | 1952 | 2604 | 2604 | N/A | N/A | INFASIBLE | 941 | not encodable |
| ML-DSA-65-pk-base64 | byte | H | 1952 | 2604 | 2604 | N/A | N/A | INFASIBLE | 1331 | not encodable |
| ML-DSA-65-pk-base32 | alphanumeric | L | 1952 | 3124 | 3124 | 34 | 153 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-base32 | alphanumeric | M | 1952 | 3124 | 3124 | 39 | 173 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-65-pk-base32 | alphanumeric | Q | 1952 | 3124 | 3124 | N/A | N/A | INFASIBLE | 704 | not encodable |
| ML-DSA-65-pk-base32 | alphanumeric | H | 1952 | 3124 | 3124 | N/A | N/A | INFASIBLE | 1272 | not encodable |
| ML-DSA-65-signature-raw | byte | L | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 356 | not encodable |
| ML-DSA-65-signature-raw | byte | M | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 978 | not encodable |
| ML-DSA-65-signature-raw | byte | Q | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 1646 | not encodable |
| ML-DSA-65-signature-raw | byte | H | 3309 | 3309 | N/A | N/A | N/A | INFASIBLE | 2036 | not encodable |
| ML-DSA-65-signature-base64 | byte | L | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 1459 | not encodable |
| ML-DSA-65-signature-base64 | byte | M | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 2081 | not encodable |
| ML-DSA-65-signature-base64 | byte | Q | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 2749 | not encodable |
| ML-DSA-65-signature-base64 | byte | H | 3309 | 4412 | 4412 | N/A | N/A | INFASIBLE | 3139 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | L | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 999 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | M | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 1904 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | Q | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 2875 | not encodable |
| ML-DSA-65-signature-base32 | alphanumeric | H | 3309 | 5295 | 5295 | N/A | N/A | INFASIBLE | 3443 | not encodable |
| ML-DSA-65-pk-signature | byte | L | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 2308 | not encodable |
| ML-DSA-65-pk-signature | byte | M | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 2930 | not encodable |
| ML-DSA-65-pk-signature | byte | Q | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 3598 | not encodable |
| ML-DSA-65-pk-signature | byte | H | 5261 | 5261 | N/A | N/A | N/A | INFASIBLE | 3988 | not encodable |
| ML-DSA-87-pk-raw | byte | L | 2592 | 2592 | N/A | 38 | 169 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-87-pk-raw | byte | M | 2592 | 2592 | N/A | N/A | N/A | INFASIBLE | 261 | not encodable |
| ML-DSA-87-pk-raw | byte | Q | 2592 | 2592 | N/A | N/A | N/A | INFASIBLE | 929 | not encodable |
| ML-DSA-87-pk-raw | byte | H | 2592 | 2592 | N/A | N/A | N/A | INFASIBLE | 1319 | not encodable |
| ML-DSA-87-pk-base64 | byte | L | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 503 | not encodable |
| ML-DSA-87-pk-base64 | byte | M | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 1125 | not encodable |
| ML-DSA-87-pk-base64 | byte | Q | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 1793 | not encodable |
| ML-DSA-87-pk-base64 | byte | H | 2592 | 3456 | 3456 | N/A | N/A | INFASIBLE | 2183 | not encodable |
| ML-DSA-87-pk-base32 | alphanumeric | L | 2592 | 4148 | 4148 | 40 | 177 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| ML-DSA-87-pk-base32 | alphanumeric | M | 2592 | 4148 | 4148 | N/A | N/A | INFASIBLE | 757 | not encodable |
| ML-DSA-87-pk-base32 | alphanumeric | Q | 2592 | 4148 | 4148 | N/A | N/A | INFASIBLE | 1728 | not encodable |
| ML-DSA-87-pk-base32 | alphanumeric | H | 2592 | 4148 | 4148 | N/A | N/A | INFASIBLE | 2296 | not encodable |
| ML-DSA-87-signature-raw | byte | L | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 1674 | not encodable |
| ML-DSA-87-signature-raw | byte | M | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 2296 | not encodable |
| ML-DSA-87-signature-raw | byte | Q | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 2964 | not encodable |
| ML-DSA-87-signature-raw | byte | H | 4627 | 4627 | N/A | N/A | N/A | INFASIBLE | 3354 | not encodable |
| ML-DSA-87-signature-base64 | byte | L | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 3219 | not encodable |
| ML-DSA-87-signature-base64 | byte | M | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 3841 | not encodable |
| ML-DSA-87-signature-base64 | byte | Q | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 4509 | not encodable |
| ML-DSA-87-signature-base64 | byte | H | 4627 | 6172 | 6172 | N/A | N/A | INFASIBLE | 4899 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | L | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 3108 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | M | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 4013 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | Q | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 4984 | not encodable |
| ML-DSA-87-signature-base32 | alphanumeric | H | 4627 | 7404 | 7404 | N/A | N/A | INFASIBLE | 5552 | not encodable |
| ML-DSA-87-pk-signature | byte | L | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 4266 | not encodable |
| ML-DSA-87-pk-signature | byte | M | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 4888 | not encodable |
| ML-DSA-87-pk-signature | byte | Q | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 5556 | not encodable |
| ML-DSA-87-pk-signature | byte | H | 7219 | 7219 | N/A | N/A | N/A | INFASIBLE | 5946 | not encodable |
| SLH-DSA-SHAKE-128s-pk-raw | byte | L | 32 | 32 | N/A | 2 | 25 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-raw | byte | M | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-raw | byte | Q | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-raw | byte | H | 32 | 32 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | L | 32 | 44 | 44 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | M | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | Q | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base64 | byte | H | 32 | 44 | 44 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | L | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | M | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | Q | 32 | 52 | 52 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-pk-base32 | alphanumeric | H | 32 | 52 | 52 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128s-signature-raw | byte | L | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 4903 | not encodable |
| SLH-DSA-SHAKE-128s-signature-raw | byte | M | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 5525 | not encodable |
| SLH-DSA-SHAKE-128s-signature-raw | byte | Q | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 6193 | not encodable |
| SLH-DSA-SHAKE-128s-signature-raw | byte | H | 7856 | 7856 | N/A | N/A | N/A | INFASIBLE | 6583 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | L | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 7523 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | M | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 8145 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | Q | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 8813 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base64 | byte | H | 7856 | 10476 | 10476 | N/A | N/A | INFASIBLE | 9203 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | L | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 8274 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | M | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 9179 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | Q | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 10150 | not encodable |
| SLH-DSA-SHAKE-128s-signature-base32 | alphanumeric | H | 7856 | 12570 | 12570 | N/A | N/A | INFASIBLE | 10718 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | L | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 4935 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | M | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 5557 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | Q | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 6225 | not encodable |
| SLH-DSA-SHAKE-128s-pk-signature | byte | H | 7888 | 7888 | N/A | N/A | N/A | INFASIBLE | 6615 | not encodable |
| SLH-DSA-SHAKE-192s-pk-raw | byte | L | 48 | 48 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-raw | byte | M | 48 | 48 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-raw | byte | Q | 48 | 48 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-raw | byte | H | 48 | 48 | N/A | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | L | 48 | 64 | 64 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | M | 48 | 64 | 64 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | Q | 48 | 64 | 64 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base64 | byte | H | 48 | 64 | 64 | 7 | 45 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | L | 48 | 77 | 77 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | M | 48 | 77 | 77 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | Q | 48 | 77 | 77 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-pk-base32 | alphanumeric | H | 48 | 77 | 77 | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-192s-signature-raw | byte | L | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 13271 | not encodable |
| SLH-DSA-SHAKE-192s-signature-raw | byte | M | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 13893 | not encodable |
| SLH-DSA-SHAKE-192s-signature-raw | byte | Q | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 14561 | not encodable |
| SLH-DSA-SHAKE-192s-signature-raw | byte | H | 16224 | 16224 | N/A | N/A | N/A | INFASIBLE | 14951 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | L | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 18679 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | M | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 19301 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | Q | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 19969 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base64 | byte | H | 16224 | 21632 | 21632 | N/A | N/A | INFASIBLE | 20359 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | L | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 21663 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | M | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 22568 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | Q | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 23539 | not encodable |
| SLH-DSA-SHAKE-192s-signature-base32 | alphanumeric | H | 16224 | 25959 | 25959 | N/A | N/A | INFASIBLE | 24107 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | L | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 13319 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | M | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 13941 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | Q | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 14609 | not encodable |
| SLH-DSA-SHAKE-192s-pk-signature | byte | H | 16272 | 16272 | N/A | N/A | N/A | INFASIBLE | 14999 | not encodable |
| SLH-DSA-SHAKE-256s-pk-raw | byte | L | 64 | 64 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-raw | byte | M | 64 | 64 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-raw | byte | Q | 64 | 64 | N/A | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-raw | byte | H | 64 | 64 | N/A | 7 | 45 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | L | 64 | 88 | 88 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | M | 64 | 88 | 88 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | Q | 64 | 88 | 88 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base64 | byte | H | 64 | 88 | 88 | 9 | 53 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | L | 64 | 103 | 103 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | M | 64 | 103 | 103 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | Q | 64 | 103 | 103 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-pk-base32 | alphanumeric | H | 64 | 103 | 103 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256s-signature-raw | byte | L | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 26839 | not encodable |
| SLH-DSA-SHAKE-256s-signature-raw | byte | M | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 27461 | not encodable |
| SLH-DSA-SHAKE-256s-signature-raw | byte | Q | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 28129 | not encodable |
| SLH-DSA-SHAKE-256s-signature-raw | byte | H | 29792 | 29792 | N/A | N/A | N/A | INFASIBLE | 28519 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | L | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 36771 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | M | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 37393 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | Q | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 38061 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base64 | byte | H | 29792 | 39724 | 39724 | N/A | N/A | INFASIBLE | 38451 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | L | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 43372 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | M | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 44277 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | Q | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 45248 | not encodable |
| SLH-DSA-SHAKE-256s-signature-base32 | alphanumeric | H | 29792 | 47668 | 47668 | N/A | N/A | INFASIBLE | 45816 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | L | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 26903 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | M | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 27525 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | Q | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 28193 | not encodable |
| SLH-DSA-SHAKE-256s-pk-signature | byte | H | 29856 | 29856 | N/A | N/A | N/A | INFASIBLE | 28583 | not encodable |
| SLH-DSA-SHAKE-128f-pk-raw | byte | L | 32 | 32 | N/A | 2 | 25 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-raw | byte | M | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-raw | byte | Q | 32 | 32 | N/A | 3 | 29 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-raw | byte | H | 32 | 32 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | L | 32 | 44 | 44 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | M | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | Q | 32 | 44 | 44 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base64 | byte | H | 32 | 44 | 44 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | L | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | M | 32 | 52 | 52 | 3 | 29 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | Q | 32 | 52 | 52 | 4 | 33 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-pk-base32 | alphanumeric | H | 32 | 52 | 52 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-128f-signature-raw | byte | L | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 14135 | not encodable |
| SLH-DSA-SHAKE-128f-signature-raw | byte | M | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 14757 | not encodable |
| SLH-DSA-SHAKE-128f-signature-raw | byte | Q | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 15425 | not encodable |
| SLH-DSA-SHAKE-128f-signature-raw | byte | H | 17088 | 17088 | N/A | N/A | N/A | INFASIBLE | 15815 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | L | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 19831 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | M | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 20453 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | Q | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 21121 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base64 | byte | H | 17088 | 22784 | 22784 | N/A | N/A | INFASIBLE | 21511 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | L | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 23045 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | M | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 23950 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | Q | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 24921 | not encodable |
| SLH-DSA-SHAKE-128f-signature-base32 | alphanumeric | H | 17088 | 27341 | 27341 | N/A | N/A | INFASIBLE | 25489 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | L | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 14167 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | M | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 14789 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | Q | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 15457 | not encodable |
| SLH-DSA-SHAKE-128f-pk-signature | byte | H | 17120 | 17120 | N/A | N/A | N/A | INFASIBLE | 15847 | not encodable |
| SLH-DSA-SHAKE-256f-pk-raw | byte | L | 64 | 64 | N/A | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-raw | byte | M | 64 | 64 | N/A | 5 | 37 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-raw | byte | Q | 64 | 64 | N/A | 6 | 41 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-raw | byte | H | 64 | 64 | N/A | 7 | 45 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | L | 64 | 88 | 88 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | M | 64 | 88 | 88 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | Q | 64 | 88 | 88 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base64 | byte | H | 64 | 88 | 88 | 9 | 53 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | L | 64 | 103 | 103 | 4 | 33 | FITS | 0 | cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | M | 64 | 103 | 103 | 5 | 37 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | Q | 64 | 103 | 103 | 6 | 41 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-pk-base32 | alphanumeric | H | 64 | 103 | 103 | 8 | 49 | FITS | 0 | cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode |
| SLH-DSA-SHAKE-256f-signature-raw | byte | L | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 46903 | not encodable |
| SLH-DSA-SHAKE-256f-signature-raw | byte | M | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 47525 | not encodable |
| SLH-DSA-SHAKE-256f-signature-raw | byte | Q | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 48193 | not encodable |
| SLH-DSA-SHAKE-256f-signature-raw | byte | H | 49856 | 49856 | N/A | N/A | N/A | INFASIBLE | 48583 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | L | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 63523 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | M | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 64145 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | Q | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 64813 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base64 | byte | H | 49856 | 66476 | 66476 | N/A | N/A | INFASIBLE | 65203 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | L | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 75474 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | M | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 76379 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | Q | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 77350 | not encodable |
| SLH-DSA-SHAKE-256f-signature-base32 | alphanumeric | H | 49856 | 79770 | 79770 | N/A | N/A | INFASIBLE | 77918 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | L | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 46967 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | M | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 47589 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | Q | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 48257 | not encodable |
| SLH-DSA-SHAKE-256f-pk-signature | byte | H | 49920 | 49920 | N/A | N/A | N/A | INFASIBLE | 48647 | not encodable |

## 5. Two minimal constructions, ranked

### Rank 1 — private recovery capsule (private-only)

Exact layout: 5 ASCII bytes `BRQ1S` followed by the 32 entropy bytes underlying
the 24 words: **5 + 32 = 37 bytes**. The header pins this experimental packaging
revision, the existing BRTH-1 suite and the word/derivation rules; it is not a
new BRTH object or a new cryptographic primitive. Base64 is
52 characters; uppercase unpadded
base32 is 60 characters. Measured
raw v40-L-compatible result: 37 bytes; version 3; 29 modules/side; decode: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode.
Measured base32 capsule results: L: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode; M: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode; Q: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode; H: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode.
Measured raw capsule results: L: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode; M: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode; Q: cv2: byte-identical PNG decode; zxing-cpp: byte-identical PNG decode; H: cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode.
These are PNG measurements; physical-backup scanning remains to be tested. The measured published-input 24-word form is
187 UTF-8 bytes; arbitrary phrases vary
in length, so this is not a claimed universal phrase length.

From this QR alone an offline holder can recover the 24-word form, both original
root keypairs, the exact original Birth and IdentityID, and create/verify dual
root signatures locally. The words independently represent the **same entropy**,
not a second lookup. This cannot prove legal identity, intended ownership,
latest authority, subsequent root rotation, physical authenticity or 100-year
algorithm survival. Recovering a non-genesis current log still needs public
history; no such claim is made for this capsule. QR error correction is not
cryptographic authenticity. Custody MUST remain private. Loss or copying is
loss or copying of root authority. Rank 1 best satisfies self-contained offline
reconstruction with small size and both unchanged root families, but only for
a private backup, not a public Birthstone.

### Rank 2 — compact dual-public-root descriptor (publicly displayable)

Exact layout: 5 ASCII bytes `BRQ1D`, 32-byte SHA3-256 canonical Birth digest,
2592-byte ML-DSA-87 public key, 64-byte SLH-DSA-SHAKE-256s public key in that order:
**5 + 32 + 2592 + 64 = 2693 bytes**. The header fixes all remaining canonical
Birth constants, threshold 2, suite, algorithm labels and key order. Rebuild
canonical Birth with the unchanged library and compare its digest; the full ID
is `b1:` plus lowercase unpadded base32 of that digest. No private entropy or
seed is present. The same private 24 words regenerate these exact public roots.
Measured raw L result: 2693 bytes; version 38; 169 modules/side; decode: cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode.
Raw bytes fit L only; the byte-identical PNG round trip is
**demonstrated**
with the per-decoder results above. Byte-identical recovery preserves the descriptor
input to the separately tested canonical Birth reconstruction. Textual base64/base32 variants and exact shortfalls
are in section 4. Binary-safe scanning is a requirement, not an assumption about an
ordinary phone scanner's text UI.

One QR alone supplies both original verification keys, checks the Birth/key
binding, and computes the full original ID. It contains **no signature** and
therefore verifies no signed assertion or proof of possession by itself.
Signatures supplied separately could be verified using its keys, but that is
explicitly outside the strict one-QR-alone claim. It proves neither intended
actor nor current authority/freshness, and cannot incorporate later succession
without more authenticated history. It inherits both BRTH root families, not a
single-family downgrade. Rank 2 meets public custody and self-contained original
public-root reconstruction, but falls short of a self-contained signed public
assertion and requires a dense low-EC binary symbol.

The single-ML descriptor measured in section 4 (`BRQ1M` + digest + ML public key,
**5 + 32 + 2592 = 2629 bytes**) is a diagnostic comparison, **not a third ranked
construction**. Missing the SLH root, it cannot independently reconstruct or
check the full BRTH Birth from its advertised digest. It is not recommended as
a replacement for dual-root verification. Neither ranked construction changes
BRTH identity semantics or claims single-family root authority.

## 6. Result classification

**(c) A tradeoff with explicit residuals.** Compact private recovery and compact
public Birth reconstruction fit by byte budget (public descriptor PNG decode:
cv2: no byte-identical decode; zxing-cpp: byte-identical PNG decode), while even the smallest measured standard
ML-DSA public-key-plus-signature package exceeds v40-L. The exact scoped
infeasibility result is arithmetic in section 4. It is not a proof that every
possible future scheme or every encoding is impossible. Neither construction
simultaneously provides publicly displayed recovery authority, private custody,
self-contained signed current authority and guaranteed 100+ year security.
No Q-day or custody requirement has been weakened to claim that combination.

## 7. Offline clean-machine proof and actual output

Actual command from the repository root:

```sh
node experimental/brth-qr/tools/offline_reconstruct_proof.mjs > experimental/brth-qr/.work/offline.log 2>&1
```

Equivalent reproduction from this directory: `node tools/offline_reconstruct_proof.mjs`.
Exit 0. The exact public JSON output is embedded below and also saved as
`out/offline_proof.json`. A generator child creates the phrase/roots from a fixed public TEST vector,
32 zero bytes (256 zero bits), non-secret test material that must never be used
as a production secret or identity,
Birth and before-signatures, emits only the capsule over private IPC, then
**exits**. Only the capsule survives as secret input. A fresh child in the fresh
temporary cwd, with a minimal environment, reconstructs entropy and the 24-word
form from that capsule and derives both roots through the original Layer 4
implementation. Its direct entropy and word-derived paths agree. It reads
public baseline evidence only **after** deriving the identity; that evidence
cannot supply private authority. It compares canonical Birth bytes, full ID,
and public-key SHA-256 digests, then verifies pre-destruction signatures and new
signatures for **both** root families using the independent OpenSSL 3.5.5 path.
Tampered messages fail. The unchanged recoverFromWords API also reconstructs
the same identity and creates a valid genesis authorization event.

Default runs reproduce `out/offline_proof.json` **byte-for-byte** with the same
runtime and isolation environment (these environment details are included in
the evidence). Two default runs were compared with `sha256sum` and `cmp`;
the actual outputs and matching digests are recorded in `out/validation.txt`.
For fresh random entropy use `node tools/offline_reconstruct_proof.mjs --random`.
That opt-in overwrites the evidence with a new identity. Restore the default
evidence afterward with `node tools/offline_reconstruct_proof.mjs`, then
`python3 tools/build_report.py`. Only entropy selection changes; both modes
retain the same generator-exit, private-IPC and fresh reconstruction boundaries.

The proof does not claim secure physical memory erasure. The generator's
process lifetime ends; private JS strings/buffers are not guaranteed zeroized.
The existing OpenSSL bridge writes permitted private temporary files and removes
them in `finally`. No secret-bearing QR, phrase, entropy, seed or private key is
printed or retained in report/output files. Sensitive values appear only as
SHA-256 digests. The proof uses real crypto, not a mocked verifier.

Kernel isolation attempt: `unshare -n true`, exit
1, stderr `unshare: unshare failed: Operation not permitted`.
The actual fallback is fresh processes, clean minimal environment, temporary cwd
and no attempted DNS/network calls. This proves local input sufficiency under
that execution, **not** a kernel-enforced air gap, monitored absence of packets
or absence of malicious dependency behavior.

```json
{
  "identity_id": "b1:n4xq6w26e76t5acvynw7dsf6c53pm6nc2detgqihszkcjqkvweja",
  "birth_bytes": 3683,
  "birth_sha256": "0b1f3ba2529fd7695ef872941a9d6e421ab167ba9f2a3cfd89b84b8c9e9b8e7e",
  "ml_public_sha256": "5b562a1de433ffa495a1a5d08b8fbabdca62484780ad5424b6c40a6ea5c7c4fa",
  "slh_public_sha256": "53bae6c817b0cdff658fc045ad3e39d90b4ddc05bb60be4fd709eaaa94fdd7d8",
  "entropy_sha256": "66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925",
  "capsule_sha256": "857e9e2bddf6bed2afbb7f598f6c0df6dacd361226505d07f846942eefad266e",
  "capsule_bytes": 37,
  "signature_bytes": [
    {
      "algorithm": "ML-DSA-87",
      "bytes": 4627
    },
    {
      "algorithm": "SLH-DSA-SHAKE-256s",
      "bytes": 29792
    }
  ],
  "verdicts": {
    "words_entropy_capsule_equal": true,
    "birth_byte_identical": true,
    "identity_id_identical": true,
    "public_key_hashes_identical": true,
    "before_signatures_verify_both_families": true,
    "after_signatures_verify_openssl_both_families": true,
    "tampering_rejected_both_families": true,
    "recovery_api_same_identity": true,
    "recovery_event_authority_valid": true,
    "generator_exited_before_reconstruction": true,
    "fresh_process_and_directory": true
  },
  "openssl": "OpenSSL 3.5.5 27 Jan 2026 (Library: OpenSSL 3.5.5 27 Jan 2026)",
  "isolation": {
    "attempted_command": "unshare -n true",
    "exit_code": 1,
    "stderr": "unshare: unshare failed: Operation not permitted",
    "kernel_network_namespace": false,
    "actual": "fresh generator exits; fresh reconstruction process; temporary cwd; minimal environment; no DNS or network calls attempted",
    "limitation": "network access was not blocked by the kernel; absence of attempted calls is code inspection, not a packet trace"
  }
}
```

## 8. Remaining open assumptions

| Assumption | Concrete consequence if false |
|---|---|
| At least one root signature family remains secure; shared hash/KDF/implementation assumptions hold | Dual quorum does not protect against shared failures or full root compromise; century-long verification may fail. |
| Root entropy has the intended strength and remains private | Low entropy permits search; leaked entropy gives both root signing keys immediately. |
| Printed QR survives and a decoder supports exact binary data | The public dense L symbol or a damaged backup may be unreadable; PNG round trips are not paper-aging or camera tests. |
| The experimental header's exact layout and original implementation remain archived | Future readers may not reconstruct canonical Birth correctly; preserve source/spec/wordlist alongside institutional documentation, not through a required online lookup. |
| A trusted expected ID or physical provenance exists when associating a descriptor with an actor | Whole-QR substitution is undetectable from internal consistency alone. |
| Current authority is not inferred from an original-root-only QR | Otherwise stale/rotated roots can be mistaken for current authority; authenticated log history is necessary for that separate task. |
| The execution platform and dependency code behave as inspected | Process separation alone cannot exclude malware, covert network use, swap retention or side channels. |
| New algorithm support and historical transitions are preserved through future revisions | Fixed BRTH-1 algorithm labels do not themselves deliver genuine algorithm agility across a century. |

## 9. Founder decision request

1. Should R1 distinguish private recovery from public verification as two products? **Recommend yes**, with explicit custody labels and no public seed.
2. Should the 37-byte private capsule proceed to physical backup testing? **Recommend yes**, as private-only experimental packaging retaining both existing root families.
3. Should the 2693-byte binary public descriptor proceed to scanner testing? **Recommend yes for research only**, with original-root binding and no signed/current-authority claim.
4. Should a single QR remain mandatory for a self-contained public signed assertion? **Recommend acknowledge measured infeasibility for these uncompressed standard packages** and request a separate scope decision before alternative packaging.
5. Should century-scale guarantees be replaced by an explicit archival/succession plan? **Recommend yes**; retain historical transitions and require a future reviewed protocol revision for new algorithms.

## 10. Reproduction index

| Evidence/table/number | Exact command (from `experimental/brth-qr/` unless noted) | Generated evidence |
|---|---|---|
| QR capacities; all key/signature/base64/base32 sizes; exact shortfalls; fit and PNG decode tables/counts; construction lengths | `python3 tools/measure_qr.py` | `out/measurements.json`, `out/measurements.md`; implementation `tools/measure_qr.py`, `tools/payloads.mjs`, `tools/capsule.mjs` |
| Original identity/roots/Birth byte count; both signature sizes; fresh-process/continuity verdicts; isolation result | `node tools/offline_reconstruct_proof.mjs` | `out/offline_proof.json` |
| Byte-for-byte default reproducibility (fixed public test entropy; random opt-in: `--random`) | `node tools/offline_reconstruct_proof.mjs` twice; after the first run `cp out/offline_proof.json .work/offline-proof-first.json`; after each run `sha256sum out/offline_proof.json`; then `cmp .work/offline-proof-first.json out/offline_proof.json` | `out/validation.txt` records both digests and comparison exit status |
| Every embedded evidence figure | `python3 tools/build_report.py` | this report, directly embedding both evidence files |
| Existing #3 regression counts, actual run | `cd ../brth-layer4 && npm install && npm test` | `out/validation.txt` records the actual observed output; tests/source unchanged |
| New R1 test counts, live encoder boundaries, secret absence and report equality | `node --test test/` | actual command output in `out/validation.txt`; `test/brth_qr.test.mjs` |
| Whitespace and scope | `git diff --check` and `git status --short --ignored` | actual command output in `out/validation.txt` |

Manual inspection covers capsule field boundaries, no network APIs in the proof,
private/public custody, report arithmetic and changed-file scope. No physical
print/scanner, browser, production, deployment or human acceptance test is claimed.
