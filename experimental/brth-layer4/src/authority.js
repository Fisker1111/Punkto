"use strict";
const { encode, digest } = require("./cjson");
const { fields, integer, text, bytes, id, clone } = require("./format");
const { validateRoot, identityIdOf } = require("./birth");
const { validateKey, kidOf, sign, verify } = require("./keys");
const hash = (o) => digest(o).toString("base64url");
function scopes(a) {
  if (
    !Array.isArray(a) ||
    a.some((s) => !["sign", "claim", "authority"].includes(s)) ||
    new Set(a).size !== a.length
  )
    throw Error("scopes");
}
function expiry(n) {
  if (n !== null) integer(n);
}
function claims(c) {
  if (!c || typeof c !== "object" || Array.isArray(c))
    throw Error("claims object");
  encode(c);
}
function bodyValid(op, b) {
  switch (op) {
    case "authorize":
      fields(b, ["key", "scopes", "not_after"]);
      validateKey(b.key);
      scopes(b.scopes);
      expiry(b.not_after);
      break;
    case "revoke":
      fields(b, ["kid", "reason"]);
      id(b.kid, "k:");
      text(b.reason);
      break;
    case "succeed":
      fields(b, ["from", "to", "reason"]);
      text(b.reason);
      if (
        !Array.isArray(b.from) ||
        !Array.isArray(b.to) ||
        new Set(b.from).size !== b.from.length
      )
        throw Error("succession lists");
      b.from.forEach((k) => id(k, "k:"));
      b.to.forEach((k) => {
        fields(k, ["alg", "pk", "scopes", "not_after"]);
        validateKey({ alg: k.alg, pk: k.pk });
        scopes(k.scopes);
        expiry(k.not_after);
      });
      if (
        new Set(b.to.map((k) => kidOf(k.alg, bytes(k.pk)))).size !== b.to.length
      )
        throw Error("duplicate successor");
      break;
    case "root.rotate":
      fields(b, ["root", "reason"]);
      validateRoot(b.root);
      text(b.reason);
      break;
    case "claim.set":
      fields(b, ["claims"]);
      claims(b.claims);
      break;
    case "claim.del":
      fields(b, ["names"]);
      if (!Array.isArray(b.names) || new Set(b.names).size !== b.names.length)
        throw Error("claim names");
      b.names.forEach(text);
      break;
    default:
      throw Error("unknown op");
  }
}
function sigsValid(sigs) {
  if (!Array.isArray(sigs) || !sigs.length) throw Error("signatures required");
  const seen = new Set();
  for (const s of sigs) {
    fields(s, ["alg", "kid", "sig"]);
    if (!["ML-DSA-87", "SLH-DSA-SHAKE-256s"].includes(s.alg))
      throw Error("signature algorithm");
    id(s.kid, "k:");
    bytes(s.sig, s.alg === "ML-DSA-87" ? 4627 : 29792);
    if (seen.has(s.kid)) throw Error("duplicate signer");
    seen.add(s.kid);
  }
}
function verifyEvent(e) {
  try {
    fields(e, ["type", "v", "id", "seq", "prev", "op", "iat", "body", "sigs"]);
    if (e.type !== "brth.event" || e.v !== 1) throw Error("event constants");
    id(e.id);
    integer(e.seq);
    if (e.seq < 1) throw Error("sequence");
    integer(e.iat);
    if (e.prev !== null) bytes(e.prev, 32);
    if ((e.seq === 1) !== (e.prev === null)) throw Error("prev/sequence");
    bodyValid(e.op, e.body);
    sigsValid(e.sigs);
    return { ok: true, errors: [] };
  } catch (e) {
    return { ok: false, errors: [e.message] };
  }
}
function unsigned(e) {
  const { sigs, ...rest } = e;
  return rest;
}
function signObject(o, signers) {
  if (!Array.isArray(signers) || !signers.length)
    throw Error("signers required");
  const msg = encode(o);
  const result = {
    ...clone(o),
    sigs: signers.map((s) => ({
      alg: s.alg,
      kid: kidOf(s.alg, s.pk),
      sig: sign(s.alg, s.sk, msg, { deterministic: true }).toString(
        "base64url",
      ),
    })),
  };
  sigsValid(result.sigs);
  return result;
}
function signEvent(e, signers) {
  fields(e, ["type", "v", "id", "seq", "prev", "op", "iat", "body"]);
  const signed = signObject(e, signers);
  const v = verifyEvent(signed);
  if (!v.ok) throw Error(v.errors.join());
  return signed;
}
function newLog(birth) {
  identityIdOf(birth);
  return { birth: clone(birth), events: [] };
}
function active(k, iat) {
  return k && (k.not_after === null || iat <= k.not_after);
}
// Every signature must be valid and authorized; a partial root quorum cannot substitute for a scoped key.
function authorized(o, state, scope, rootOnly = false) {
  sigsValid(o.sigs);
  const msg = encode(unsigned(o));
  const roots = new Set(),
    operators = [];
  for (const s of o.sigs) {
    const root = state.root.keys.find(
      (k) => kidOf(k.alg, bytes(k.pk)) === s.kid,
    );
    const k = root || state.keys[s.kid];
    if (!k || k.alg !== s.alg || !verify(s.alg, bytes(k.pk), msg, bytes(s.sig)))
      throw Error("invalid/unknown signature");
    if (root) roots.add(root.alg);
    else {
      if (rootOnly || !active(k, o.iat) || !k.scopes.includes(scope))
        throw Error("unauthorized scope/expiry");
      operators.push(s.kid);
    }
  }
  if (roots.size && roots.size !== 2) throw Error("root quorum");
  if (
    roots.size !== 2 &&
    !operators.some((kid) => state.keys[kid].alg === "ML-DSA-87")
  )
    throw Error("ML-DSA operational signature required");
  return operators;
}
function apply(e, s) {
  const v = verifyEvent(e);
  if (!v.ok) throw Error(v.errors.join());
  if (e.id !== s.id || e.seq !== s.seq + 1 || e.prev !== s.headHash)
    throw Error("identity/chain");
  const operators = authorized(
    e,
    s,
    e.op.startsWith("claim.") ? "claim" : "authority",
    e.op === "root.rotate",
  );
  const b = e.body,
    priorKeys = clone(s.keys);
  function add(k) {
    const kid = kidOf(k.alg, bytes(k.pk));
    // Reauthorizing an existing signing key may not widen its own scope or lifetime.
    if (operators.includes(kid)) {
      const old = priorKeys[kid];
      if (
        k.scopes.some((x) => !old.scopes.includes(x)) ||
        (old.not_after !== null &&
          (k.not_after === null || k.not_after > old.not_after))
      )
        throw Error("self widening");
    }
    s.keys[kid] = clone(k);
  }
  switch (e.op) {
    case "authorize":
      add({ ...b.key, scopes: b.scopes, not_after: b.not_after });
      break;
    case "revoke":
      if (!s.keys[b.kid]) throw Error("unknown revoked key");
      delete s.keys[b.kid];
      break;
    case "succeed":
      for (const k of b.from) {
        if (!s.keys[k] && !s.revoked.includes(k))
          throw Error("unknown predecessor");
        delete s.keys[k];
      }
      b.to.forEach(add);
      break;
    case "root.rotate":
      s.root = clone(b.root);
      break;
    case "claim.set":
      for (const [k, v] of Object.entries(b.claims))
        Object.defineProperty(s.claims, k, {
          value: clone(v),
          enumerable: true,
          writable: true,
          configurable: true,
        });
      break;
    case "claim.del":
      b.names.forEach((k) => delete s.claims[k]);
      break;
  }
  if (e.op === "revoke") s.revoked.push(b.kid);
  if (e.op === "succeed") s.revoked.push(...b.from);
  s.seq = e.seq;
  s.headHash = hash(e);
}
function deriveState(log, { untilSeq } = {}) {
  fields(log, ["birth", "events"]);
  const identity = identityIdOf(log.birth);
  if (!Array.isArray(log.events)) throw Error("events array");
  if (untilSeq !== undefined) {
    integer(untilSeq);
    if (untilSeq < 0) throw Error("untilSeq");
  }
  let s = {
    status: "OK",
    id: identity,
    root: clone(log.birth.root),
    keys: {},
    claims: {},
    seq: 0,
    headHash: null,
    fork: null,
    revoked: [],
    partial: true,
  };
  // Sort only by sequence. Duplicate/replayed records are errors, valid competing records are forks.
  const events = log.events.slice().sort((a, b) => a.seq - b.seq);
  for (let i = 0; i < events.length; ) {
    const e = events[i];
    if (untilSeq !== undefined && e.seq > untilSeq) break;
    const group = [];
    do {
      group.push(events[i++]);
    } while (i < events.length && events[i].seq === e.seq);
    const accepted = [];
    let error;
    for (const candidate of group) {
      try {
        const next = clone(s);
        apply(candidate, next);
        accepted.push({ candidate, next });
      } catch (err) {
        error = err.message;
      }
    }
    const unique = new Map(accepted.map((a) => [hash(a.candidate), a]));
    if (unique.size > 1) {
      s.status = "CONFLICTED";
      s.fork = { seq: e.seq, prev: s.headHash, hashes: [...unique.keys()] };
      break;
    }
    if (error || accepted.length !== 1) {
      s.status = "BROKEN";
      s.error = error || "duplicate/replayed event";
      break;
    }
    s = accepted[0].next;
  }
  if (untilSeq !== undefined && s.status === "OK" && s.seq < untilSeq) {
    s.status = "BROKEN";
    s.error = "missing requested history";
  }
  return s;
}
function append(log, op, body, signers, { iat } = {}) {
  integer(iat);
  const state = deriveState(log);
  if (state.status !== "OK") throw Error("log " + state.status);
  const event = signEvent(
    {
      type: "brth.event",
      v: 1,
      id: state.id,
      seq: state.seq + 1,
      prev: state.headHash,
      op,
      iat,
      body,
    },
    signers,
  );
  const result = deriveState({ ...log, events: [...log.events, event] });
  if (result.status !== "OK") throw Error(result.error || result.status);
  log.events.push(event);
  return event;
}
module.exports = {
  newLog,
  append,
  deriveState,
  verifyEvent,
  signEvent,
  signObject,
  unsigned,
  authorized,
  hash,
};
