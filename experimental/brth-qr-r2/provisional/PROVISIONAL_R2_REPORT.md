# BRTH R2 — provisional findings report (non-repo, honest partial deliverable)

**Status:** PROVISIONAL. This is **not** the committed R2 repository slice.
The committed slice (`experimental/brth-qr-r2/` in `Fisker1111/Punkto`) could **not** be
produced because the Codex CLI account quota was exhausted during the run
(reset **Nov 4, 2026 8:02 AM**). Every finding below was executed and verified with the
**unchanged** Layer-4 implementation (`experimental/brth-layer4/`) and real QR
encoders/decoders. Nothing here is estimated.

**Hermes Kanban task:** `t_5aa58922`
**Source of truth:** CEO-OS issue #40

---

## 1. Scope, layering and non-goals

- Layer 4 (BRTH) only. No Punkti Layer-3 change, no protocol freeze, no production
  publishing, no identity migration, no deployment, no merge.
- No cryptographic invention. ML-DSA-87 and SLH-DSA-SHAKE-256s are used exactly as the
  unchanged Layer-4 implementation uses them.
- The only entropy used is **public, non-secret, deterministic** test material: the
  32-zero-byte TEST seed (every QR artifact) and a 32-byte `0x01` TEST seed (used only
  for the wholesale-substitution demonstration; never encoded into a QR, never printed,
  never committed).
- No real seed, wallet, entropy or private certificate appears in any artifact, log or
  output.

## 2. Binding audit — the six questions of Issue #40 task 1

Epistemic labels: **PROVEN (executed here)** | **MEASURED (from R1)** |
**UNPROVEN / NOT CLAIMED**.

### Q1 — Can a verifier reconstruct and hash the canonical Birth from the descriptor alone?

**PROVEN (executed).** Yes.

The `BRQ1D` layout is `5 ASCII bytes "BRQ1D"` + 32-byte SHA3-256 canonical-Birth digest
+ 2592-byte ML-DSA-87 public key + 64-byte SLH-DSA-SHAKE-256s public key = **2693
bytes**. The unchanged Layer-4 `buildBirth()` is a pure function of the two public keys
plus fixed constants (`type`, `v`, `suite`, `root.threshold = 2`, algorithm order), so
the descriptor alone suffices.

Executed evidence (zero-seed TEST identity):

| Check | Result |
|---|---|
| Rebuilt canonical Birth bytes identical to the original | **true** |
| Carried digest equals the recomputed SHA3-256 digest | **true** |
| IdentityID | `b1:n4xq6w26e76t5acvynw7dsf6c53pm6nc2detgqihszkcjqkvweja` |

### Q2 — What does the carried digest actually bind?

**PROVEN (executed).** The digest is **recomputable from the carried keys**. It is a
self-consistency / corruption / partial-substitution check — **not an external trust
anchor**.

Executed substitution test: a wholly different TEST identity's descriptor (its own keys
plus its own matching digest) verifies internally with a true digest check, while
yielding a different IdentityID
(`b1:yvoch3oos4h5hm4gcui5jqo2w4afusydklyrzlkwwomsf4hxnw6q`).

**Consequence:** a verifier with no external anchor cannot distinguish the intended
actor from a substituted one. Binding to a *specific intended actor* requires an
external anchor.

### Q3 — Does it prove possession, current authority or freshness?

**PROVEN (executed).** No. The descriptor contains **zero signature bytes** and carries
no authenticated log head, no revocation status and no succession evidence. It proves
neither that the bearer holds the private keys, nor that these roots are the current
authority, nor anything about freshness.

### Q4 — Single-family `BRQ1M`

**PROVEN (executed) — binding is UNPROVEN for `BRQ1M`.**

The single-ML descriptor (`"BRQ1M"` + digest + 2592-byte ML public key = 2629 bytes)
**cannot** reconstruct the canonical Birth: the Layer-4 canonical Birth requires **both**
root public keys (2-of-2 dual family). Rebuilding from a `BRQ1M` payload raises
`root quorum`. Its advertised digest therefore **cannot be checked against the canonical
Birth from its own contents**. `BRQ1M` is a diagnostic comparison only, not a
construction.

### Q5 — Offline self-containment vs. verification of an unknown actor's current authority

- **OFFLINE SELF-CONTAINMENT — PROVEN (executed).** The descriptor alone rebuilds the
  canonical Birth, the IdentityID and both public keys offline, and can verify
  signatures made by those roots over a separately supplied message. (Verifying a
  *separately supplied* signed assertion is outside the one-QR-alone claim.)
- **CURRENT AUTHORITY OF AN UNKNOWN ACTOR — UNPROVEN / NOT CLAIMED.** No single
  descriptor can establish this. It requires the authenticated append-only authority log
  (succession, revocation, root rotation), which a descriptor does not carry. R1 already
  recorded this limitation; R2 confirms it holds.

### Q6 — Smallest safe fix, or the explicit external proof requirement

**MEASURED (R1) + PROPOSED (this audit).** No new algorithm and no invented certificate.

Options that do not weaken the dual-family requirement:

1. **External trust anchor.** Publish the descriptor's digest / IdentityID in the
   authenticated authority log, so substitution becomes detectable against an
   independently obtained expected ID.
2. **Out-of-band signed public assertion.** Carry the descriptor digest plus identity
   metadata, signed with the already-standard ML-DSA-87 root key, with the **signature
   delivered out of band** (log atom / link) rather than inside the same QR.

Byte-budget reality (R1, measured on a real encoder):

| Item | Bytes |
|---|---|
| `BRQ1D` descriptor | 2693 (fits v40-L **only** in raw byte mode) |
| ML-DSA-87 signature | 4627 |
| SLH-DSA-SHAKE-256s signature | 29792 |
| Single-family pk + signature in one QR | **does not fit** |
| Dual-family pk + signature in one QR | **does not fit** |
| base64/base32 textual encoding of the descriptor | **does not fit** at any EC level |

## 3. Test artifacts (Issue #40 task 2)

All from the public zero-seed TEST vector only. Every artifact is labelled **TEST ONLY**.

| Artifact | Payload | Bytes | Payload SHA-256 | QR | EC | Modules |
|---|---|---|---|---|---|---|
| `BRQ1S` private backup | `"BRQ1S"` + 32 zero bytes | 37 | `857e9e2bddf6bed2afbb7f598f6c0df6dacd361226505d07f846942eefad266e` | v3 | L | 29/side |
| `BRQ1D` public descriptor | header + digest + both public keys | 2693 | `5b52c6a6be822f047e82cf62764966016c8d5c22c9fa3c54825d1173ed27b91c` | v38 | L | 169/side |

Expected TEST IdentityID:
`b1:n4xq6w26e76t5acvynw7dsf6c53pm6nc2detgqihszkcjqkvweja`

Physical print sizes (width = (modules + 2 x border) x module size, border 4):

| Code | 0.4 mm/module | 0.5 mm/module |
|---|---|---|
| `BRQ1S` | 14.8 x 14.8 mm | 18.5 x 18.5 mm |
| `BRQ1D` | 70.8 x 70.8 mm | 88.5 x 88.5 mm |

Encode → decode round trip, two independent real decoders:

| Code | zxing-cpp byte-identical | OpenCV byte-identical | Verdict |
|---|---|---|---|
| `BRQ1S` | yes | yes | decoded |
| `BRQ1D` | yes | **no** | decoded (OpenCV failure is a **decoder limitation** at this density, not a QR-level failure) |

This reproduces R1's measured zxing-cpp/OpenCV split at v38 density.

## 4. Physical scanning status — UNTESTED

**No physical print, camera or phone scan was performed by the project.**

This is a verified environment fact, not an assumption. Checks run on the build host:

```
$ which lpstat            -> (not found)
$ ls /etc/cups             -> No such file or directory
$ ls /dev/video*           -> No such file or directory
$ lsusb                   -> Bus 001 Device 001: 1d6b:0001 Linux Foundation 1.1 root hub   (only)
$ which scanimage          -> (not found)
$ systemctl list-units | grep -E 'cups|print|scan' -> only dev-ttyprintk.device (virtual console tty)
```

There is no printer, no scanner and no camera on this host, so the Issue's task-4
fallback applies. The deliverable is therefore a **printable A4 test sheet** plus a
**fully offline independent scan verifier**, with the physical test left to an opt-in
volunteer.

A **browser-rendering round trip** was performed (Chrome for Testing rendered the sheet;
the rendered pixels were decoded back out of a screenshot). All three rendered codes
decoded byte-identically. **This is not a physical scan** and is not presented as one.

### Printable test sheet (one A4 page)

- `brth_r2_TEST_ONLY_test_sheet.pdf` / `.html` — one A4 page containing the
  `TEST ONLY — NOT A SECRET — DO NOT USE AS A WALLET` banner, the expected TEST
  IdentityID, all four code renderings with physical dimensions and payload SHA-256
  printed alongside, the volunteer phone-test steps, and the custody comparison table.
- Rendering verified by Chrome for Testing (`/home/hermes/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`).
  The PDF's extracted text layer contains the banner, the IdentityID and both SHA-256
  values.

### Offline independent scan verifier

`scan_verify.py` accepts either an **image** of a scanned code or a file of **raw
decoded bytes** (hex or base64, for phone apps that can only export text). It decodes
with zxing-cpp and OpenCV (treating a single-decoder failure as a decoder limitation),
prints the payload length and SHA-256, detects the header, and delegates every
cryptographic reconstruction to the unchanged Node Layer-4 implementation
(`verify_payload.mjs`) — Python does not re-implement ML-DSA-87 or SLH-DSA-SHAKE-256s.
It exits non-zero on failure.

Executed self-test on the generated artifacts: **PASS** for both custody classes.

- `BRQ1S` -> custody `PRIVATE BACKUP SECRET`; recovered IdentityID equals the expected
  TEST IdentityID; 24-word round trip true.
- `BRQ1D` -> custody `PUBLIC VIEWER IDENTITY DESCRIPTOR`; canonical Birth reconstructed;
  carried digest equals the recomputed digest (internally consistent); IdentityID equals
  the expected TEST IdentityID.

Isolation: `unshare -n true` -> exit 1, `unshare: unshare failed: Operation not
permitted`. The actual isolation is a fresh process, minimal environment, temporary cwd
and no attempted DNS or network calls. **Kernel network-namespace isolation was not
achieved**; absence of attempted calls is code inspection, not a packet trace.

## 5. Fresh-process identity continuity and mutation rejection (Issue #40 task 5)

All executed against the unchanged Layer-4 code.

- The 24-word form and the QR payload path reconstruct the **same deterministic
  IdentityID**, the same canonical Birth bytes and the same public-key SHA-256 values.
- Mutation / corruption rejection (every expectation met):

| Mutation | Expected | Actual | Meaning |
|---|---|---|---|
| Flip one byte of the carried digest | rejected as inconsistent | `ACCEPTED_INCONSISTENT` | the digest check catches it |
| Flip one byte of the ML public key | rejected as inconsistent | `ACCEPTED_INCONSISTENT` | the digest check catches it |
| Truncate the descriptor | rejected as inconsistent | `ACCEPTED_INCONSISTENT` | the digest check catches it |
| Wholesale substitution with another TEST identity | accepted but different identity | `ACCEPTED_CONSISTENT` | **the documented unproven case** — internally consistent, different IdentityID |
| Flip one byte of the private capsule entropy | silently different identity | `ACCEPTED_DIFFERENT_IDENTITY` | the capsule has **no self-authenticating checksum**; a corrupted entropy yields a valid-looking *different* identity rather than an error |

The last row is a finding worth stating plainly: **the private capsule cannot detect its
own corruption.** Detection must come from comparing the recovered IdentityID against an
independently known expected ID.

Custody differentiation, stated everywhere in the evidence:

- `BRQ1S` = **PRIVATE BACKUP SECRET** — carries the root entropy; custody is private
  only; loss or copying is loss or copying of root authority.
- `BRQ1D` = **PUBLIC VIEWER IDENTITY DESCRIPTOR** — public keys only; publicly
  displayable; proves no possession, no current authority, no freshness.

## 6. Ranked recommendation (Issue #40 task 6)

**a. Does a single physical QR meet private recovery usability?**
**Unproven physically; proven digitally.** The offline/digital side is **PROVEN**: the
`BRQ1S` capsule is 37 bytes (QR v3, 29 modules/side, 14.8 mm at 0.4 mm/module), decodes
byte-identically with two independent decoders, and reconstructs the exact IdentityID
offline in a fresh process. But **no physical scan has been performed**, so real-world
phone usability of the private backup remains **UNTESTED**. The printed size is the only
physical variable (a 14.8 mm code at 0.4 mm/module is small for many phone cameras; the
0.5 mm/module, 18.5 mm rendering is the safer default).

**b. Is the binary public descriptor sufficiently robust in actual phone scanning?**
**UNKNOWN / UNTESTED.** The measured reasons it is a live risk:
- 2693-byte **raw binary** payload at **QR v38** (169 modules/side) — 70.8 mm at
  0.4 mm/module, 88.5 mm at 0.5 mm/module;
- error correction **level L** only;
- only **raw byte mode** fits; base64 and base32 textual encodings do **not** fit at any
  EC level, so there is no text-safe fallback for this payload;
- **OpenCV's own detector failed** to read it at this density while zxing-cpp succeeded
  — so even desktop-grade decoders disagree at this density (MEASURED);
- a phone app that only exports **text** will corrupt or refuse the payload.

Conclusion: physical robustness is a genuine open question, and a binary-safe capture
path (an app that returns raw bytes) is a prerequisite, not a detail.

**c. Is a one-QR *signed* public assertion feasible under established standard algorithms
and the physical constraints?**
**No — and this is measured, not assumed.** The descriptor alone is 2693 bytes and fits
v40-L only in raw byte mode. An ML-DSA-87 signature is 4627 bytes and a
SLH-DSA-SHAKE-256s signature is 29792 bytes, so even the *smallest* standard NIST
pk+signature package does not fit one QR, and the dual-family package is far out of
range. The consequence: a signed public assertion must carry its signature **out of
band** (a log atom or a link), with the QR carrying the descriptor and the verifier
fetching/holding the signature separately. **This is a scope decision for the Founder**;
this slice does not and may not decide it, and it does not silently drop the dual-family
requirement or invent a compression/packing scheme.

**d. Unresolved PQ authority-succession / century-scale assumptions**

| Assumption | If false |
|---|---|
| ML-DSA-87 and SLH-DSA-SHAKE-256s remain break-resistant for the required horizon | the root identity becomes forgeable in the future; century-scale survival needs an explicit agility/succession plan |
| The authenticated authority log survives and remains available | current authority, revocation and succession cannot be established at all; a descriptor alone never suffices |
| Root succession/rotation is possible without breaking `IdentityID` | a compromised or dead root cannot be replaced while preserving the identity |
| Paper (or whatever medium the QR ends up on) survives physically for the intended period | the private backup is lost; loss is loss of root authority, since the 24 words and the capsule are the same entropy |
| The private capsule remains in private custody | anyone who scans it holds bearer root authority; the "private" qualifier is the whole security boundary |
| The paper artefact can be read at all (optics, module size, print quality) | recovery fails even though the cryptography is correct — which is exactly what the volunteer test measures |

**This does not weaken the Q-day requirements.** It states honestly that a *signed*
public assertion inside a single QR is not achievable with the current standard
packages, which is a finding about the original one-QR ambition that the Founder must
act on, not something this slice may soften.

## 7. What a future physical test must record

To close the untested physical questions, the volunteer must record per code: the
scanner app and version, whether it returns raw binary bytes, distance in cm, angle,
lighting condition, success/failure, and the SHA-256 of the recovered bytes. The
offline verifier already prints the expected SHA-256 for each code.

## 8. What is still missing, and why

The committed R2 repository slice — `experimental/brth-qr-r2/` with
`tools/binding_audit.mjs`, `tools/make_test_artifacts.py`, `tools/print_sheet.py`,
`tools/scan_verify.py` + `tools/verify_payload.mjs`, `tools/identity_continuity.mjs`,
`tools/build_report.py`, `test/brth_qr_r2.test.mjs`, the tracked test sheet and the
generated report — **was not produced**, because the Codex CLI account quota was
exhausted during the run and repository/code work must be delegated to Codex.

What *was* produced is the equivalent logic as **provisional, non-repo** tools outside
the repository, with every result executed and verified, so that the Founder can inspect
the findings now and the committed slice can be rebuilt from the normative spec
(`experimental/brth-qr-r2/SPEC_R2.md`, pushed on branch `research/brth-qr-r2`) once quota
is available.

**Not claimed anywhere in this report:** any physical print, camera or phone scan
success; any production deployment; any protocol freeze; any claim that a one-QR signed
public assertion is feasible.
