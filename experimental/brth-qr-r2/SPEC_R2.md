# SPEC — BRTH one-QR R2: physical QR scan test + public-descriptor binding audit (test vectors only)

Status: NORMATIVE SPEC for the Codex implementation run.
Source of truth: CEO-OS issue #40 (Founder GO, P2, research-only).
Base: branch `research/brth-qr-r1` (commit `fe28414f59fd9b31763fd32623246bb0559dbad2`),
which contains the accepted R1 slice under `experimental/brth-qr/` and the unchanged
Layer-4 reference under `experimental/brth-layer4/`.

## 0. Stop rule (read first)

If an acceptance item below cannot be met with a REAL measurement, REAL cryptography or a
REAL file on disk, STOP and report the exact blocker instead of relaxing a requirement,
inventing a number, claiming a physical scan that did not happen, or substituting a toy
algorithm. Do not weaken Q-day, identity-continuity or offline self-containment
requirements. Do not silently expand scope. Do not claim real-world phone scanning
unless actual physical optics were exercised.

## 1. Scope and boundaries

- Research-only. This slice touches **Layer 4 (BRTH) only**.
- ALL new tracked files live under `experimental/brth-qr-r2/`. No tracked file outside
  that directory may be modified or deleted. `experimental/brth-qr/` and
  `experimental/brth-layer4/` are READ-ONLY inputs: you may import them, never edit them.
- Explicitly permitted untracked/gitignored build artefacts (add a `.gitignore` inside
  `experimental/brth-qr-r2/` listing `node_modules/`, `.work/`, `__pycache__/`,
  `out/*.tmp`, `out/*.png`, `out/*.pdf` before creating them):
  - `experimental/brth-layer4/node_modules/` (already gitignored there) — required by
    `npm install` in `experimental/brth-layer4/`;
  - `experimental/brth-layer4/.tmp/` (already gitignored there) — hard-coded temp dir of
    `experimental/brth-layer4/tools/pq-openssl.js`;
  - `experimental/brth-qr-r2/.work/` and `experimental/brth-qr-r2/out/*.tmp`.
  `git status --short` must show only `experimental/brth-qr-r2/` entries, and no ignored
  artefact may be committed.
- No Punkti Layer-3 change, no protocol freeze, no main merge, no production publishing,
  no identity migration, no deployment, no PR, no push, no GitHub post, no Notion
  write-back. The Hermes worker does commit, push, PR and write-back itself.
- No cryptographic invention. Only the algorithms already used by
  `experimental/brth-layer4` (ML-DSA-87, SLH-DSA-SHAKE-256s) and the unchanged Layer-4
  CJSON/BIP39/HKDF-SHA-512 machinery. No new certificates, no new hash-to-curve scheme,
  no non-standard packing invented to make a QR fit.
- Existing production Ed25519 signatures remain explicitly NON-post-quantum.

## 2. TEST-VECTOR-ONLY HARD RULE

Every QR artifact produced by this slice encodes **test vectors only**:

- The private-backup QR encodes a capsule built from the **deterministic, published,
  non-secret TEST seed: 32 zero bytes (256 zero bits)** — the same public test vector
  R1 already used. It is NOT a secret and MUST NOT be described as one.
- The public-descriptor QR encodes the public descriptor of that same TEST identity.
- **Never** generate, print, log, commit or reference a real signing seed, real entropy,
  a user wallet, a real QR secret or a private certificate. Never write a real
  `--random` entropy run into any committed file.
- Every artifact must carry a visible `TEST ONLY` label (inside the printable sheet,
  in the filename, and in the SVG/PNG/PDF metadata where feasible) and must state that
  the TEST identity must never be used as a wallet, credential or real identity.
  Precisely: this filename rule applies to the PRINTABLE/SCANNABLE ARTIFACTS — the
  test sheet (PDF/HTML/SVG), the QR code image files (SVG/PNG) and any per-code file
  exported for a volunteer. Every one of those filenames MUST contain the literal
  token `TEST_ONLY`. It does NOT apply to machine-readable evidence files
  (`out/*.json`, `out/*.md`), to source files under `tools/`, `test/` or `docs/`, or to
  the spec and report markdown files themselves.
- Every artifact and its metadata records the SHA-256 of the *encoded payload bytes* so
  a scanned result can be compared byte-for-byte later.
- The generated artifacts are **research artifacts for an opt-in volunteer phone test**.
  They are published in a repository; that is intentional and is exactly why they are
  labelled TEST ONLY and derived from a public zero seed.

## 3. Binding audit (task 1 — audit truthfulness FIRST)

Deliverable: `tools/binding_audit.mjs` plus a machine-readable
`out/binding_audit.json` and a report section.

The audit MUST answer, with executable evidence, these questions:

1. **Can a verifier reconstruct and hash the canonical Birth solely from the public
   descriptor bytes?** Determine this from the code, not from prose. Specifically:
   the `BRQ1D` layout is `5 ASCII bytes "BRQ1D"` + 32-byte SHA3-256 canonical-Birth
   digest + ML-DSA-87 public key (2592 bytes) + SLH-DSA-SHAKE-256s public key
   (64 bytes) = 2693 bytes. The unchanged `experimental/brth-layer4` `buildBirth`
   takes exactly the two public keys plus fixed constants (`type`, `v`, `suite`,
   `root.threshold = 2`, algorithm order). So the canonical Birth, its CJSON bytes,
   its SHA3-256 digest and its `IdentityID` are all RECOMPUTABLE from the descriptor
   alone. Prove this by executing it and asserting byte equality with the original
   identity's canonical Birth, digest and IdentityID.
2. **What does the carried digest actually bind?** State plainly that the digest is
   RECOMPUTABLE from the carried keys, i.e. it is a self-consistency / corruption and
   partial-substitution check, NOT an external anchor. A verifier who trusts nothing
   external can be fed a fully substituted (keys + matching digest) descriptor that
   still verifies. Demonstrate this with an executable "wholesale substitution" case:
   a second, different TEST identity's descriptor verifies internally with a true
   digest check while pointing at a different `IdentityID`.
   For this demonstration ONLY, the second identity may be derived from a second
   PUBLIC, NON-SECRET, DETERMINISTIC test seed that is not the zero seed (for example
   32 bytes of `0x01`). It is never encoded into any QR artifact, never printed and
   never committed as secret material; only its public descriptor and its public
   `IdentityID` appear in the evidence. No random entropy may be used.
3. **Does it prove current authority, possession or freshness?** No. The descriptor
   contains NO signature. It proves neither that the bearer holds the private keys
   (no proof of possession), nor that these roots are the current authority (no
   authenticated log head, no successor/succession evidence, no revocation status).
   The audit MUST state this explicitly and MUST NOT let any text imply otherwise.
4. **Single-family `BRQ1M` comparison.** The single-ML public descriptor
   (`"BRQ1M"` + digest + ML public key only, 2629 bytes) CANNOT reconstruct the full
   canonical Birth, because the Layer-4 canonical Birth requires BOTH root public
   keys. Therefore its advertised digest CANNOT be checked against the canonical
   Birth from its own contents: **binding is UNPROVEN for `BRQ1M`**. Execute this and
   record it. Do not present `BRQ1M` as a construction.
5. **Offline self-containment vs. unknown-actor current authority.** Evaluate and
   separate two different claims:
   - OFFLINE SELF-CONTAINMENT for identity reconstruction: what the descriptor alone
     can rebuild (canonical Birth, `IdentityID`, both public keys, and the ability to
     VERIFY signatures made by those roots over any message supplied separately) —
     state this as supported, with the caveat that verification of a separately
     supplied signed assertion is outside the one-QR-alone claim;
   - VERIFICATION OF AN UNKNOWN ACTOR'S CURRENT AUTHORITY: state that this is NOT
     supported by any single descriptor, because it needs the authenticated append-only
     authority log (succession, revocation, root rotation), which a descriptor does not
     carry. Be explicit that R1's own report already recorded this limitation.
6. **Smallest safe fix or explicit external proof requirement.** Propose, without
   inventing new algorithms, the smallest safe option(s) and the explicit external
   proof requirement:
   - an external trust anchor for the descriptor (e.g. the descriptor's
     `IdentityID`/digest being published in the authenticated authority log, so
     substitution is detectable against an independently obtained expected ID); and/or
   - a signed public assertion carrying the descriptor's digest + identity metadata,
     verified with the already-standard ML-DSA-87 root key, where the signature lives
     OUT of band (log atom / link) rather than inside the same QR.
   State the byte-budget reality from R1's measured numbers: the descriptor alone is
   2693 bytes and already fits version 40 level L only in RAW byte mode; a
   ML-DSA-87 signature is 4627 bytes and a SLH-DSA-SHAKE-256s signature is 29792
   bytes, so a single-family pk+signature package does NOT fit one QR, and
   base64/base32 textual encodings of the descriptor do NOT fit either. Do not
   propose a compression or packing scheme that is not already standard, and do not
   silently drop the dual-family requirement.

Every claim above must be backed by an executed assertion or a measured number, and
must be labelled with which of the three epistemic statuses it has:
**PROVEN (executed here)**, **MEASURED (from R1's committed measurements)**,
or **UNPROVEN / NOT CLAIMED**.

## 4. Reproducible printable/scannable test artifacts (task 2)

Deliverables (all under `experimental/brth-qr-r2/`):

- `tools/make_test_artifacts.py` — generates, from the public zero-seed TEST vector
  only, the printable/scannable artifacts:
  - `BRQ1S` private-backup capsule QR (37 bytes payload: `"BRQ1S"` + 32 zero bytes),
    which R1 measured as a version-3, 29-modules-per-side code;
  - `BRQ1D` public-descriptor QR for the same TEST identity (2693 bytes payload).
  Requirements:
  - Use the real encoder `segno` 1.6.6 (interpreter path in §7). Binary byte mode for
    the raw payloads; do NOT switch to base64/base32 text for the descriptor (R1
    measured that textual encodings do not fit at any EC level) — record that fact.
  - Emit BOTH PNG and SVG for each code, at a module scale that makes the physical
    module size explicit, and record for each artifact: payload bytes, payload
    SHA-256, QR version, error-correction level, modules per side, border/quiet
    zone, and the printed physical size in millimetres.
    Output paths: the raster PNG copies go to `out/` with `TEST_ONLY` in the
    filename (gitignored); the vector SVG copies are written by
    `tools/print_sheet.py` into the tracked directory
    `docs/brth_qr_r2_TEST_ONLY_test_codes/` (see §4's print-sheet bullet).
  - Compute the physical print size honestly: physical width mm = (modules + 2 x
    border) x module_mm. Recommend at least two module sizes (e.g. 0.4 mm/module and
    0.5 mm/module) and state the resulting paper sizes for both codes, so a volunteer
    can pick a printer scale that is actually printable.
  - Every artifact must carry the `TEST ONLY` label and the payload SHA-256 in the
    printable sheet next to the code (never INSIDE the QR payload).
  - Write a machine-readable `out/artifacts.json` with the same facts.
  - The generator MUST verify each generated image by decoding it back with at least
    one real decoder (`zxingcpp`, and additionally `cv2` where it can) and asserting
    byte-identical recovery of the payload. Record per-decoder results honestly; a
    decoder failure must be reported as a decoder limitation, never as "QR unreadable".
- `tools/print_sheet.py` — builds a concise, printable A4 test sheet, written to
  **tracked** paths so a volunteer can actually obtain it:
  - `docs/brth_qr_r2_TEST_ONLY_test_sheet.pdf` (the printable sheet),
  - `docs/brth_qr_r2_TEST_ONLY_test_sheet.html` (the source used to render it),
  - `docs/brth_qr_r2_TEST_ONLY_test_sheet.svg` (a vector alternative that opens in any
    browser and prints at exact physical size), plus the embedded QR codes as SVG in
    `docs/brth_qr_r2_TEST_ONLY_test_codes/` (SVG is text, diffable and print-exact).
  These `docs/` files are TRACKED deliverables (not gitignored) and contain only
  test-vector material. The PNG raster copies stay in `out/` (gitignored, and their
  filenames also contain `TEST_ONLY`).
  The sheet must contain:
  - a clear `TEST ONLY — NOT A SECRET — DO NOT USE AS A WALLET` header;
  - the private-backup TEST QR and the public-descriptor TEST QR, each at the two
    recommended module sizes with the physical dimensions and payload SHA-256 printed
    alongside, plus the expected `IdentityID` of the TEST identity;
  - a short, explicit step list for a volunteer WITH A PHONE (print at 100% / "actual
    size", do not scale-to-fit; scan with the phone's stock camera; for the public
    descriptor use a scanner app that returns RAW BINARY bytes and record which app,
    because a text-only scanner will corrupt a 2693-byte binary payload; write down
    the app name, the distance, the angle, the lighting and success/failure);
  - the exact offline verifier command and what a pass/fail means;
  - an explicit statement that no physical scan has been performed by the project and
    that the sheet is the opt-in physical test.
  Render the PDF with the locally available Chrome for Testing binary (locate it
  under `/home/hermes/.cache/ms-playwright/chromium-*/chrome-linux64/chrome`; verify
  the exact path first). Verify the produced PDF exists, is non-trivial in size, and
  contains the expected strings.

## 5. Offline independent scan verifier (task 4 fallback)

Deliverable: `tools/scan_verify.py` — a simple, fully OFFLINE verifier that a
volunteer (or the project later) can run against a scan result, with no network and no
Punkti dependency. It MUST:

- Accept EITHER an image file (PNG/JPG of the scanned code) OR a file of raw decoded
  bytes (so a volunteer whose phone app can only export text can paste hex/base64).
- Decode with `zxingcpp` (and `cv2` where it can) when given an image, and treat a
  single-decoder failure as a decoder limitation, not as a QR-level failure.
- Print the decoded payload length, the payload SHA-256 and the detected header
  (`BRQ1S` / `BRQ1D` / unknown) WITHOUT ever printing secret material.
- **Implementation constraint:** the Layer-4 PQ cryptography (ML-DSA-87,
  SLH-DSA-SHAKE-256s) exists only in the unchanged Node implementation under
  `experimental/brth-layer4/`. Python must NOT re-implement it. Therefore
  `tools/scan_verify.py` performs decoding/hashing/format checks in Python and
  delegates every cryptographic reconstruction to a Node helper
  `tools/verify_payload.mjs` (in the same directory) invoked as a child process,
  which reads the payload bytes on stdin and prints a JSON result on stdout
  (never secret material). The Python side parses that JSON. Use the same
  `minimal` environment pattern as R1's
  `experimental/brth-qr/tools/offline_reconstruct_proof.mjs` when spawning Node.
- For `BRQ1S` (private backup): reconstruct the identity offline through the unchanged
  Layer-4 code and report the recovered `IdentityID`, plus whether it equals the
  expected TEST `IdentityID`.
- For `BRQ1D` (public descriptor): recompute the canonical Birth from the carried
  keys, recompute the digest, compare it with the carried digest, and report the
  `IdentityID` and whether the digest binding is internally consistent.
- Clearly label the two custody classes in its output: `PRIVATE BACKUP SECRET` vs
  `PUBLIC VIEWER IDENTITY DESCRIPTOR`, and state that a `BRQ1D` result proves neither
  possession nor current authority.
- Exit non-zero when a check fails, so it is usable in CI later.
- Prove it is offline: attempt `unshare -n true`; if the kernel forbids it, state the
  actual isolation used (fresh process, minimal environment, no network calls
  attempted) exactly as R1 did, and do NOT claim stronger isolation than was achieved.

## 6. Fresh-process identity continuity + mutation rejection (task 5)

Deliverable: `tools/identity_continuity.mjs` (plus `out/identity_continuity.json`).

Required, all with REAL unchanged PQ cryptography:

1. Build the TEST identity from the 24-word form, and separately from the QR payload
   bytes (obtain those bytes by DECODING a generated artifact image with a real
   decoder, not by copying the payload from a variable), then reconstruct. Assert
   both paths yield the SAME deterministic `IdentityID`, the same canonical Birth
   bytes and the same public-key SHA-256.
   Implementation note: image decoding lives in Python (`zxingcpp` / `cv2`), so the
   Node tool MAY shell out to the `QR_PYTHON` interpreter (R1's `test/brth_qr.test.mjs`
   already does exactly this) to decode the artifact image, and MAY use the returned
   payload bytes. It MUST NOT re-implement the PQ cryptography in Python.
2. Do the reconstruction in a FRESH CHILD PROCESS in a fresh temporary cwd with a
   minimal environment, following the R1 pattern in
   `experimental/brth-qr/tools/offline_reconstruct_proof.mjs` (which you must reuse
   the shape of, not fork the identity logic). The generator process must EXIT before
   reconstruction starts.
3. Mutation / corruption rejection: for each of a set of deterministic mutations
   (flip one bit in the capsule payload, truncate the capsule, flip one byte in the
   descriptor's digest, flip one byte in the descriptor's ML public key, replace the
   descriptor with the OTHER TEST identity's descriptor), assert that the correct
   check REJECTS it (or, for the wholesale-substitution case, assert the honest
   outcome: it is internally consistent but points at a DIFFERENT IdentityID — that is
   the documented unproven case from §3.2, not a "rejection"). Record every case's
   expected-vs-actual outcome in the JSON so the test suite can assert them.
4. Explicitly differentiate `PRIVATE BACKUP SECRET` (the `BRQ1S` capsule, custody:
   private-only, loss/copy = loss/copy of root authority) from `PUBLIC VIEWER IDENTITY
   DESCRIPTOR` (the `BRQ1D` descriptor, custody: publicly displayable, proves no
   possession, no current authority, no freshness). This differentiation must appear
   in the JSON, in the report and in the verifier output.

## 7. Test suite and reproducibility

- `test/brth_qr_r2.test.mjs` — Node test suite asserting every claim in §3, §4, §5 and
  §6 that is mechanically checkable, including:
  - the descriptor reconstructs the canonical Birth byte-identically and the digest
    check passes (PROVEN);
  - the substituted-key descriptor is internally consistent but yields a different
    IdentityID (documented unproven case);
  - the `BRQ1M` descriptor cannot reconstruct the canonical Birth (binding UNPROVEN);
  - `BRQ1S` and `BRQ1D` payloads and their SHA-256 digests are the exact expected
    values for the zero-seed TEST vector, read from `out/artifacts.json`;
  - the generated artifact images decode back byte-identically with at least one
    real decoder;
  - the printable sheet exists at `docs/brth_qr_r2_TEST_ONLY_test_sheet.pdf` (plus its
    `.html`/`.svg` siblings), is non-trivial, and contains the `TEST ONLY` label,
    both payload SHA-256 values, the expected `IdentityID` and the volunteer steps;
  - the continuity/mutation results in `out/identity_continuity.json` match the
    recorded expected outcomes;
  - the report embeds the exact generated JSON/markdown figures (like R1's
    `build_report.py` did) so prose cannot drift from measurements.
- `tools/build_report.py` — regenerate `docs/BRTH_QR_R2_REPORT.md` from the measured
  JSON/Markdown evidence so the report is generated, not hand-typed.
- `README.md` — how to reproduce every number, artifact and test in the R2 report,
  how a volunteer uses the printable sheet, and an explicit "physical scanning is
  UNTESTED" statement.

## 8. Report contents (`docs/BRTH_QR_R2_REPORT.md`)

In this order, with real numbers and explicit epistemic status labels
(PROVEN/MEASURED/UNPROVEN):

1. Scope, layering, non-goals, and the unchanged-R1-baseline statement.
2. Binding audit (all six questions of §3), including the wholesale-substitution
   demonstration and the `BRQ1M` unproven case.
3. Test artifacts: exactly what was generated, from which public TEST vector, the
   payload SHA-256 values, versions/EC/modules/physical mm, and the printable sheet.
4. Physical scanning status: an explicit, prominent statement that NO physical
   print/camera/phone scan was performed by the project, WHY (no printer, no camera or
   scanner is present on the execution host — this is the verified environment fact,
   record the checks you ran and their output), and what remains untested. The
   project must NOT claim any physical success. Every physical claim in this report
   must be framed as a hypothesis for the volunteer test, not as a measurement.
5. Offline continuity and mutation-rejection results (the real outputs).
6. Ranked recommendation (task 6), compact and explicit, answering:
   a. Does a single physical QR meet PRIVATE RECOVERY usability? Answer must reflect
      that physical scanning is UNTESTED and that the offline/digital side is PROVEN.
   b. Is the binary public descriptor sufficiently robust in actual phone scanning?
      Answer must be UNKNOWN/UNTESTED, with the measured reasons (2693-byte binary
      payload, version 38, low EC, only raw byte mode fits, text scanners will corrupt
      it, OpenCV's own detector failed on this density while zxing-cpp succeeded —
      all MEASURED).
   c. Is a one-QR SIGNED public assertion feasible under established standard
      algorithms and the physical constraints? Answer with the R1 byte arithmetic
      (descriptor 2693 bytes; ML-DSA-87 signature 4627; SLH-DSA-SHAKE-256s signature
      29792; a single-family pk+signature package does not fit; the dual-family
      package is far out of range) and the consequence: a signed public assertion must
      carry its signature out of band (log atom / link) — and note this is a scope
      decision for the Founder, not something this slice may decide.
   d. Unresolved PQ authority-succession / century-scale assumptions: list them with
      the consequence if each is false (algorithm survival, root succession, log
      availability, physical survivability of paper, key custody). Do NOT weaken the
      Q-day requirements; state honestly that a one-QR signed public assertion inside
      a single QR is not achievable with the current standard packages and what that
      means for the original one-QR ambition.
7. Remaining open assumptions and the explicit list of what a future physical test
   must record to close them.
8. Reproduction index: every table/number points to the exact command and file.

## 9. Acceptance criteria (the run is complete only when ALL hold)

1. `cd experimental/brth-layer4 && npm install && npm test` still passes unchanged.
   Report the exact pass/fail counts. (This suite is slow — allow up to ~15 minutes.)
2. `cd experimental/brth-qr-r2 && node --test test/` passes with every test green.
3. `python3 tools/make_test_artifacts.py` runs clean, produces `out/artifacts.json`,
   the PNG and SVG artifacts under `out/`, and every artifact decodes
   byte-identically with at least one real decoder.
4. `python3 tools/print_sheet.py` runs clean and produces
   `docs/brth_qr_r2_TEST_ONLY_test_sheet.pdf` (plus the `.html` and `.svg` siblings and
   `docs/brth_qr_r2_TEST_ONLY_test_codes/`) with the `TEST ONLY` labels, both payload
   SHA-256 values, the expected TEST `IdentityID` and the volunteer steps.
5. `node tools/binding_audit.mjs` runs clean and produces `out/binding_audit.json`
   with every §3 question answered and each claim carrying an epistemic status label.
6. `python3 tools/scan_verify.py --self-test` runs clean on the generated artifacts and
   exercises both the `BRQ1S` and the `BRQ1D` path plus at least one deliberate
   corruption that must fail with a non-zero exit.
7. `node tools/identity_continuity.mjs` runs clean and produces
   `out/identity_continuity.json` with all verdicts true and every mutation case
   recording its expected-vs-actual outcome.
8. `python3 tools/build_report.py` regenerates `docs/BRTH_QR_R2_REPORT.md` and the
   report embeds the exact generated evidence.
9. `git diff --check` is clean; `git status --short` shows only
   `experimental/brth-qr-r2/` entries; `git status --short --ignored` shows only the
   permitted build-artefact paths from §1.
10. No secret material anywhere in the diff. The only entropy that may appear in any
    committed file or encoded artifact is PUBLIC, NON-SECRET, DETERMINISTIC test
    material: the 32-zero-byte seed used for every QR artifact, and the second
    32-byte `0x01` seed used ONLY for the §3.2 wholesale-substitution demonstration
    (never encoded into a QR, never printed, never committed as secret material).
    No random entropy may be used anywhere. No real seed, wallet, or private key
    appears in any file, log, or output.
11. No claim of physical scanning anywhere in the report, the README, the code output
    or the comments.

## 10. Environment facts (verify, do not assume)

- Node v26.9.0, npm 12.0.2, OpenSSL 3.5.5.
- QR Python interpreter (has segno 1.6.6, opencv-python-headless 5.0.0, zxing-cpp
  3.1.1, numpy):
  `/home/hermes/.hermes/tools/python-3.14.9+202****1021-linux-x64/bin/python3`
  (the directory name literally contains `****`; verify with `ls`). The other
  interpreter under `/home/hermes/.hermes/tools/` does NOT have segno — do not use it.
  Export it as `QR_PYTHON`.
- Chrome for Testing: locate under `/home/hermes/.cache/ms-playwright/chromium-*/`
  and verify the exact binary path with `ls` before use.
- There is NO printer, NO CUPS, NO scanner and NO camera on this host: `lpstat` is
  absent, `/etc/cups` does not exist, `/dev/video*` does not exist and `lsusb` shows
  only the root hub. This is why §4's printable-sheet fallback applies. Re-verify
  these commands and paste their real output into the report; do not merely assert it.
- `experimental/brth-layer4/node_modules` must exist before running the Node code
  (`npm install` there). `experimental/brth-layer4/.tmp/` is the OpenSSL bridge's
  hard-coded temp dir; it is gitignored and must not be committed.

## 11. Stop condition

When the acceptance criteria hold, STOP and report: files changed, exact commands run
with their real outputs, test counts, the binding-audit verdicts with their epistemic
labels, the artifact inventory with SHA-256 values, the explicit "physical scanning
untested" statement and its reason, the ranked recommendation, and any remaining
blocker. Do NOT commit, push, open a PR, merge, deploy, write to Notion or post to
GitHub — the Hermes worker does the commit, push, PR and write-back itself.
