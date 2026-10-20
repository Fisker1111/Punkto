"use strict";
const { fields, id, integer, bytes } = require("./format");
const { encode } = require("./cjson");
const {
  signObject,
  unsigned,
  authorized,
  deriveState,
} = require("./authority");
const { identityIdOf } = require("./birth");
function validate(o) {
  fields(o, ["type", "v", "subject", "issuer", "claim", "iat", "ref", "sigs"]);
  if (o.type !== "brth.attest" || o.v !== 1)
    throw Error("attestation constants");
  id(o.subject);
  id(o.issuer);
  integer(o.iat);
  if (o.ref !== null) bytes(o.ref, 32);
  if (!o.claim || typeof o.claim !== "object" || Array.isArray(o.claim))
    throw Error("claim object");
  encode(o.claim);
}
function buildAttestation(input, signers) {
  fields(input, ["subject", "issuer", "claim", "iat", "ref"]);
  const o = signObject({ type: "brth.attest", v: 1, ...input }, signers);
  validate(o);
  return o;
}
function verifyAttestation(o, log, { atIat = o?.iat } = {}) {
  try {
    validate(o);
    integer(atIat);
    if (atIat !== o.iat) throw Error("evaluation must use signed iat");
    if (identityIdOf(log.birth) !== o.issuer) throw Error("issuer mismatch");
    const full = deriveState(log);
    if (full.status !== "OK") throw Error("issuer log " + full.status);
    // iat is untrusted and may regress. Do not guess a historical prefix in that case.
    for (let i = 1; i < log.events.length; i++)
      if (log.events[i].iat < log.events[i - 1].iat)
        throw Error("ambiguous issuer timestamps");
    const events = log.events.filter((e) => e.iat <= atIat);
    const state = deriveState({ birth: log.birth, events });
    authorized(o, state, "sign");
    return { ok: true, reasons: [], seq: state.seq };
  } catch (e) {
    return { ok: false, reasons: [e.message] };
  }
}
module.exports = { buildAttestation, verifyAttestation };
