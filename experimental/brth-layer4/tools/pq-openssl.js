"use strict";
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
function tlv(tag, b) {
  b = Buffer.from(b);
  const n = b.length;
  const len =
    n < 128
      ? Buffer.from([n])
      : n < 256
        ? Buffer.from([129, n])
        : Buffer.from([130, n >> 8, n & 255]);
  return Buffer.concat([Buffer.from([tag]), len, b]);
}
function algorithm(alg) {
  const last =
    alg === "ML-DSA-87" ? 19 : alg === "SLH-DSA-SHAKE-256s" ? 30 : null;
  if (last === null) throw Error("algorithm");
  return tlv(48, tlv(6, Buffer.from([96, 134, 72, 1, 101, 3, 4, 3, last])));
}
function privateDer(alg, sk) {
  return tlv(
    48,
    Buffer.concat([
      tlv(2, [0]),
      algorithm(alg),
      tlv(4, alg === "ML-DSA-87" ? tlv(128, sk) : sk),
    ]),
  );
}
function publicDer(alg, pk) {
  return tlv(
    48,
    Buffer.concat([
      algorithm(alg),
      tlv(3, Buffer.concat([Buffer.from([0]), pk])),
    ]),
  );
}
function capable() {
  const r = spawnSync("openssl", ["list", "-signature-algorithms"], {
    encoding: "utf8",
  });
  return r.status === 0 && r.stdout.includes("SLH-DSA-SHAKE-256s");
}
function run(alg, key, msg, sig) {
  const base = path.join(__dirname, "../.tmp");
  fs.mkdirSync(base, { recursive: true });
  const dir = fs.mkdtempSync(path.join(base, "pq-"));
  try {
    const k = path.join(dir, "key.der"),
      m = path.join(dir, "message"),
      s = path.join(dir, "sig");
    fs.writeFileSync(k, key, { mode: 0o600 });
    fs.writeFileSync(m, msg);
    if (sig) fs.writeFileSync(s, sig);
    const args = [
      "pkeyutl",
      sig ? "-verify" : "-sign",
      "-rawin",
      "-inkey",
      k,
      "-keyform",
      "DER",
      "-in",
      m,
    ];
    if (sig) args.push("-pubin", "-sigfile", s);
    else args.push("-out", s, "-pkeyopt", "deterministic:1");
    const r = spawnSync("openssl", args, { encoding: "utf8" });
    if (sig) return r.status === 0;
    if (r.status !== 0) throw Error(r.stderr || "OpenSSL failed");
    return fs.readFileSync(s);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
function derivePublic(alg, sk) {
  const r = spawnSync(
    "openssl",
    ["pkey", "-inform", "DER", "-pubout", "-outform", "DER"],
    { input: privateDer(alg, sk) },
  );
  if (r.status !== 0) throw Error(r.stderr.toString());
  return r.stdout.subarray(-(alg === "ML-DSA-87" ? 2592 : 64));
}
module.exports = {
  privateDer,
  publicDer,
  capable,
  derivePublic,
  sign: (alg, sk, msg) => run(alg, privateDer(alg, sk), msg),
  verify: (alg, pk, msg, sig) => run(alg, publicDer(alg, pk), msg, sig),
};
