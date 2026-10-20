"use strict";
const b = require("../src");
const { ml_dsa87 } = require("@noble/post-quantum/ml-dsa.js");
const ROOT = b.deriveRootKeys(Buffer.alloc(32));
const BIRTH = b.buildBirth(ROOT);
const ROOTS = b.rootSigners(ROOT);
const IAT = 1760000000;
function op(n = 1) {
  const sk = Buffer.alloc(32, n),
    kp = ml_dsa87.keygen(sk);
  return { alg: b.ML, pk: Buffer.from(kp.publicKey), sk };
}
function key(s) {
  return { alg: s.alg, pk: s.pk.toString("base64url") };
}
function grant(
  log,
  s,
  scopes = ["sign", "claim", "authority"],
  signers = ROOTS,
  iat = IAT,
  not_after = null,
) {
  return b.append(
    log,
    "authorize",
    { key: key(s), scopes, not_after },
    signers,
    { iat },
  );
}
function event(log, op, body, signers = ROOTS, iat = IAT) {
  const s = b.deriveState(log);
  return b.signEvent(
    {
      type: "brth.event",
      v: 1,
      id: s.id,
      seq: s.seq + 1,
      prev: s.headHash,
      op,
      iat,
      body,
    },
    signers,
  );
}
module.exports = { b, ROOT, BIRTH, ROOTS, IAT, op, key, grant, event };
