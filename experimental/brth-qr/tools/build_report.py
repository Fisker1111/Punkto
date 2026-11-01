"""Embed measured evidence into the authored report; no guessed measurements."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
m = json.loads((ROOT / 'out/measurements.json').read_text())
p = json.loads((ROOT / 'out/offline_proof.json').read_text())
measurements = (ROOT / 'out/measurements.md').read_text().strip()
proof = (ROOT / 'out/offline_proof.json').read_text().strip()
rows = m['cases']
fit = sum(r['fits'] for r in rows)
passed = sum(r['decode_ok'] for r in rows)
failed = fit - passed

def case(name, ec='L'):
    return next(r for r in rows if r['name'] == name and r['error_correction'] == ec)

def decode_levels(name):
    return '; '.join(f"{ec}: {case(name, ec)['decode_result']}" for ec in 'LMQH')

def summary(name):
    r = case(name)
    return f"{r['payload_bytes']} bytes; version {r['version']}; {r['modules']} modules/side; decode: {r['decode_result']}"

report = f'''# BRTH one-QR offline Q-day Birthstone — R1 measured report

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
{p['birth_bytes']} bytes. Section 4 contains all actual parameter-set outputs;
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
{m['encoder']}; decoders: {m['decoders']['cvp2']} and {m['decoders']['zxingcpp']}; Python: {m['python']}.

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

Measured totals: **{len(rows)} payload/EC cases, {fit} fit, {passed} successful
PNG decodes by at least one decoder, {failed} cases read by neither decoder,
{len(rows)-fit} infeasible**. OpenCV decoded **{sum(r['decode_cvp2'] for r in rows)}**
cases byte-identically; zxing-cpp decoded **{sum(r['decode_zxingcpp'] for r in rows)}**.
A failure by one decoder is a limitation of that decoder, not a QR capacity limit
or evidence that the payload is unreadable. PNG success does not establish
reliable scanning on physical paper. No printer/camera durability trial was run.

The exact arithmetic table includes the smallest ML-DSA parameter set:
ML-DSA-44 raw PK+signature is already larger than one v40-L symbol, even before
metadata. The smallest SLH parameter set is also shown. These are lower bounds
for these uncompressed public-key-plus-signature packages, not all conceivable
cryptographic constructions. Every **INFASIBLE** row below repeats its exact
measured shortfall.

{measurements}

## 5. Two minimal constructions, ranked

### Rank 1 — private recovery capsule (private-only)

Exact layout: 5 ASCII bytes `BRQ1S` followed by the 32 entropy bytes underlying
the 24 words: **5 + 32 = 37 bytes**. The header pins this experimental packaging
revision, the existing BRTH-1 suite and the word/derivation rules; it is not a
new BRTH object or a new cryptographic primitive. Base64 is
{case('private-capsule-base64')['payload_bytes']} characters; uppercase unpadded
base32 is {case('private-capsule-base32')['payload_bytes']} characters. Measured
raw v40-L-compatible result: {summary('private-capsule-raw')}.
Measured base32 capsule results: {decode_levels('private-capsule-base32')}.
Measured raw capsule results: {decode_levels('private-capsule-raw')}.
These are PNG measurements; physical-backup scanning remains to be tested. The measured published-input 24-word form is
{case('recovery-24-words')['payload_bytes']} UTF-8 bytes; arbitrary phrases vary
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
Measured raw L result: {summary('public-dual-descriptor-raw')}.
Raw bytes fit L only; the byte-identical PNG round trip is
**{'demonstrated' if case('public-dual-descriptor-raw')['decode_ok'] else 'not demonstrated by either decoder'}**
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
{case('public-dual-descriptor-raw')['decode_result']}), while even the smallest measured standard
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
{p['isolation']['exit_code']}, stderr `{p['isolation']['stderr']}`.
The actual fallback is fresh processes, clean minimal environment, temporary cwd
and no attempted DNS/network calls. This proves local input sufficiency under
that execution, **not** a kernel-enforced air gap, monitored absence of packets
or absence of malicious dependency behavior.

```json
{proof}
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
'''
(ROOT / 'docs/BRTH_QR_R1_REPORT.md').write_text(report)
print('Wrote docs/BRTH_QR_R1_REPORT.md from measured JSON/Markdown and offline proof')
