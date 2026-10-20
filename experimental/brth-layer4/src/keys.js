"use strict";
const { hkdfSync, createHash } = require("node:crypto");
const { ml_dsa87 } = require("@noble/post-quantum/ml-dsa.js");
const { slh_dsa_shake_256s } = require("@noble/post-quantum/slh-dsa.js");
const bridge = require("../tools/pq-openssl");
const { b32, bytes, fields } = require("./format");
const ML = "ML-DSA-87",
  SLH = "SLH-DSA-SHAKE-256s";
function suite(alg) {
  if (alg === ML) return ml_dsa87;
  if (alg === SLH) return slh_dsa_shake_256s;
  throw Error("algorithm");
}
function kidOf(alg, pk) {
  suite(alg);
  if (!(pk instanceof Uint8Array) || pk.length !== (alg === ML ? 2592 : 64))
    throw Error("public key");
  return (
    "k:" +
    b32(
      createHash("sha3-256")
        .update(alg)
        .update(Buffer.from([0]))
        .update(pk)
        .digest(),
    )
  );
}
function validateKey(k) {
  fields(k, ["alg", "pk"]);
  kidOf(k.alg, bytes(k.pk));
}
function deriveRootKeys(entropy) {
  if (!(entropy instanceof Uint8Array) || entropy.length !== 32)
    throw Error("32-byte entropy");
  const seed = (alg) =>
    Buffer.from(
      hkdfSync(
        "sha512",
        entropy,
        Buffer.from("BRTH/1/root/salt"),
        Buffer.from("BRTH/1/root/" + alg),
        alg === ML ? 32 : 96,
      ),
    );
  const skSeed = seed(ML),
    ml = ml_dsa87.keygen(skSeed),
    slh = slh_dsa_shake_256s.keygen(seed(SLH));
  return {
    ml: { pk: Buffer.from(ml.publicKey), skSeed },
    slh: { pk: Buffer.from(slh.publicKey), sk: Buffer.from(slh.secretKey) },
    kid: (pk, alg) => kidOf(alg, pk),
  };
}
function sign(alg, sk, msg, { deterministic = true } = {}) {
  suite(alg);
  if (
    !(sk instanceof Uint8Array) ||
    !(msg instanceof Uint8Array) ||
    typeof deterministic !== "boolean"
  )
    throw Error("sign arguments");
  if (alg === SLH && deterministic && bridge.capable())
    return bridge.sign(alg, sk, msg);
  const secret =
    alg === ML && sk.length === 32 ? ml_dsa87.keygen(sk).secretKey : sk;
  return Buffer.from(
    suite(alg).sign(msg, secret, {
      extraEntropy: deterministic ? false : undefined,
    }),
  );
}
function verify(alg, pk, msg, sig) {
  try {
    kidOf(alg, pk);
    return suite(alg).verify(sig, msg, pk);
  } catch {
    return false;
  }
}
function rootSigners(r) {
  return [
    { alg: ML, pk: r.ml.pk, sk: r.ml.skSeed },
    { alg: SLH, pk: r.slh.pk, sk: r.slh.sk },
  ];
}
module.exports = {
  ML,
  SLH,
  deriveRootKeys,
  kidOf,
  keyId: kidOf,
  sign,
  verify,
  validateKey,
  rootSigners,
};
