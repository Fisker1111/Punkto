# SPEC — BRTH one-QR offline Q-day Birthstone, research slice R1

Status: NORMATIVE SPEC for the Codex implementation run.
Source of truth: CEO-OS issue #10 (R1 deliverable list), branch `research/brth-qr-r1`
(base `origin/proposal/brth-layer4`, commit 3e4b20e — the closed CEO-OS #3 reference work).

## 0. Stop rule (read first)

If any acceptance item below cannot be met with *real* measurement or *real* cryptography,
STOP and report the exact blocker instead of relaxing a requirement, inventing numbers,
or substituting a toy algorithm. Do not weaken Q-day, identity continuity or
self-contained/offline requirements. Do not silently expand scope.

## 1. Scope and layering

- Layer 4 (BRTH) only. This task MUST NOT touch Punkti Layer 3, the frozen Punkti v0.6
  carrier/spec, the PWA, relay, deployment, identity migration or any production state.
- ALL new tracked files live under `experimental/brth-qr/`. No tracked file outside that
  directory may be modified. `experimental/brth-layer4/` is READ-ONLY input for this task
  (you may import it; do not edit it).
- EXPLICIT EXCEPTION for untracked, gitignored build/runtime artefacts. Running the existing
  suite and the existing OpenSSL bridge necessarily creates these paths; they are transient
  and must never be committed:
  - `experimental/brth-layer4/node_modules/` (already listed in that directory's
    `.gitignore`) — required by `npm install` in §7.1;
  - `experimental/brth-layer4/.tmp/` (already listed in that directory's `.gitignore`) —
    the hard-coded temp directory of `experimental/brth-layer4/tools/pq-openssl.js`, which
    writes `key.der`, `message` and `sig` there and cannot be redirected by `TMPDIR` or
    the working directory;
  - `experimental/brth-qr/node_modules/` and `experimental/brth-qr/.work/` — add a
    `.gitignore` inside `experimental/brth-qr/` listing `node_modules/`, `.work/`,
    `__pycache__/` and `out/*.tmp` before creating them.
  These paths are not "files outside the boundary" for the purposes of §7.6-§7.7: they are
  untracked build artefacts. `git status --short` must show only `experimental/brth-qr/`
  entries, and the final diff must contain no ignored artefact.
- For §5 you MAY stage an unmodified working copy of the Layer 4 tree under
  `experimental/brth-qr/.work/layer4/` (gitignored) so that the OpenSSL bridge's `.tmp/`
  writes land inside the boundary. If you do, the copy must be byte-identical to
  `experimental/brth-layer4/` except for `node_modules/`; assert that with a diff. This is
  permitted; it is not a licence to modify Layer 4.
- Existing production Ed25519 signatures remain explicitly NON-post-quantum. No text may
  describe Ed25519 as PQ-safe.
- No new cryptographic invention. Only NIST FIPS 203/204/205 algorithms already used by
  `experimental/brth-layer4` (ML-DSA-87, SLH-DSA-SHAKE-256s) plus, for byte-budget
  comparison only, the standard parameter sets of ML-DSA-44/65/87 and
  SLH-DSA-SHAKE-128s/192s/256s/128f/256f. Any non-NIST-standardised scheme (e.g. Falcon-512)
  may appear ONLY in an explicitly-labelled appendix note that states it is not relied upon
  by any construction and is not FIPS-standardised.
- No protocol freeze, no merge to `main`, no PR, no deployment, no secret material in the
  report or in committed vectors.

## 2. Deliverables

All under `experimental/brth-qr/`:

- `docs/BRTH_QR_R1_REPORT.md` — the normative R1 report (section 3 defines its contents).
- `tools/measure_qr.py` — real QR byte/character budget measurement (section 4).
- `tools/offline_reconstruct_proof.mjs` — offline clean-machine-style proof (section 5).
- `test/brth_qr.test.mjs` — Node test suite (section 6).
- `README.md` — how to reproduce every number and every test in the report.

## 3. Report contents (`docs/BRTH_QR_R1_REPORT.md`)

The report must contain, in this order, each with concrete measured numbers (no estimates
presented as measurements; estimates must be labelled as estimates):

1. **Scope, layering and non-goals.** What this slice does and does not decide.
2. **Audit of the closed CEO-OS #3 implementation.** Cite concrete files/paths under
   `experimental/brth-layer4/` (spec, `src/keys.js`, `src/birth.js`, `src/mnemonic.js`,
   `src/recover.js`, `test/pq.test.js`, `test/vectors.test.js`, `EVIDENCE.md`, committed
   `vectors/*.json`). State precisely what #3 PROVED (deterministic 24-word -> entropy ->
   HKDF-SHA-512 -> ML-DSA-87 + SLH-DSA-SHAKE-256s root keys -> canonical Birth ->
   `IdentityID = "b1:" + base32(SHA3-256(CJSON(Birth)))`; append-only hash-chained authority
   log; 2-of-2 dual-family root quorum; revoke/succeed/root.rotate preserving `IdentityID`;
   cross-verification against OpenSSL 3.5.5) versus what it did NOT solve (the physical
   one-QR packaging: carrying durable root material in ONE printed QR, and the public-vs-private
   custody split). Include the real key/signature byte sizes measured in THIS run.
3. **Threat model.** Cover, each with an explicit attacker capability and consequence:
   harvest-now/decrypt-later; key substitution (attacker replaces the key material in the QR);
   offline verification lasting 100+ years (algorithm agility / succession);
   key recovery and key succession; public-vs-private QR custody. State the hard rule:
   a publicly displayed QR must NOT expose the private root signing seed; the private backup
   scenario and the public verification scenario are separate designs.
4. **Real byte/character budget for ONE printed QR.** Must be produced by `tools/measure_qr.py`
   from a real QR encoder, per candidate payload: encoding mode, error-correction level,
   QR version, module count, raw payload bytes, encoded payload characters, and whether the
   payload survives a real decode round trip (per-decoder results for cv2 and zxing-cpp; a
   payload counts as decoded if at least one decoder recovers it byte-identically). The
   report MUST NOT claim that a payload is unreadable when only one decoder failed. Must compare, using the standard parameter
   sets, at minimum: ML-DSA-44/65/87 public key and signature sizes, SLH-DSA-SHAKE-128s,
   -192s, -256s and -256f public key and signature sizes, base64 and base32 expansions of
   those, and the cost of the dual-family public key set together. Must state the QR
   capacities actually used by the tool (version 40 at error-correction levels L/M/Q/H, in
   byte mode; numeric and alphanumeric only where stated) and cite the measured values.
   Include the measured "one QR cannot carry public key + signature for the smallest
   standard NIST parameter set" result as an exact arithmetic table, not as prose.
5. **At most TWO minimal constructions.** Each must relate a private 24-word recovery form
   and a public-or-private QR to the SAME durable root material, with no DNS, no Punkto, no
   server, no registry and no second lookup. For each: exact fields carried, exact bytes,
   who can verify what from one QR alone, what is explicitly NOT verifiable from one QR
   alone, custody rule (private-only vs publicly displayable), and the security assumptions
   it inherits. Rank the two against the original strict constraints of CEO-OS #10 and state
   the ranking rationale.
6. **Result classification.** State plainly whether the outcome is (a) a materially improved
   construction, (b) a rigorous impossibility result, or (c) a tradeoff with explicit
   residuals — and give the precise reason.
7. **Offline clean-machine proof.** Describe and cite the actual run of
   `tools/offline_reconstruct_proof.mjs`, including the exact commands and their real output
   (redacted: never print the 24-word phrase, raw entropy, private keys or seed material;
   print only public values and a SHA-256 digest of sensitive material).
8. **Remaining open assumptions.** Every assumption the result depends on, each with the
   concrete consequence if it turns out false.
9. **Founder decision request.** An explicit, numbered list of at most 5 decisions the
   Founder must make, each phrased as a question with the recommended option stated.
10. **Reproduction index.** Every table and number in the report points to the exact command
    and file that regenerates it.

## 4. `tools/measure_qr.py` — real measurement requirements

- Use a real QR encoder. `segno` (1.6.6) is already installed for the interpreter at
  `/home/hermes/.hermes/tools/python-3.14.9+202****1021-linux-x64/bin/python3`
  (verify the exact path first with `ls`; the directory name literally contains `****`).
  If segno is unavailable to your interpreter, create a venv and install segno there.
- DECODER REQUIREMENT (supersedes any single-decoder assumption): a decode round trip MUST
  use TWO independent real decoders:
  (a) `opencv-python-headless` `cv2.QRCodeDetector` (5.0.0, already installed for that
      interpreter), AND
  (b) `zxing-cpp` (Python `zxingcpp`, install with `pip install zxing-cpp` for the same
      interpreter; `zxingcpp.read_barcodes(png)` returns results whose `.bytes` must equal
      the input payload).
  A payload counts as DECODED only if at least one decoder recovers it byte-identically.
  Record per-decoder results separately in the JSON (`decode_cvp2`, `decode_zxingcpp`,
  `decode_ok`). A single decoder failing MUST NOT be reported as a QR-level failure: the
  measurement must distinguish "this decoder could not read it" from "no decoder could
  read it", and the report must state which decoder produced each result.
  Independently confirmed during the R1 run: `cv2.QRCodeDetector` fails to decode dense
  v40 codes at every tested scale/border (5/4, 9/4, 20/8, 40/12) for payloads of 1500+
  bytes, while `zxing-cpp` decodes 1500-, 2693-, 2900- and full 2953-byte v40-L byte-mode
  payloads byte-identically. Treat cv2 failures as a decoder limitation, not a capacity
  limit, and re-derive every "decode failed" statement in the report accordingly.
- For every measured payload the tool MUST: encode it, and record version, error-correction
  level, mode, module count, payload byte length and encoded character length; and decode the
  rendered PNG back with a real decoder and assert the decoded payload equals the input.
  `opencv-python-headless` (5.0.0, `cv2.QRCodeDetector`) is installed for the same
  interpreter; use it for the decode round trip. If the decode round trip fails for a
  payload, report the failure as a measurement result — never silently drop the case.
- The tool MUST additionally report the raw capacity limits it used (e.g. version 40 byte
  mode at L/M/Q/H) by measuring them (encode payloads of increasing length and observe where
  the encoder refuses or raises the version), rather than quoting remembered constants.
- Output a machine-readable JSON file (`experimental/brth-qr/out/measurements.json`) and a
  Markdown table (`experimental/brth-qr/out/measurements.md`) that the report embeds.
- Payload set MUST include, at minimum: (a) the 24-word recovery form; (b) a private QR
  capsule carrying the same root material as the 24 words; (c) a public descriptor QR
  carrying a single PQ public key plus identity metadata; (d) a public descriptor QR
  carrying the DUAL-family public key set; (e) a QR carrying public key + signature for
  ML-DSA-44 and for ML-DSA-65; (f) the base64 and base32 encodings of the relevant public
  keys. Report per case: fits / does not fit at v40-L, v40-M, v40-Q, v40-H.
- The tool MUST print an explicit INFASIBLE verdict (with the exact byte shortfall) for the
  cases that do not fit, and the report MUST repeat those shortfalls exactly.

## 5. `tools/offline_reconstruct_proof.mjs` — offline proof requirements

- Reuse the existing, unmodified `experimental/brth-layer4/src` implementation
  (`mnemonic.js`, `keys.js`, `birth.js`, `recover.js`, `cjson.js`, `format.js`) — this is the
  point of the audit: the QR work must reuse #3, not reimplement the identity.
- The proof MUST show a full destroy-and-reconstruct cycle:
  1. build a 24-word phrase (deterministic test phrase or freshly generated);
  2. derive entropy -> root keys -> canonical Birth -> `IdentityID`;
  3. encode the QR capsule bytes for that identity;
  4. DISCARD every in-memory object from steps 1-3 except the capsule bytes, then in a
     FRESH CHILD PROCESS reconstruct the identity from ONLY the capsule bytes and the
     24-word form, and assert: byte-identical canonical Birth, identical `IdentityID`,
     identical derived public keys (compare SHA-256 of the public keys, not the keys
     themselves), and a valid signature made by the reconstructed root over a test message
     verified with the independent OpenSSL 3.5.5 path (`experimental/brth-layer4/tools/pq-openssl.js`).
  5. Assert the reconstructed identity can verify a signature produced BEFORE the destroy
     step (cross-process continuity of authority).
- Redaction rules (hard): never write the phrase, entropy, seed, private keys or any
  private key bytes to stdout, to the report, or to any committed file. Only public values
  plus SHA-256 digests of sensitive material may appear.
- Offline hygiene: run the reconstruction in a fresh temporary working directory and a fresh
  process with a minimal environment. Attempt real network isolation (e.g. `unshare -n`); if
  the sandbox forbids it, state plainly in the report that kernel network-namespace
  isolation was unavailable, what isolation was actually used (fresh process, clean env,
  no DNS or network calls attempted) and what that does and does not prove. Do NOT claim
  stronger isolation than was actually achieved.
- Output a JSON result file (`experimental/brth-qr/out/offline_proof.json`) with the
  public values and verdicts.

## 6. `test/brth_qr.test.mjs` — required assertions

- 24-word <-> entropy <-> QR capsule round trip yields the identical `IdentityID`.
- The public-descriptor QR payload NEVER contains the entropy, the 24 words, the seed or
  any private key material (assert by scanning the encoded payload for the entropy bytes and
  their base64/base32 forms).
- Measured feasibility verdicts are asserted as facts by the test (e.g. dual-family public
  key set in base64 does not fit v40-L; public key + ML-DSA-44 signature does not fit),
  using the values produced by the measurement run.
- A QR payload fits / does not fit check uses the real encoder, not a hard-coded constant.
- The report's byte-accounting tables are consistent with the measurement JSON (the test
  re-reads `out/measurements.json` and checks the report contains the same figures).

## 7. Acceptance criteria (the run is complete only when all hold)

1. `cd experimental/brth-layer4 && npm install && npm test` still passes unchanged (the #3
   suite must not regress; report the exact pass/fail counts).
2. `cd experimental/brth-qr && node --test test/` passes with every test green.
3. `python3 tools/measure_qr.py` runs clean and produces `out/measurements.json` and
   `out/measurements.md`; every payload case shows a real decode round trip result.
4. `node tools/offline_reconstruct_proof.mjs` runs clean and produces
   `out/offline_proof.json` with all verdicts true.
5. `docs/BRTH_QR_R1_REPORT.md` exists and satisfies every section requirement in §3, with
   real measured numbers, no placeholder text, and a Founder decision request.
6. `git diff --check` clean; `git status --short` shows only `experimental/brth-qr/` entries
   (plus untracked-but-ignored `node_modules/`, `.tmp/`, `.work/` build artefacts, which
   must NOT appear in `git status` output).
7. No secret material anywhere in the diff; `git diff` shows no TRACKED file outside
   `experimental/brth-qr/`, and `git status --short --ignored` shows only the explicitly
   permitted build-artefact paths listed in §1.

## 8. Stop condition

When the acceptance criteria hold, STOP and report: files changed, exact commands run with
their real outputs, test counts, the measured byte verdicts, the two ranked constructions,
and any remaining blocker. Do NOT commit, push, open a PR, merge, deploy, write to Notion,
or post to GitHub — the Hermes worker does the commit, push and write-back itself.
