"use strict";
const { randomBytes } = require("node:crypto");
const { ml_dsa87 } = require("@noble/post-quantum/ml-dsa.js");
const { wordsToEntropy } = require("./mnemonic");
const { deriveRootKeys, rootSigners, ML } = require("./keys");
const { buildBirth, identityIdOf } = require("./birth");
const { newLog, deriveState, signEvent } = require("./authority");
const { integer } = require("./format");
function recoverFromWords(words, { head, iat, operationalSeed }) {
  integer(iat);
  const rootKeys = deriveRootKeys(wordsToEntropy(words)),
    birth = buildBirth(rootKeys),
    identityId = identityIdOf(birth);
  // head is the public log, not merely a hash: replay prevents recovery against a fork or rotated root.
  const log = head === null ? newLog(birth) : head,
    state = deriveState(log);
  if (state.id !== identityId || state.status !== "OK")
    throw Error("recovery head mismatch");
  if (JSON.stringify(state.root) !== JSON.stringify(birth.root))
    throw Error(
      "original roots have rotated; phrase no longer has current authority",
    );
  const seed =
    operationalSeed === undefined ? randomBytes(32) : operationalSeed;
  if (!(seed instanceof Uint8Array) || seed.length !== 32)
    throw Error("operational seed");
  const kp = ml_dsa87.keygen(seed);
  const recoveryEvent = signEvent(
    {
      type: "brth.event",
      v: 1,
      id: identityId,
      seq: state.seq + 1,
      prev: state.headHash,
      op: "authorize",
      iat,
      body: {
        key: { alg: ML, pk: Buffer.from(kp.publicKey).toString("base64url") },
        scopes: ["sign", "claim", "authority"],
        not_after: null,
      },
    },
    rootSigners(rootKeys),
  );
  // Return the fresh private key locally; it is never included in the event.
  return {
    birth,
    identityId,
    rootKeys,
    recoveryEvent,
    operationalKey: { alg: ML, pk: Buffer.from(kp.publicKey), sk: seed },
  };
}
module.exports = { recoverFromWords };
