# BRTH one-QR research R1

An isolated packaging audit of the unchanged `../brth-layer4/` implementation.
Read [the normative report](docs/BRTH_QR_R1_REPORT.md) for the measured verdicts,
custody split and remaining limits. This is research, not a frozen wire protocol,
production wallet or deployment. Ed25519 is not post-quantum safe.

## Reproduce

Node 26, OpenSSL **3.5.5**, Python with `segno==1.6.6`,
`opencv-python-headless==5.0.0`, `zxing-cpp==3.1.1` and NumPy are required. The existing Layer 4 suite
also needs Python `cryptography`. Installation accesses the package registry;
the proof and measurement routines contain no network calls.

From the repository root:

```sh
ls -d /home/hermes/.hermes/tools/python*
cd experimental/brth-layer4
npm install && npm test
cd ../brth-qr
export QR_PYTHON=/home/hermes/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3
export PATH="$(dirname "$QR_PYTHON"):$PATH"
python3 -c 'import segno,cv2,zxingcpp,importlib.metadata; print("segno",segno.__version__); print("opencv",cv2.__version__); print("zxing-cpp",importlib.metadata.version("zxing-cpp"))'
python3 tools/measure_qr.py
node tools/offline_reconstruct_proof.mjs
python3 tools/build_report.py
node --test test/
git diff --check
git status --short --ignored
```

The actual installed Python directory is `python-3.14.9+20261021-linux-x64`;
it has no literal asterisks, contrary to the path description in the task spec.
If unavailable, create a venv **inside `.work/`** and install the pinned packages
there, then set `QR_PYTHON` to its interpreter. No Layer 4 source copy or change
is required. Its existing OpenSSL bridge uses its permitted ignored `.tmp/`.
Allow several minutes for real SLH key generation/signing and QR encoding.

`measure_qr.py` creates `out/measurements.json` and `out/measurements.md`.
It binary-searches each version-40 mode/EC capacity and tests the exact boundary
and boundary plus one. Every feasible case is encoded at the smallest version
with EC boosting disabled, rendered to PNG in memory and decoded with OpenCV's
binary-safe `detectAndDecodeBytes` AND independently with zxing-cpp's
`read_barcodes`, comparing result `.bytes` to the original payload. Each decoder
tries scales 5 and 9 until its own success. JSON records `decode_cvp2` (cv2,
spelled as required by the spec), `decode_zxingcpp`, and `decode_ok` (either
succeeds byte-identically). All attempts are retained with their decoder names.
A cv2-only failure is a decoder limitation, not an unreadable QR or capacity limit. Oversize cases have `decode_ok: false`, `decode_result: "not encodable"`,
and no invented version/module count: there is no QR image to decode.

Base64 is padded RFC 4648 in byte mode. Base32 is unpadded uppercase RFC 4648
in alphanumeric mode. Shortfalls are bytes for byte-mode payloads and ASCII
bytes/characters for alphanumeric payloads; numeric capacity is diagnostic only.
Raw binary QR segments have no character string (`encoded_characters: null`).
Every key/signature size comes from real noble key generation, signing and
verification; the smaller parameter sets are **comparison only**. Actual BRTH
constructions retain ML-DSA-87 plus SLH-DSA-SHAKE-256s.

The producer `tools/payloads.mjs` uses a dedicated anonymous pipe, never stdout,
for private measurement inputs. Do not modify it to print payloads. Its all-zero
published Layer 4 test case is unsuitable for a real identity. No phrase,
entropy, seed, private key, capsule contents or private QR image is saved in
`out/`, reports or logs. Only sizes, public values and SHA-256 digests are saved.

The offline proof defaults to a fixed public TEST vector: 32 zero bytes
(256 zero bits), non-secret test material, never a production secret or identity. Its generator exits before a
fresh child reconstructs from the retained capsule through the 24-word form.
A public-only before-signature/Birth evidence file is read **after** reconstruction
for equality/continuity checks. The capsule is the only retained secret; there
is no secret-bearing stdout. With the same runtime and isolation environment, default runs reproduce
`out/offline_proof.json` byte-for-byte. Check with:

```sh
node tools/offline_reconstruct_proof.mjs
cp out/offline_proof.json .work/offline-proof-first.json
sha256sum out/offline_proof.json
node tools/offline_reconstruct_proof.mjs
sha256sum out/offline_proof.json
cmp .work/offline-proof-first.json out/offline_proof.json
```

For fresh random entropy, explicitly run
`node tools/offline_reconstruct_proof.mjs --random`. This overwrites the evidence
with a new identity; sizes and verdicts remain stable. To restore reproducible
evidence afterward, run the default command and then
`python3 tools/build_report.py`. The report builder refreshes embedded evidence. This is process-lifetime destruction, not a guarantee of physical RAM,
swap or garbage-collected-buffer erasure. The `.tmp/` bridge files are deleted
in its existing `finally` blocks.

Network namespace creation is attempted with `unshare -n true`. If denied,
the result explicitly reports the fallback: fresh process, temporary cwd,
minimal environment and no attempted network calls, without claiming enforced
network isolation. Failed crypto or reconstruction assertions terminate the
proof and do not produce a new successful result.

The tests check identity round trips, malformed capsules, absence of private
material in public descriptors, public Birth reconstruction, measured feasibility,
live encoder boundaries, verbatim report/table consistency, and offline verdicts.
No browser/manual physical printing test is claimed. All writes stay within
this research directory, except the explicitly allowed Layer 4 npm and `.tmp/`
build/runtime artefacts. Do not commit ignored files.
